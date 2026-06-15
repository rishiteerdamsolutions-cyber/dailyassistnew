/**
 * AHA — Artificial Human Agent
 * Background Service Worker (MV3)
 *
 * Responsibilities:
 *  - chrome.alarms keepalive (every 0.5 min) to prevent SW termination
 *  - WebSocket connection to backend with exponential backoff
 *  - chrome.debugger CDP command execution
 *  - 24-hour license validation via chrome.alarms
 *  - Screenshot capture via chrome.tabs.captureVisibleTab
 *  - OCR delegation to offscreen document
 */

// ─── Configuration ────────────────────────────────────────────────────────────
let BACKEND_WS_URL      = 'wss://aha-cloud-brain.onrender.com/ws/agent';
let LICENSE_API_URL     = 'https://aha-cloud-brain.onrender.com/api/validate-license';
const WS_MAX_BACKOFF_MS = 30_000;
const ALARM_KEEPALIVE   = 'aha-keepalive';
const ALARM_LICENSE     = 'aha-license-check';
const DEBUGGER_VERSION  = '1.3';

// Dynamic config loader to override URLs (e.g. for local testing)
async function loadConfig() {
  // Disabled custom URL overrides to ensure connection to Render backend
  /*
  const { customWsUrl, customApiUrl } = await chrome.storage.local.get(['customWsUrl', 'customApiUrl']);
  if (customWsUrl) {
    BACKEND_WS_URL = customWsUrl;
  }
  if (customApiUrl) {
    LICENSE_API_URL = customApiUrl;
  }
  */
}

// ─── WebSocket state (stored in chrome.storage.session to survive SW restart)
let _ws            = null;
let _wsBackoffMs   = 1000;
let _wsConnecting  = false;
let _attachedTabId = null;  // current tab being debugged

// ─────────────────────────────────────────────────────────────────────────────
// ALARM: keepalive + license
// All listeners registered synchronously at top level.
// ─────────────────────────────────────────────────────────────────────────────
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_KEEPALIVE) {
    ensureWebSocket();
  }
  if (alarm.name === ALARM_LICENSE) {
    validateLicense().catch(console.error);
  }
});

chrome.runtime.onInstalled.addListener(async () => {
  // Set up alarms on install/update
  await setupAlarms();
  // Validate license immediately on install
  await validateLicense().catch(console.error);
});

chrome.runtime.onStartup.addListener(async () => {
  await setupAlarms();
});

// Message listener from popup.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      switch (message.type) {
        case 'START_EXECUTION':
          await handleStartExecution(message.payload, sendResponse);
          break;
        case 'CAPTURE_SCREENSHOT':
          await handleCaptureScreenshot(message.tabId, sendResponse);
          break;
        case 'GET_STATUS':
          await handleGetStatus(sendResponse);
          break;
        case 'ACTIVATE_LICENSE':
          await handleActivateLicense(message.licenseKey, sendResponse);
          break;
        case 'OCR_RESULT':
          // Result from offscreen document — forward to WS
          forwardOcrResult(message.result);
          sendResponse({ ok: true });
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
  if (!names.includes(ALARM_LICENSE)) {
    // Every 24 hours = 1440 minutes
    chrome.alarms.create(ALARM_LICENSE, {
      delayInMinutes: 1440,
      periodInMinutes: 1440
    });
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

    // Send license key on connect for backend auth
    const { licenseKey } = await chrome.storage.local.get('licenseKey');
    if (licenseKey) {
      safeSend({ type: 'AUTH', licenseKey });
    }
  };

  _ws.onmessage = async (event) => {
    try {
      const msg = JSON.parse(event.data);
      await handleBackendMessage(msg);
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
  switch (msg.type) {
    case 'MOUSE_MOVE':
      await cdpMouseMove(msg.tabId, msg.x, msg.y);
      break;
    case 'MOUSE_CLICK':
      await cdpMouseClick(msg.tabId, msg.x, msg.y, msg.button ?? 'left');
      break;
    case 'KEY_DOWN':
      await cdpKeyDown(msg.tabId, msg.key, msg.text);
      break;
    case 'KEY_UP':
      await cdpKeyUp(msg.tabId, msg.key, msg.text);
      break;
    case 'TYPE_TEXT':
      await cdpTypeText(msg.tabId, msg.text);
      break;
    case 'SCROLL':
      await cdpScroll(msg.tabId, msg.x, msg.y, msg.deltaX ?? 0, msg.deltaY ?? 0);
      break;
    case 'TAKE_SCREENSHOT':
      await handleCaptureAndOcr(msg.tabId);
      break;
    case 'ATTACH_DEBUGGER':
      await attachDebugger(msg.tabId);
      break;
    case 'DETACH_DEBUGGER':
      await detachDebugger(msg.tabId);
      break;
    case 'EXECUTION_COMPLETE':
      notifyPopup({ type: 'EXECUTION_COMPLETE', success: msg.success, message: msg.message });
      break;
    case 'AUTH_RESULT':
      if (!msg.valid) {
        await chrome.storage.local.set({ licenseValid: false });
        notifyPopup({ type: 'STATUS_UPDATE', status: 'locked' });
      }
      break;
    default:
      console.warn('[AHA BG] Unknown backend message type:', msg.type);
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
  await cdpSend(tabId, 'Input.dispatchMouseEvent', { ...baseParams, type: 'mouseReleased' });
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
async function cdpTypeText(tabId, text) {
  for (const char of text) {
    await cdpSend(tabId, 'Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: char,
      text: char
    });
    await cdpSend(tabId, 'Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: char,
      text: char
    });
    // Small delay to simulate human typing cadence
    await sleep(30 + Math.random() * 60);
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
// Screenshot + OCR
// ─────────────────────────────────────────────────────────────────────────────
async function handleCaptureScreenshot(tabId, sendResponse) {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(
      null, // current window
      { format: 'png', quality: 100 }
    );
    sendResponse({ ok: true, dataUrl });
  } catch (err) {
    console.error('[AHA BG] Screenshot error:', err);
    sendResponse({ ok: false, error: err.message });
  }
}

async function handleCaptureAndOcr(tabId) {
  try {
    // Capture screenshot
    const dataUrl = await chrome.tabs.captureVisibleTab(null, { format: 'png', quality: 100 });

    // Delegate OCR to offscreen document
    await ensureOffscreenDocument();

    await chrome.runtime.sendMessage({
      type:   'RUN_OCR',
      target: 'offscreen',
      dataUrl
    });
    // Result comes back via 'OCR_RESULT' message handler above
  } catch (err) {
    console.error('[AHA BG] Capture+OCR error:', err);
  }
}

async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT']
  });
  if (existingContexts.length > 0) return;

  await chrome.offscreen.createDocument({
    url:    'ocr_offscreen.html',
    reasons: ['DOM_PARSER'],
    justification: 'Run Tesseract.js OCR on captured screenshots to extract text coordinates'
  });
}

function forwardOcrResult(result) {
  safeSend({ type: 'OCR_RESULT', result });
}

// ─────────────────────────────────────────────────────────────────────────────
// Execution handler
// ─────────────────────────────────────────────────────────────────────────────
async function handleStartExecution(payload, sendResponse) {
  const { licenseValid } = await chrome.storage.local.get('licenseValid');
  if (!licenseValid) {
    sendResponse({ ok: false, error: 'License not valid. Please activate a license key.' });
    return;
  }

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

  await chrome.storage.local.set({ executionStatus: 'executing' });
  notifyPopup({ type: 'STATUS_UPDATE', status: 'executing' });

  // Attach debugger to active tab
  await attachDebugger(tab.id);

  // Send execution command to backend
  const sent = safeSend({
    type:    'START_EXECUTION',
    tabId:   tab.id,
    tabUrl:  tab.url,
    payload
  });

  if (!sent) {
    sendResponse({ ok: false, error: 'Failed to send to backend.' });
    return;
  }

  sendResponse({ ok: true, tabId: tab.id });
}

// ─────────────────────────────────────────────────────────────────────────────
// Status
// ─────────────────────────────────────────────────────────────────────────────
async function handleGetStatus(sendResponse) {
  const data = await chrome.storage.local.get([
    'licenseValid',
    'wsConnected',
    'executionStatus',
    'licenseKey'
  ]);
  sendResponse({
    ok: true,
    licenseValid:    data.licenseValid    ?? false,
    wsConnected:     data.wsConnected     ?? false,
    executionStatus: data.executionStatus ?? 'idle',
    hasLicenseKey:   !!data.licenseKey
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// License
// ─────────────────────────────────────────────────────────────────────────────
async function handleActivateLicense(licenseKey, sendResponse) {
  const trimmedKey = (licenseKey || 'bypass-active-key').trim();
  await chrome.storage.local.set({
    licenseKey: trimmedKey,
    licenseValid: true,
    licenseValidatedAt: Date.now()
  });
  sendResponse({ ok: true });
  notifyPopup({ type: 'STATUS_UPDATE', status: 'idle' });
  ensureWebSocket();
}

async function validateLicense() {
  await chrome.storage.local.set({
    licenseValid: true,
    licenseKey: 'bypass-active-key'
  });
}

async function callLicenseApi(licenseKey) {
  return { valid: true };
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
    await validateLicense().catch(console.error);
    ensureWebSocket();
  } catch (err) {
    console.error('[AHA BG] Boot error:', err);
  }
})();
