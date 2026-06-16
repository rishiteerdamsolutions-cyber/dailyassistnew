/**
 * AHA Popup — popup.js (simplified)
 *
 * 3 inputs: Platform (dropdown), Text (yes/no), Media (none/image/video)
 * Run button always enabled once platform is selected.
 * No license checks. No vault picker.
 */

// ─── DOM References ──────────────────────────────────────────────────────────
const statusDot    = document.getElementById('statusDot');
const statusLabel  = document.getElementById('statusLabel');
const platformInput = document.getElementById('platformInput');
const runBtn       = document.getElementById('runBtn');
const logPanel     = document.getElementById('logPanel');
const logContent   = document.getElementById('logContent');
const footerWs     = document.getElementById('footerWs');

// ─── State ───────────────────────────────────────────────────────────────────
let currentStatus = 'idle';

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
async function init() {
  await refreshStatus();
  chrome.runtime.onMessage.addListener(handleBackgroundMessage);
}

// ─────────────────────────────────────────────────────────────────────────────
// Status
// ─────────────────────────────────────────────────────────────────────────────
async function refreshStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    if (!response?.ok) return;
    applyStatus(response.executionStatus ?? 'idle', response.wsConnected);
  } catch (err) {
    console.error('[AHA Popup] refreshStatus error:', err);
  }
}

function applyStatus(status, wsConnected) {
  currentStatus = status;

  statusDot.className = 'status-dot';
  statusDot.classList.add('status-dot--' + status);

  const labels = {
    idle: 'Idle',
    executing: 'Executing…',
    connected: 'Connected',
    disconnected: 'Disconnected'
  };
  statusLabel.textContent = labels[status] || status;

  if (wsConnected !== undefined) {
    footerWs.textContent = wsConnected ? 'Backend: ✓ Connected' : 'Backend: ✗ Disconnected';
    footerWs.className = 'footer-ws footer-ws--' + (wsConnected ? 'connected' : 'disconnected');
  }

  updateRunButton();
}

function handleBackgroundMessage(message) {
  if (message.type === 'STATUS_UPDATE') {
    refreshStatus();
  }
  if (message.type === 'EXECUTION_COMPLETE') {
    applyStatus('idle', undefined);
    appendLog(message.success ? '✅ Done!' : '❌ Failed: ' + message.message);
    refreshStatus();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Run button enable/disable — only needs platform selected + not executing
// ─────────────────────────────────────────────────────────────────────────────
platformInput.addEventListener('change', updateRunButton);

function updateRunButton() {
  const platformSelected = platformInput.value !== '';
  const notBusy = currentStatus !== 'executing';
  runBtn.disabled = !(platformSelected && notBusy);
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function getSelectedText() {
  const el = document.querySelector('input[name="textChoice"]:checked');
  return el ? el.value : 'no';
}

function getSelectedMedia() {
  const el = document.querySelector('input[name="mediaType"]:checked');
  return el ? el.value : 'none';
}

function getCurrentDaySlot() {
  return Math.min(new Date().getDate(), 30);
}

// ─────────────────────────────────────────────────────────────────────────────
// Run Agent
// ─────────────────────────────────────────────────────────────────────────────
runBtn.addEventListener('click', async () => {
  const platform = platformInput.value;
  if (!platform) return;

  runBtn.disabled = true;
  logPanel.hidden = false;
  appendLog('▶ Starting execution…');

  try {
    const daySlot   = getCurrentDaySlot();
    const includeText = getSelectedText() === 'yes';
    const mediaType = getSelectedMedia();

    const payload = { platform, daySlot, mediaType, includeText };

    appendLog('📡 Sending to backend: ' + platform + ' | Text: ' + (includeText ? 'Yes' : 'No') + ' | Media: ' + mediaType);

    const response = await chrome.runtime.sendMessage({
      type: 'START_EXECUTION',
      payload
    });

    if (response?.ok) {
      appendLog('✓ Execution started — waiting for backend…');
      applyStatus('executing', undefined);
    } else {
      appendLog('❌ Error: ' + (response?.error || 'Unknown error'));
      runBtn.disabled = false;
    }
  } catch (err) {
    console.error('[AHA Popup] Run error:', err);
    appendLog('❌ ' + err.message);
    runBtn.disabled = false;
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Log
// ─────────────────────────────────────────────────────────────────────────────
function appendLog(message) {
  logPanel.hidden = false;
  const line = document.createElement('div');
  line.className = 'log-line';
  const time = new Date().toLocaleTimeString();
  line.textContent = '[' + time + '] ' + message;
  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
init().catch(console.error);
