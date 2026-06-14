#!/usr/bin/env node
/**
 * AHA Extension — Tesseract.js Asset Downloader
 *
 * Downloads all required Tesseract.js files for offline/bundled use.
 * Chrome MV3 CSP blocks CDN scripts, so all JS must be local.
 *
 * Usage:
 *   node download_tesseract.js
 *
 * After running, you'll have:
 *   extension/tesseract/tesseract.min.js
 *   extension/tesseract/worker.min.js
 *   extension/tesseract/tesseract-core.wasm.js
 *   extension/tesseract/lang-data/eng.traineddata.gz
 */

const https = require('https');
const fs    = require('fs');
const path  = require('path');

const TESSERACT_VERSION = '5.0.4';
const BASE_URL = `https://cdn.jsdelivr.net/npm/tesseract.js@${TESSERACT_VERSION}/dist/`;
const LANG_URL = `https://tessdata.projectnaptha.com/4.0.0/`;

const outDir = path.join(__dirname, 'tesseract');
const langDir = path.join(outDir, 'lang-data');

fs.mkdirSync(outDir,  { recursive: true });
fs.mkdirSync(langDir, { recursive: true });

function download(url, destPath) {
  return new Promise((resolve, reject) => {
    console.log(`⬇  ${url}`);
    const file = fs.createWriteStream(destPath);

    function get(url) {
      https.get(url, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302) {
          get(res.headers.location);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} for ${url}`));
          return;
        }
        res.pipe(file);
        file.on('finish', () => { file.close(); resolve(destPath); });
      }).on('error', (err) => {
        fs.unlink(destPath, () => {});
        reject(err);
      });
    }

    get(url);
  });
}

async function main() {
  const files = [
    { url: `${BASE_URL}tesseract.min.js`,        dest: path.join(outDir, 'tesseract.min.js') },
    { url: `${BASE_URL}worker.min.js`,           dest: path.join(outDir, 'worker.min.js') },
    { url: `${BASE_URL}tesseract-core.wasm.js`,  dest: path.join(outDir, 'tesseract-core.wasm.js') },
    { url: `${LANG_URL}eng.traineddata.gz`,       dest: path.join(langDir, 'eng.traineddata.gz') },
  ];

  for (const { url, dest } of files) {
    try {
      await download(url, dest);
      console.log(`   ✓ ${path.relative(__dirname, dest)}`);
    } catch (err) {
      console.error(`   ✗ Failed: ${err.message}`);
      process.exitCode = 1;
    }
  }

  console.log('\nDone. Tesseract.js assets are ready for offline use.');
  console.log('Make sure to add the tesseract/ directory to your extension ZIP.');
}

main();
