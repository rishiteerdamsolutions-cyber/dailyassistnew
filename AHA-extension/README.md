# AHA Chrome Extension — Developer Guide

## Quick Start

```bash
# 1. Generate icons (run once)
node extension/generate_icons.js

# 2. Download Tesseract.js assets (run once, requires internet)
node extension/download_tesseract.js

# 3. Load extension in Chrome
# chrome://extensions → Enable Developer Mode → Load Unpacked → select extension/
```

## Project Structure

```
AHA-extension/
└── extension/                  ← Load this folder in Chrome
    ├── manifest.json           ← MV3 manifest
    ├── background.js           ← Service worker (ES module)
    ├── popup.html              ← Extension popup UI
    ├── popup.js                ← Popup controller (ES module)
    ├── popup.css               ← Dark theme styles
    ├── ocr_offscreen.html      ← Offscreen document for OCR
    ├── ocr_offscreen.js        ← Tesseract.js OCR runner
    ├── vault_reader.js         ← IndexedDB + File System Access helpers
    ├── generate_icons.js       ← One-time icon generator (Node.js)
    ├── generate_icons.py       ← One-time icon generator (Python)
    ├── download_tesseract.js   ← One-time Tesseract asset downloader
    ├── icons/
    │   ├── icon16.png
    │   ├── icon48.png
    │   └── icon128.png
    └── tesseract/              ← Created by download_tesseract.js
        ├── tesseract.min.js
        ├── worker.min.js
        ├── tesseract-core.wasm.js
        └── lang-data/
            └── eng.traineddata.gz
```

## Backend Requirements

The extension expects two backend services on localhost:

| Service | Default | Purpose |
|---------|---------|---------|
| WebSocket | `ws://localhost:8765` | Receives screenshots + sends CDP commands |
| License API | `http://localhost:8766/validate-license` | POST `{ licenseKey }` → `{ valid: bool }` |

Change `BACKEND_WS_URL` and `LICENSE_API_URL` constants at the top of `background.js`.

## Vault File Structure

```
~/Downloads/aha/AI Pro/
├── LinkedIn/
│   ├── Texts/    1AI.txt … 30AI.txt
│   ├── Images/   1AI.png … 30AI.png
│   └── Videos/   1AI.mp4 … 30AI.mp4
├── Instagram/
│   └── ...
├── Facebook/
│   └── ...
├── X/
│   └── ...
└── WhatsApp/
    └── ...
```

Day slot = current `Date.getDate()` clamped to 1–30.

## WebSocket Protocol

### Extension → Backend

```jsonc
// Authenticate
{ "type": "AUTH", "licenseKey": "..." }

// Start a posting session
{ "type": "START_EXECUTION", "tabId": 123, "tabUrl": "...", "payload": {
    "platform": "LinkedIn",
    "daySlot": 14,
    "mediaType": "Image",
    "textContent": "Hello world",
    "mediaDataUrl": "data:image/png;base64,...",
    "mediaMimeType": "image/png"
}}

// OCR result (forwarded from offscreen)
{ "type": "OCR_RESULT", "result": [
    { "text": "Post", "x": 120, "y": 340, "width": 44, "height": 18, "confidence": 95 }
]}
```

### Backend → Extension

```jsonc
// Mouse actions
{ "type": "MOUSE_MOVE",  "tabId": 123, "x": 200, "y": 300 }
{ "type": "MOUSE_CLICK", "tabId": 123, "x": 200, "y": 300, "button": "left" }
{ "type": "SCROLL",      "tabId": 123, "x": 400, "y": 400, "deltaX": 0, "deltaY": 300 }

// Keyboard actions
{ "type": "KEY_DOWN",  "tabId": 123, "key": "Enter" }
{ "type": "KEY_UP",    "tabId": 123, "key": "Enter" }
{ "type": "TYPE_TEXT", "tabId": 123, "text": "Hello, LinkedIn!" }

// Debugger control
{ "type": "ATTACH_DEBUGGER",  "tabId": 123 }
{ "type": "DETACH_DEBUGGER",  "tabId": 123 }
{ "type": "TAKE_SCREENSHOT",  "tabId": 123 }

// Session complete
{ "type": "EXECUTION_COMPLETE", "success": true, "message": "Posted successfully." }
```

## Architecture

```
popup.js (File System Access API)
    │  chrome.runtime.sendMessage
    ▼
background.js (Service Worker)
    ├── chrome.alarms keepalive (every 0.5 min)
    ├── chrome.alarms license check (every 24h)
    ├── WebSocket ⟷ Backend (exponential backoff reconnect)
    ├── chrome.debugger → CDP commands on active tab
    └── chrome.tabs.captureVisibleTab → offscreen OCR
            │
            ▼
    ocr_offscreen.js (Offscreen Document)
        └── Tesseract.js (bundled locally)
```

## MV3 Constraints Addressed

| Constraint | Solution |
|-----------|----------|
| SW is ephemeral | `chrome.alarms` keepalive every 0.5 min |
| No persistent WS | Reconnect on alarm + exponential backoff |
| File System API blocked in SW | Called only from `popup.js` |
| CDN scripts blocked by CSP | Tesseract bundled locally via `download_tesseract.js` |
| No inline scripts in HTML | All HTML uses `<script src="...">` |
| Offscreen API restrictions | Only `chrome.runtime` messaging used in `ocr_offscreen.js` |
| FileSystemHandle not serialisable | IndexedDB used in `vault_reader.js` |
