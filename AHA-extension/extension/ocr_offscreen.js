/**
 * AHA — ocr_offscreen.js
 *
 * Runs in the offscreen document (chrome.offscreen API, Chrome 109+).
 * Receives image dataURLs from background.js via chrome.runtime.onMessage,
 * runs Tesseract.js OCR, and returns structured word-level bounding boxes.
 *
 * Available APIs here:
 *   ✓ chrome.runtime.sendMessage / onMessage
 *   ✓ Standard Web APIs (DOM, Canvas, fetch, etc.)
 *   ✗ chrome.tabs, chrome.downloads, chrome.action — NOT available
 *
 * Tesseract.js is loaded via <script> tag from the bundled local file.
 * Do NOT load from CDN — MV3 CSP blocks remote scripts.
 */

'use strict';

// Tesseract.js is loaded as a global from tesseract/tesseract.min.js
// Verify it loaded before registering the listener.
if (typeof Tesseract === 'undefined') {
  console.error('[AHA OCR] Tesseract.js not loaded! Check tesseract/tesseract.min.js path.');
}

/** @type {Tesseract.Worker|null} */
let _worker = null;
let _workerReady = false;

/**
 * Initialise Tesseract worker once.
 * Worker is reused across multiple OCR calls to amortize startup cost.
 */
async function initWorker() {
  if (_worker && _workerReady) return _worker;

  // Tesseract.js v4+ API: createWorker(lang, oem, options)
  // workerPath and langPath must point to bundled files (not CDN).
  _worker = await Tesseract.createWorker('eng', 1, {
    workerPath:   chrome.runtime.getURL('tesseract/worker.min.js'),
    langPath:     chrome.runtime.getURL('tesseract/lang-data/'),
    corePath:     chrome.runtime.getURL('tesseract/tesseract-core.wasm.js'),
    logger:       (m) => { /* suppress verbose Tesseract logs */ }
  });

  _workerReady = true;
  return _worker;
}

/**
 * Run OCR on a dataURL image.
 *
 * @param {string} dataUrl - base64 data URL of the screenshot
 * @returns {Promise<Array<{text: string, x: number, y: number, width: number, height: number}>>}
 */
async function runOcr(dataUrl) {
  const worker = await initWorker();

  const { data } = await worker.recognize(dataUrl);

  // Extract word-level results with bounding boxes
  const results = [];
  for (const block of data.blocks) {
    for (const paragraph of block.paragraphs) {
      for (const line of paragraph.lines) {
        for (const word of line.words) {
          const { text, bbox, confidence } = word;
          const cleanText = text.trim();
          if (!cleanText || confidence < 30) continue;

          results.push({
            text:       cleanText,
            confidence: Math.round(confidence),
            x:          bbox.x0,
            y:          bbox.y0,
            width:      bbox.x1 - bbox.x0,
            height:     bbox.y1 - bbox.y0
          });
        }
      }
    }
  }

  return results;
}

// ─────────────────────────────────────────────────────────────────────────────
// Message listener
// Only chrome.runtime.onMessage is available in offscreen documents.
// ─────────────────────────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Only handle messages directed at this offscreen document
  if (message.target !== 'offscreen') return false;

  if (message.type === 'RUN_OCR') {
    (async () => {
      try {
        if (!message.dataUrl || typeof message.dataUrl !== 'string') {
          throw new Error('Invalid dataUrl provided for OCR.');
        }

        const result = await runOcr(message.dataUrl);

        // Send OCR results back to the service worker
        await chrome.runtime.sendMessage({
          type:   'OCR_RESULT',
          result
        });

        sendResponse({ ok: true, count: result.length });
      } catch (err) {
        console.error('[AHA OCR] Error:', err);
        await chrome.runtime.sendMessage({
          type:   'OCR_RESULT',
          result: [],
          error:  err.message
        }).catch(() => {}); // background may have terminated
        sendResponse({ ok: false, error: err.message });
      }
    })();

    return true; // keep channel open
  }

  if (message.type === 'TERMINATE_WORKER') {
    (async () => {
      try {
        if (_worker) {
          await _worker.terminate();
          _worker      = null;
          _workerReady = false;
        }
        sendResponse({ ok: true });
      } catch (err) {
        sendResponse({ ok: false, error: err.message });
      }
    })();
    return true;
  }

  return false;
});

// Pre-warm worker on load to reduce first-OCR latency
initWorker().catch(err => {
  console.error('[AHA OCR] Worker pre-warm failed:', err);
});
