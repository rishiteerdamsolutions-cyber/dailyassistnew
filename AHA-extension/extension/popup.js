/**
 * AHA Popup — popup.js
 *
 * Handles:
 *  - Platform validation (5 allowed values)
 *  - Text slot toggle
 *  - Media type radio (Image | Video | None)
 *  - Vault directory picker (File System Access API — IndexedDB for handle)
 *  - Vault file reading for today's day slot
 *  - chrome.runtime.sendMessage to background.js
 *  - Status updates from background.js
 *  - License activation form
 */

import { saveDirectoryHandle, loadDirectoryHandle } from './vault_reader.js';

// ─── Constants ───────────────────────────────────────────────────────────────
const VALID_PLATFORMS = ['linkedin', 'instagram', 'facebook', 'x', 'whatsapp'];

// ─── DOM References ──────────────────────────────────────────────────────────
const statusDot        = document.getElementById('statusDot');
const statusLabel      = document.getElementById('statusLabel');
const licenseSection   = document.getElementById('licenseSection');
const mainForm         = document.getElementById('mainForm');
const licenseKeyInput  = document.getElementById('licenseKeyInput');
const licenseError     = document.getElementById('licenseError');
const activateLicenseBtn = document.getElementById('activateLicenseBtn');

const platformInput    = document.getElementById('platformInput');
const platformIcon     = document.getElementById('platformIcon');
const platformError    = document.getElementById('platformError');

const textToggle       = document.getElementById('textToggle');
const textSlot         = document.getElementById('textSlot');
const textFilePath     = document.getElementById('textFilePath');

const mediaRadios      = document.querySelectorAll('input[name="mediaType"]');
const mediaVaultInfo   = document.getElementById('mediaVaultInfo');
const mediaFilePath    = document.getElementById('mediaFilePath');

const pickVaultBtn     = document.getElementById('pickVaultBtn');
const vaultPathDisplay = document.getElementById('vaultPathDisplay');

const runBtn           = document.getElementById('runBtn');
const logPanel         = document.getElementById('logPanel');
const logContent       = document.getElementById('logContent');
const footerWs         = document.getElementById('footerWs');

// ─── State ───────────────────────────────────────────────────────────────────
let currentStatus     = 'idle';
let platformValid     = false;
let vaultHandle       = null;  // FileSystemDirectoryHandle

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
async function init() {
  // Load status from background
  await refreshStatus();

  // Try to restore vault directory handle from IndexedDB
  try {
    const handle = await loadDirectoryHandle();
    if (handle) {
      vaultHandle = handle;
      vaultPathDisplay.textContent = handle.name;
      vaultPathDisplay.classList.add('has-path');
    }
  } catch (err) {
    console.warn('[AHA Popup] Could not restore vault handle:', err);
  }

  // Listen for background messages
  chrome.runtime.onMessage.addListener(handleBackgroundMessage);
}

// ─────────────────────────────────────────────────────────────────────────────
// Status management
// ─────────────────────────────────────────────────────────────────────────────
async function refreshStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    if (!response?.ok) return;

    applyStatus(
      response.licenseValid ? (response.executionStatus ?? 'idle') : 'locked',
      response.wsConnected
    );
  } catch (err) {
    console.error('[AHA Popup] refreshStatus error:', err);
  }
}

function applyStatus(status, wsConnected) {
  currentStatus = status;

  // Status dot classes
  statusDot.className = 'status-dot';
  statusDot.classList.add(`status-dot--${status}`);

  const labels = {
    idle:       'Idle',
    executing:  'Executing…',
    locked:     'Locked',
    connected:  'Connected',
    disconnected: 'Disconnected'
  };
  statusLabel.textContent = labels[status] ?? status;

  // Show/hide license section vs main form
  if (status === 'locked') {
    licenseSection.hidden = false;
    mainForm.hidden = true;
  } else {
    licenseSection.hidden = true;
    mainForm.hidden = false;
  }

  // Footer WS status
  footerWs.textContent = wsConnected ? 'Backend: ✓ Connected' : 'Backend: ✗ Disconnected';
  footerWs.className = `footer-ws footer-ws--${wsConnected ? 'connected' : 'disconnected'}`;

  // Run button state
  updateRunButton();
}

function handleBackgroundMessage(message) {
  if (message.type === 'STATUS_UPDATE') {
    applyStatus(message.status, undefined);
    // Re-fetch full status to get wsConnected
    refreshStatus();
  }
  if (message.type === 'EXECUTION_COMPLETE') {
    applyStatus('idle', undefined);
    appendLog(message.success ? '✅ Execution complete.' : `❌ Failed: ${message.message}`);
    refreshStatus();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Platform validation
// ─────────────────────────────────────────────────────────────────────────────
platformInput.addEventListener('input', () => {
  const raw = platformInput.value.trim().toLowerCase();
  platformValid = VALID_PLATFORMS.includes(raw);

  if (raw.length === 0) {
    setFieldState(platformInput, platformIcon, platformError, 'empty', '');
  } else if (platformValid) {
    setFieldState(platformInput, platformIcon, platformError, 'valid', '');
  } else {
    setFieldState(
      platformInput,
      platformIcon,
      platformError,
      'invalid',
      `"${platformInput.value.trim()}" is not a supported platform.`
    );
  }

  updateFilePaths();
  updateRunButton();
});

function setFieldState(input, icon, errorEl, state, errorMsg) {
  input.className = 'form-input';
  if (state === 'valid')   { input.classList.add('form-input--valid');   icon.textContent = '✓'; }
  if (state === 'invalid') { input.classList.add('form-input--invalid'); icon.textContent = '✗'; }
  if (state === 'empty')   { icon.textContent = ''; }

  if (errorMsg) {
    errorEl.textContent = errorMsg;
    errorEl.hidden = false;
  } else {
    errorEl.hidden = true;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Text toggle
// ─────────────────────────────────────────────────────────────────────────────
textToggle.addEventListener('change', () => {
  textSlot.hidden = !textToggle.checked;
  updateFilePaths();
  updateRunButton();
});

// ─────────────────────────────────────────────────────────────────────────────
// Media type
// ─────────────────────────────────────────────────────────────────────────────
mediaRadios.forEach(radio => {
  radio.addEventListener('change', () => {
    const selected = getSelectedMedia();
    mediaVaultInfo.hidden = (selected === 'none');
    updateFilePaths();
    updateRunButton();
  });
});

function getSelectedMedia() {
  for (const r of mediaRadios) {
    if (r.checked) return r.value;
  }
  return 'none';
}

// ─────────────────────────────────────────────────────────────────────────────
// File path preview
// ─────────────────────────────────────────────────────────────────────────────
function updateFilePaths() {
  const platform  = platformInput.value.trim();
  const daySlot   = getCurrentDaySlot();
  const mediaType = getSelectedMedia();

  if (platformValid) {
    const platformFormatted = normalizeplatform(platform);

    if (textToggle.checked) {
      textFilePath.textContent = `${platformFormatted}/Texts/${daySlot}AI.txt`;
    }

    if (mediaType === 'Image') {
      mediaFilePath.textContent = `${platformFormatted}/Images/${daySlot}AI.png`;
    } else if (mediaType === 'Video') {
      mediaFilePath.textContent = `${platformFormatted}/Videos/${daySlot}AI.mp4`;
    }
  } else {
    textFilePath.textContent  = '—';
    mediaFilePath.textContent = '—';
  }
}

function normalizeplatform(raw) {
  const map = {
    linkedin:  'LinkedIn',
    instagram: 'Instagram',
    facebook:  'Facebook',
    x:         'X',
    whatsapp:  'WhatsApp'
  };
  return map[raw.toLowerCase()] ?? raw;
}

function getCurrentDaySlot() {
  // Day 1–30 cycling based on current date of month
  const day = new Date().getDate();
  return Math.min(day, 30);
}

// ─────────────────────────────────────────────────────────────────────────────
// Vault directory picker — File System Access API
// MUST be called from popup.js (cannot use from service worker)
// Handle stored in IndexedDB (cannot serialize to chrome.storage)
// ─────────────────────────────────────────────────────────────────────────────
pickVaultBtn.addEventListener('click', async () => {
  try {
    // showDirectoryPicker MUST be called from a user gesture in an extension page
    const handle = await window.showDirectoryPicker({
      id: 'aha-vault',
      mode: 'read',
      startIn: 'downloads'
    });

    vaultHandle = handle;
    vaultPathDisplay.textContent = handle.name;
    vaultPathDisplay.classList.add('has-path');

    // Persist handle to IndexedDB
    await saveDirectoryHandle(handle);

    appendLog(`📁 Vault set: ${handle.name}`);
    updateRunButton();
  } catch (err) {
    if (err.name === 'AbortError') return; // User cancelled
    console.error('[AHA Popup] Directory picker error:', err);
    appendLog(`❌ Could not open vault: ${err.message}`);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Run button
// ─────────────────────────────────────────────────────────────────────────────
function updateRunButton() {
  const canRun = (
    platformValid &&
    currentStatus !== 'locked' &&
    currentStatus !== 'executing' &&
    vaultHandle !== null
  );
  runBtn.disabled = !canRun;
}

runBtn.addEventListener('click', async () => {
  if (!platformValid || !vaultHandle) return;

  runBtn.disabled = true;
  logPanel.hidden = false;
  appendLog('▶ Starting execution…');

  try {
    const platform  = normalizeplatform(platformInput.value.trim());
    const daySlot   = getCurrentDaySlot();
    const mediaType = getSelectedMedia();

    // Read files from vault using File System Access API (popup context only)
    const payload = { platform, daySlot, mediaType };

    if (textToggle.checked) {
      appendLog(`📄 Reading text file: ${platform}/Texts/${daySlot}AI.txt`);
      const textContent = await readVaultText(platform, daySlot);
      payload.textContent = textContent;
      appendLog(`✓ Text loaded (${textContent.length} chars)`);
    }

    if (mediaType === 'Image') {
      appendLog(`🖼 Reading image: ${platform}/Images/${daySlot}AI.png`);
      const { dataUrl, mimeType } = await readVaultMedia(platform, daySlot, 'Images', 'png');
      payload.mediaDataUrl = dataUrl;
      payload.mediaMimeType = mimeType;
      appendLog('✓ Image loaded');
    } else if (mediaType === 'Video') {
      appendLog(`🎬 Reading video: ${platform}/Videos/${daySlot}AI.mp4`);
      const { dataUrl, mimeType } = await readVaultMedia(platform, daySlot, 'Videos', 'mp4');
      payload.mediaDataUrl = dataUrl;
      payload.mediaMimeType = mimeType;
      appendLog('✓ Video loaded');
    }

    const response = await chrome.runtime.sendMessage({
      type: 'START_EXECUTION',
      payload
    });

    if (response?.ok) {
      appendLog('✓ Execution started — waiting for backend…');
      applyStatus('executing', undefined);
    } else {
      appendLog(`❌ Error: ${response?.error ?? 'Unknown error'}`);
      runBtn.disabled = false;
    }
  } catch (err) {
    console.error('[AHA Popup] Run error:', err);
    appendLog(`❌ ${err.message}`);
    runBtn.disabled = false;
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Vault file reading (File System Access API — from popup context)
// ─────────────────────────────────────────────────────────────────────────────
async function getVaultSubdirHandle(platform, subfolder) {
  if (!vaultHandle) throw new Error('Vault directory not set. Please pick the vault folder.');

  // Navigate: <root> / <Platform> / <subfolder>
  // vaultHandle should already be pointing at ~/Downloads/aha/AI Pro/
  // or the user may have selected <root> = "AI Pro"
  // We try platform folder first, then platform/subfolder
  let platformDir;
  try {
    platformDir = await vaultHandle.getDirectoryHandle(platform, { create: false });
  } catch {
    // Maybe vault root IS the platform folder?
    // Try treating vaultHandle as the platform folder itself
    platformDir = vaultHandle;
  }

  let subDir;
  try {
    subDir = await platformDir.getDirectoryHandle(subfolder, { create: false });
  } catch {
    throw new Error(`Folder not found: ${platform}/${subfolder}/`);
  }
  return subDir;
}

async function readVaultText(platform, daySlot) {
  const dir = await getVaultSubdirHandle(platform, 'Texts');
  const fileName = `${daySlot}AI.txt`;

  let fileHandle;
  try {
    fileHandle = await dir.getFileHandle(fileName, { create: false });
  } catch {
    throw new Error(`File not found: ${platform}/Texts/${fileName}`);
  }

  const file = await fileHandle.getFile();
  return await file.text();
}

async function readVaultMedia(platform, daySlot, subfolder, ext) {
  const dir = await getVaultSubdirHandle(platform, subfolder);
  const fileName = `${daySlot}AI.${ext}`;

  let fileHandle;
  try {
    fileHandle = await dir.getFileHandle(fileName, { create: false });
  } catch {
    throw new Error(`File not found: ${platform}/${subfolder}/${fileName}`);
  }

  const file = await fileHandle.getFile();
  const arrayBuffer = await file.arrayBuffer();
  const base64 = arrayBufferToBase64(arrayBuffer);
  const mimeType = file.type || guessMimeType(ext);
  return { dataUrl: `data:${mimeType};base64,${base64}`, mimeType };
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function guessMimeType(ext) {
  const map = { png: 'image/png', jpg: 'image/jpeg', mp4: 'video/mp4' };
  return map[ext] ?? 'application/octet-stream';
}

// ─────────────────────────────────────────────────────────────────────────────
// License activation
// ─────────────────────────────────────────────────────────────────────────────
activateLicenseBtn.addEventListener('click', async () => {
  const key = licenseKeyInput.value.trim();
  if (!key) {
    licenseError.textContent = 'Please enter a license key.';
    licenseError.hidden = false;
    return;
  }

  licenseError.hidden = true;
  activateLicenseBtn.disabled = true;
  activateLicenseBtn.textContent = 'Validating…';

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'ACTIVATE_LICENSE',
      licenseKey: key
    });

    if (response?.ok) {
      appendLog('✅ License activated successfully.');
      await refreshStatus();
    } else {
      licenseError.textContent = response?.error ?? 'Activation failed.';
      licenseError.hidden = false;
    }
  } catch (err) {
    licenseError.textContent = err.message;
    licenseError.hidden = false;
  } finally {
    activateLicenseBtn.disabled = false;
    activateLicenseBtn.textContent = 'Activate License';
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Log panel
// ─────────────────────────────────────────────────────────────────────────────
function appendLog(message) {
  logPanel.hidden = false;
  const line = document.createElement('div');
  line.className = 'log-line';
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${message}`;
  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
init().catch(console.error);
