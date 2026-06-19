/**
 * AHA — Artificial Human Agent
 * Background Service Worker (MV3)
 *
 * Responsibilities:
 *  - chrome.alarms keepalive (every 0.5 min) to prevent SW termination
 *  - WebSocket connection to backend with exponential backoff
 *  - chrome.debugger CDP command execution
 *  - Screenshot capture via chrome.tabs.captureVisibleTab
 *  - OCR delegation to offscreen document
 */

// ─── Configuration ────────────────────────────────────────────────────────────
let BACKEND_WS_URL      = 'wss://aha-cloud-brain.onrender.com/ws/agent';
const WS_MAX_BACKOFF_MS = 30_000;
const ALARM_KEEPALIVE   = 'aha-keepalive';
const DEBUGGER_VERSION  = '1.3';

// Dynamic config loader to override URLs (e.g. for local testing)
async function loadConfig() {
  // Disabled custom URL overrides to ensure connection to Render backend
  /*
  const { customWsUrl } = await chrome.storage.local.get(['customWsUrl']);
  if (customWsUrl) {
    BACKEND_WS_URL = customWsUrl;
  }
  */
}

// ─── WebSocket state (stored in chrome.storage.session to survive SW restart)
let _ws            = null;
let _wsBackoffMs   = 1000;
let _wsConnecting  = false;
let _attachedTabId = null;  // current tab being debugged

// ─────────────────────────────────────────────────────────────────────────────
// ALARM: keepalive
// All listeners registered synchronously at top level.
// ─────────────────────────────────────────────────────────────────────────────
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_KEEPALIVE) {
    ensureWebSocket();
  }
});

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.local.set({ executionStatus: 'idle' });
  // Set up alarms on install/update
  await setupAlarms();
});

chrome.runtime.onStartup.addListener(async () => {
  await chrome.storage.local.set({ executionStatus: 'idle' });
  await setupAlarms();
});

// Message listener from popup.js
let _activeMediaAbsolutePath = null;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      switch (message.type) {
        case 'START_EXECUTION':
          _activeMediaAbsolutePath = message.payload.mediaAbsolutePath || null;
          await handleStartExecution(message.payload, sendResponse);
          break;
        case 'CAPTURE_SCREENSHOT':
          await handleCaptureScreenshot(message.tabId, sendResponse);
          break;
        case 'GET_STATUS':
          await handleGetStatus(sendResponse);
          break;
        default:
          sendResponse({ ok: false, error: `Unknown message type: ${message.type}` });
      }
    } catch (err) {
      console.error('[AHA BG] Message handler error:', err);
      sendResponse({ ok: false, error: err.message });
    }
  })();
  return true; // keep message channel open for async sendResponse
});

// CDP Event listener to bypass OS File Chooser Dialogs
chrome.debugger.onEvent.addListener(async (source, method, params) => {
  if (method === 'Page.fileChooserOpened') {
    if (_activeMediaAbsolutePath) {
      console.log('[AHA BG] Intercepted file chooser, injecting:', _activeMediaAbsolutePath);
      await chrome.debugger.sendCommand({ tabId: source.tabId }, 'Page.handleFileChooser', {
        action: 'accept',
        files: [_activeMediaAbsolutePath]
      });
    } else {
      console.log('[AHA BG] File chooser opened but no media available. Canceling.');
      await chrome.debugger.sendCommand({ tabId: source.tabId }, 'Page.handleFileChooser', {
        action: 'cancel'
      });
    }
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Alarm setup
// ─────────────────────────────────────────────────────────────────────────────
async function setupAlarms() {
  // Minimum alarm period is 0.5 minutes (30 seconds) per Chrome docs.
  const existing = await chrome.alarms.getAll();
  const names    = existing.map(a => a.name);

  if (!names.includes(ALARM_KEEPALIVE)) {
    chrome.alarms.create(ALARM_KEEPALIVE, { periodInMinutes: 0.5 });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket management
// ─────────────────────────────────────────────────────────────────────────────
function ensureWebSocket() {
  if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  if (_wsConnecting) return;
  connectWebSocket();
}

async function connectWebSocket() {
  _wsConnecting = true;
  await loadConfig();

  try {
    _ws = new WebSocket(BACKEND_WS_URL);
  } catch (err) {
    console.error('[AHA BG] WebSocket construction error:', err);
    _wsConnecting = false;
    scheduleReconnect();
    return;
  }

  _ws.onopen = async () => {
    console.log('[AHA BG] WebSocket connected');
    _wsBackoffMs  = 1000; // reset backoff on success
    _wsConnecting = false;

    await chrome.storage.local.set({ wsConnected: true });
    notifyPopup({ type: 'STATUS_UPDATE', status: 'connected' });
  };

  let _wsQueue = Promise.resolve();

  _ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      _wsQueue = _wsQueue.then(() => handleBackendMessage(msg)).catch(err => {
        console.error('[AHA BG] Queue execution error:', err);
      });
    } catch (err) {
      console.error('[AHA BG] WS message parse error:', err);
    }
  };

  _ws.onerror = (event) => {
    console.error('[AHA BG] WebSocket error:', event);
  };

  _ws.onclose = async (event) => {
    console.warn('[AHA BG] WebSocket closed:', event.code, event.reason);
    _ws            = null;
    _wsConnecting  = false;

    await chrome.storage.local.set({ wsConnected: false });
    notifyPopup({ type: 'STATUS_UPDATE', status: 'disconnected' });
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  const delay = Math.min(_wsBackoffMs, WS_MAX_BACKOFF_MS);
  console.log(`[AHA BG] Reconnecting WebSocket in ${delay}ms`);
  setTimeout(() => {
    _wsBackoffMs = Math.min(_wsBackoffMs * 2, WS_MAX_BACKOFF_MS);
    connectWebSocket();
  }, delay);
}

function safeSend(obj) {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify(obj));
    return true;
  }
  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Backend message handler
// ─────────────────────────────────────────────────────────────────────────────
async function handleBackendMessage(msg) {
  const msgType = msg.type || msg.action;
  switch (msgType) {
    case 'move_mouse':
    case 'MOUSE_MOVE':
      if (msg.path && Array.isArray(msg.path)) {
        const stepTime = msg.duration_ms ? msg.duration_ms / msg.path.length : 2;
        for (const [px, py] of msg.path) {
          await cdpMouseMove(_attachedTabId, px, py);
          if (stepTime > 0) await sleep(stepTime);
        }
      } else if (msg.x !== undefined && msg.y !== undefined) {
        await cdpMouseMove(_attachedTabId, msg.x, msg.y);
      }
      break;
    case 'click':
    case 'MOUSE_CLICK':
      await cdpMouseClick(_attachedTabId, msg.x, msg.y, msg.button ?? 'left');
      break;
    case 'KEY_DOWN':
      await cdpKeyDown(_attachedTabId, msg.key, msg.text);
      break;
    case 'KEY_UP':
      await cdpKeyUp(_attachedTabId, msg.key, msg.text);
      break;
    case 'type_text':
    case 'TYPE_TEXT':
      await cdpTypeText(_attachedTabId, msg.keystrokes || msg.text);
      break;
    case 'SCROLL':
      await cdpScroll(_attachedTabId, msg.x, msg.y, msg.deltaX ?? 0, msg.deltaY ?? 0);
      break;
    case 'scan_screen':
    case 'SCAN_SCREEN':
      const newElements = await scanScreen(_attachedTabId);
      safeSend({ type: 'scan_results', elements: newElements });
      break;
    case 'ATTACH_DEBUGGER':
      await attachDebugger(msg.tabId);
      break;
    case 'DETACH_DEBUGGER':
      await detachDebugger(msg.tabId);
      break;
    case 'done':
    case 'EXECUTION_COMPLETE':
      await chrome.storage.local.set({ executionStatus: 'idle' });
      notifyPopup({ type: 'EXECUTION_COMPLETE', success: msg.success ?? true, message: msg.message });
      break;
    case 'error':
      await chrome.storage.local.set({ executionStatus: 'idle' });
      notifyPopup({ type: 'EXECUTION_COMPLETE', success: false, message: msg.message });
      break;
    default:
      console.warn('[AHA BG] Unknown backend message type:', msgType, msg);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// chrome.debugger helpers
// ─────────────────────────────────────────────────────────────────────────────
async function attachDebugger(tabId) {
  try {
    // Detach from previously attached tab if different
    if (_attachedTabId !== null && _attachedTabId !== tabId) {
      await detachDebugger(_attachedTabId);
    }
    if (_attachedTabId === tabId) return; // already attached

    await chrome.debugger.attach({ tabId }, DEBUGGER_VERSION);
    _attachedTabId = tabId;
    console.log('[AHA BG] Debugger attached to tab', tabId);
    
    // Enable Page domain and intercept file choosers to bypass OS dialogs
    await chrome.debugger.sendCommand({ tabId }, 'Page.enable');
    await chrome.debugger.sendCommand({ tabId }, 'Page.setInterceptFileChooserDialog', { enabled: true });
  } catch (err) {
    console.error('[AHA BG] attachDebugger error:', err);
    throw err;
  }
}

async function detachDebugger(tabId) {
  try {
    await chrome.debugger.detach({ tabId });
    if (_attachedTabId === tabId) _attachedTabId = null;
    console.log('[AHA BG] Debugger detached from tab', tabId);
  } catch (err) {
    // May already be detached — not fatal
    console.warn('[AHA BG] detachDebugger warning:', err);
    if (_attachedTabId === tabId) _attachedTabId = null;
  }
}

async function cdpSend(tabId, method, params = {}) {
  // Ensure debugger is attached
  if (_attachedTabId !== tabId) {
    await attachDebugger(tabId);
  }
  return await chrome.debugger.sendCommand({ tabId }, method, params);
}

/** Mouse move */
async function cdpMouseMove(tabId, x, y) {
  await cdpSend(tabId, 'Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x,
    y,
    buttons: 0
  });
}

/** Mouse click — dispatches press + release */
async function cdpMouseClick(tabId, x, y, button = 'left') {
  const baseParams = {
    type: 'mousePressed',
    x,
    y,
    button,
    clickCount: 1
  };
  await cdpSend(tabId, 'Input.dispatchMouseEvent', baseParams);
  
  await sleep(40 + Math.random() * 60); // 40-100ms realistic click hold
  
  baseParams.type = 'mouseReleased';
  await cdpSend(tabId, 'Input.dispatchMouseEvent', baseParams);
}

/** Key down */
async function cdpKeyDown(tabId, key, text) {
  const params = { type: 'keyDown', key };
  if (text !== undefined) params.text = text;
  await cdpSend(tabId, 'Input.dispatchKeyEvent', params);
}

/** Key up */
async function cdpKeyUp(tabId, key, text) {
  const params = { type: 'keyUp', key };
  if (text !== undefined) params.text = text;
  await cdpSend(tabId, 'Input.dispatchKeyEvent', params);
}

/** Type a full string character by character */
async function cdpTypeText(tabId, keystrokes) {
  if (typeof keystrokes === 'string') {
    for (const char of keystrokes) {
      await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyDown', key: char, text: char });
      await sleep(20 + Math.random() * 20);
      await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: char, text: char });
      await sleep(30 + Math.random() * 60);
    }
    return;
  }
  for (const ks of keystrokes) {
    if (ks.delay_before_ms) await sleep(ks.delay_before_ms);
    if (ks.shift) await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 'Shift' });
    
    await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyDown', key: ks.key, text: ks.text });
    await sleep(20 + Math.random() * 20); // 20-40ms mechanical key press delay
    await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: ks.key, text: ks.text });
    
    if (ks.shift) await cdpSend(tabId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Shift' });
  }
}

/** Mouse wheel scroll */
async function cdpScroll(tabId, x, y, deltaX, deltaY) {
  await cdpSend(tabId, 'Input.dispatchMouseEvent', {
    type: 'mouseWheel',
    x,
    y,
    deltaX,
    deltaY
  });
}



// ─────────────────────────────────────────────────────────────────────────────
// Execution handler
// ─────────────────────────────────────────────────────────────────────────────
async function handleStartExecution(payload, sendResponse) {
  // License bypass: always valid

  if (!_ws || _ws.readyState !== WebSocket.OPEN) {
    sendResponse({ ok: false, error: 'Backend not connected. Ensure the AHA backend is running.' });
    return;
  }

  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    sendResponse({ ok: false, error: 'No active tab found.' });
    return;
  }

  if (tab.url && tab.url.startsWith('chrome://')) {
    sendResponse({ 
      ok: false, 
      error: 'You cannot run the agent on a chrome:// settings page! Please open the actual website (like https://www.facebook.com) in your browser tab first, then click the extension.' 
    });
    return;
  }

  // ─── Fetch Content from Local Storage Vault ───
  try {
    const { platform, daySlot, includeText, mediaType } = payload;
    let url = `http://127.0.0.1:8123/api/content?platform=${encodeURIComponent(platform)}&day=${daySlot}`;
    if (includeText) url += '&text=yes';
    if (mediaType && mediaType !== 'none') url += `&media=${mediaType.toLowerCase()}`;
    
    const vaultRes = await fetch(url);
    if (!vaultRes.ok) {
      throw new Error(`Local Storage Vault returned ${vaultRes.status}`);
    }
    
    const vaultData = await vaultRes.json();
    
    // Inject the fetched data into the payload so the backend can use it
    if (vaultData.textContent) payload.fetchedText = vaultData.textContent;
    if (vaultData.mediaDataUrl) {
      payload.fetchedMedia = vaultData.mediaDataUrl;
      payload.mediaMimeType = vaultData.mediaMimeType;
      payload.mediaAbsolutePath = vaultData.mediaAbsolutePath;
    }
    
  } catch (err) {
    console.error('[AHA BG] Storage Vault fetch error:', err);
    sendResponse({ 
      ok: false, 
      error: 'Cannot connect to Local Storage Vault on port 8123. Make sure the Storage Vault App is running. Error: ' + err.message 
    });
    return;
  }
  // ─────────────────────────────────────────────

  await chrome.storage.local.set({ executionStatus: 'executing' });
  notifyPopup({ type: 'STATUS_UPDATE', status: 'executing' });

  try {
    // Attach debugger to active tab
    await attachDebugger(tab.id);

    // Use isolated CDP vision to read screen layout invisibly
    const elements = await scanScreen(tab.id);

    // Send execution command to backend
    const sent = safeSend({
      type: 'execute',
      platform: payload.platform,
      slots: { 
        text: payload.fetchedText || '', 
        image: payload.mediaType === 'image', 
        video: payload.mediaType === 'video' 
      },
      day: payload.daySlot,
      elements: elements,
      viewport: { width: 1280, height: 800 }, // Can be static or grabbed
      currentMouse: { x: 0, y: 0 }
    });

    if (!sent) {
      throw new Error('Failed to send to backend. Ensure backend is connected.');
    }

    sendResponse({ ok: true, tabId: tab.id });
  } catch (err) {
    await chrome.storage.local.set({ executionStatus: 'idle' });
    notifyPopup({ type: 'STATUS_UPDATE', status: 'idle' });
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Status
// ─────────────────────────────────────────────────────────────────────────────
async function handleGetStatus(sendResponse) {
  const data = await chrome.storage.local.get([
    'wsConnected',
    'executionStatus'
  ]);
  sendResponse({
    ok: true,
    wsConnected:     data.wsConnected     ?? false,
    executionStatus: data.executionStatus ?? 'idle'
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Popup notification helper
// ─────────────────────────────────────────────────────────────────────────────
function notifyPopup(message) {
  chrome.runtime.sendMessage(message).catch(() => {
    // Popup may not be open — ignore
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility
// ─────────────────────────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot sequence
// ─────────────────────────────────────────────────────────────────────────────
(async () => {
  try {
    await setupAlarms();
    ensureWebSocket();
  } catch (err) {
    console.error('[AHA BG] Boot error:', err);
  }
})();

// ─────────────────────────────────────────────────────────────────────────────
// Visual Scanning Engine
// ─────────────────────────────────────────────────────────────────────────────
async function scanScreen(tabId) {
  const injectionResults = await chrome.scripting.executeScript({
    target: { tabId: tabId },
    world: "ISOLATED",
    func: () => {
      const elements = [];
      const addNode = (text, element) => {
        const cleanText = text ? text.trim() : '';
        if (!cleanText) return;
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        elements.push({
          text: cleanText,
          x: rect.left,
          y: rect.top,
          width: rect.width,
          height: rect.height,
          confidence: 100
        });
      };

      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      let node;
      while ((node = walker.nextNode())) {
        if (node.parentElement) addNode(node.nodeValue, node.parentElement);
      }

      const labeled = document.querySelectorAll('[aria-label], [title], img[alt], input[placeholder], textarea[placeholder], [data-placeholder]');
      for (const el of labeled) {
        const text = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('alt') || el.getAttribute('placeholder') || el.getAttribute('data-placeholder');
        addNode(text, el);
      }

      return elements;
    }
  });
  
  const elements = injectionResults[0].result;
  console.log("\n\n================ VISUAL NODES EXTRACTED ================");
  console.log(`Found ${elements.length} nodes.`);
  console.log("======================================================\n\n");
  return elements;
}
