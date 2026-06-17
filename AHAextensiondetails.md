# AHA Chrome Extension — End-to-End Technical Documentation

This document outlines the complete technical architecture, workflows, and user journeys of the Artificial Human Assistant (AHA) Chrome Extension ecosystem.

---

## 1. System Architecture Overview

The AHA ecosystem is divided into three major components:

1. **Content Management (Manager Side)**
   - **Content Engine App**: A local Python desktop app used by content managers to create, organize, and export content (text, images, videos) into standardized `.zip` packages without worrying about naming conventions.
2. **Local Storage (User Side)**
   - **Storage Vault App**: A local Python desktop app run by the end-user. It imports the `.zip` packages and acts as a lightweight local server (`localhost:8123`) to serve media directly to the Chrome extension.
3. **Execution Engine (Browser + Cloud Backend)**
   - **Chrome Extension (MV3)**: The user-facing tool that acts as a "dumb client". It reads content locally, scans the screen, and executes physical browser actions.
   - **Cloud Backend (FastAPI)**: The central brain hosted on Render. It handles license validation, generates human-like physics (Bezier curves, typing delays), and dictates step-by-step actions to the extension via WebSockets.

---

## 2. What We Do (Content Managers)

The goal of the Content Manager is to prepare 30 days of social media content for the user.

1. **Open Content Engine App**: The manager runs `content_engine_app.py`.
2. **Create Content**: 
   - They select a platform (e.g., LinkedIn).
   - They select a day on the calendar (Day 1 to 30).
   - They paste the caption text and upload an image or video.
3. **Automated Saving**: The app automatically saves the files into the correct folder structure (e.g., `~/Downloads/aha/AI Pro/LinkedIn/Images/15AI.png`).
4. **Export**: Once the month is populated, the manager clicks **"Export ZIP"**, generating a ready-to-ship `AHA_Export.zip`. This file is then delivered to the end-user.

---

## 3. What Users Do (The End-User Experience)

The end-user wants a hands-free, automated posting experience that doesn't risk getting their social media accounts banned.

1. **License Activation**: The user installs the extension, clicks the icon, enters their purchased License Key, and clicks "Activate". (Tied permanently to their Chrome Profile).
2. **Importing Content**: The user opens the **Storage Vault App** (`storage_vault_app.py`), clicks "Import ZIP", and selects the `AHA_Export.zip` they received.
3. **Running the Server**: The Storage Vault App runs silently in the background, hosting a local HTTP server on port `8123`.
4. **Executing a Post**:
   - The user opens their target website (e.g., `linkedin.com`).
   - They open the AHA extension popup.
   - They type the platform name (`LinkedIn`), tick the `Text` box, select `Image` or `Video` media, and hit **Run Agent**.
   - They take their hands off the keyboard and watch AHA post like a human.

---

## 4. End-to-End Technical Flow (How It Works)

When the user clicks **Run Agent**, the following technical sequence occurs:

### Phase 1: Local Content Retrieval
1. The extension popup triggers a message to the service worker (`background.js`).
2. `background.js` makes a standard HTTP `fetch()` request to the local Storage Vault API:
   `http://127.0.0.1:8123/api/content?platform=LinkedIn&day=15`
3. The local Storage Vault returns the text caption and base64-encoded media for that specific day.

### Phase 2: Screen Analysis (OCR)
1. `background.js` uses `chrome.tabs.captureVisibleTab` to take a screenshot of the active page.
2. The screenshot data URL is sent to an invisible offscreen document (`ocr_offscreen.html`).
3. The offscreen document runs **Tesseract.js** (bundled locally) to perform Optical Character Recognition (OCR).
4. The OCR returns an array of on-screen elements containing recognized text and their exact `(x, y, width, height)` bounding boxes.

### Phase 3: Cloud Brain Orchestration (WebSocket)
1. `background.js` establishes a persistent WebSocket connection to the Cloud Backend (`wss://aha-cloud-brain.onrender.com/ws/agent`).
2. The extension sends a JSON payload containing:
   - `licenseKey` for validation
   - `platform` (e.g., linkedin)
   - `content` (text and base64 media)
   - `elements` (The OCR bounding boxes)
   - `viewport` dimensions and current mouse coordinates.

### Phase 4: Physics Generation (Backend)
1. The cloud backend parses the payload and instantiates a `SocialFlow` (e.g., `LinkedInFlow`).
2. The flow identifies the target buttons from the OCR data (e.g., finding the "Start a post" button).
3. The backend calculates human-like physics:
   - **Kinematic Engine**: Generates a Bezier curve trajectory to the target button, incorporating overshoot and randomized landing spots within the button bounds.
   - **Linguistic Engine**: Generates keystrokes with calculated delays, factoring in fatigue models and potential typo corrections.
4. The backend streams these commands back to the extension via the WebSocket in real-time.

### Phase 5: Browser Execution (CDP)
1. `background.js` receives the JSON commands (e.g., `move_mouse`, `click`, `type_text`, `upload_file`).
2. It attaches the `chrome.debugger` API to the active tab.
3. It translates the JSON commands into raw Chrome DevTools Protocol (CDP) events:
   - `Input.dispatchMouseEvent` for `mouseMoved`, `mousePressed`, `mouseReleased`.
   - `Input.dispatchKeyEvent` for `keyDown`, `keyUp`, `char`.
4. To handle file uploads safely, the backend sends an `upload_file` command. The extension intercepts the file input dialog and injects the downloaded media file directly via CDP.

### Phase 6: Keepalive & Lifecycle
- Manifest V3 limits service workers to 30 seconds of inactivity. 
- To prevent the extension from dying mid-execution, `background.js` registers a `chrome.alarms` trigger that fires every 24 seconds, instantly waking the service worker and ensuring the WebSocket remains connected.
