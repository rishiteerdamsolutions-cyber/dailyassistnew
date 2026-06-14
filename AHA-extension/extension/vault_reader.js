/**
 * AHA — vault_reader.js
 *
 * ES module for persisting FileSystemDirectoryHandle to IndexedDB.
 * File System Access API handles cannot be stored in chrome.storage —
 * IndexedDB is the only way to persist them across popup sessions.
 *
 * Used by popup.js (runs in extension popup page context).
 */

const DB_NAME       = 'aha-vault-db';
const DB_VERSION    = 1;
const STORE_NAME    = 'handles';
const HANDLE_KEY    = 'vaultDirectoryHandle';

// ─────────────────────────────────────────────────────────────────────────────
// IndexedDB helpers
// ─────────────────────────────────────────────────────────────────────────────

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };

    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror   = (event) => reject(event.target.error);
  });
}

/**
 * Persist a FileSystemDirectoryHandle to IndexedDB.
 * IndexedDB natively supports the FileSystemHandle type.
 *
 * @param {FileSystemDirectoryHandle} handle
 */
export async function saveDirectoryHandle(handle) {
  const db = await openDatabase();

  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.put(handle, HANDLE_KEY);

    req.onsuccess = () => resolve();
    req.onerror   = (e) => reject(e.target.error);

    tx.oncomplete = () => db.close();
    tx.onerror    = (e) => reject(e.target.error);
  });
}

/**
 * Load the persisted FileSystemDirectoryHandle from IndexedDB.
 * Returns null if no handle has been saved yet.
 *
 * @returns {Promise<FileSystemDirectoryHandle|null>}
 */
export async function loadDirectoryHandle() {
  let db;
  try {
    db = await openDatabase();
  } catch (err) {
    console.error('[AHA VaultReader] openDatabase error:', err);
    return null;
  }

  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.get(HANDLE_KEY);

    req.onsuccess = async (event) => {
      const handle = event.target.result;

      if (!handle) {
        db.close();
        resolve(null);
        return;
      }

      // Verify the handle is still accessible (user may have revoked permission)
      try {
        const permState = await handle.queryPermission({ mode: 'read' });
        if (permState === 'granted') {
          db.close();
          resolve(handle);
          return;
        }

        // Permission not granted — return handle anyway (caller will re-request)
        db.close();
        resolve(handle);
      } catch (permErr) {
        console.warn('[AHA VaultReader] Permission check failed:', permErr);
        db.close();
        resolve(handle);
      }
    };

    req.onerror = (e) => {
      db.close();
      reject(e.target.error);
    };
  });
}

/**
 * Clear the stored directory handle (e.g., if it becomes invalid).
 */
export async function clearDirectoryHandle() {
  const db = await openDatabase();

  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.delete(HANDLE_KEY);

    req.onsuccess = () => resolve();
    req.onerror   = (e) => reject(e.target.error);

    tx.oncomplete = () => db.close();
    tx.onerror    = (e) => reject(e.target.error);
  });
}

/**
 * Resolve a relative path array from a root handle.
 * e.g. resolveRelativePath(root, ['LinkedIn', 'Texts']) → dir handle
 *
 * @param {FileSystemDirectoryHandle} rootHandle
 * @param {string[]} pathParts
 * @returns {Promise<FileSystemDirectoryHandle>}
 */
export async function resolveRelativePath(rootHandle, pathParts) {
  let current = rootHandle;
  for (const part of pathParts) {
    try {
      current = await current.getDirectoryHandle(part, { create: false });
    } catch {
      throw new Error(`Directory not found: ${pathParts.join('/')} (failed at "${part}")`);
    }
  }
  return current;
}

/**
 * Read a file from the vault as text.
 *
 * @param {FileSystemDirectoryHandle} rootHandle  - The vault root (AI Pro/)
 * @param {string} platform                       - e.g. "LinkedIn"
 * @param {number} daySlot                        - 1–30
 * @returns {Promise<string>}
 */
export async function readTextFile(rootHandle, platform, daySlot) {
  const dir = await resolveRelativePath(rootHandle, [platform, 'Texts']);
  const fileName = `${daySlot}AI.txt`;

  let fileHandle;
  try {
    fileHandle = await dir.getFileHandle(fileName, { create: false });
  } catch {
    throw new Error(`File not found in vault: ${platform}/Texts/${fileName}`);
  }

  const file = await fileHandle.getFile();
  return file.text();
}

/**
 * Read a media file (image or video) from the vault as ArrayBuffer.
 *
 * @param {FileSystemDirectoryHandle} rootHandle
 * @param {string} platform   - e.g. "Instagram"
 * @param {number} daySlot    - 1–30
 * @param {'Image'|'Video'} mediaType
 * @returns {Promise<{ buffer: ArrayBuffer, mimeType: string, fileName: string }>}
 */
export async function readMediaFile(rootHandle, platform, daySlot, mediaType) {
  const subfolder  = mediaType === 'Image' ? 'Images' : 'Videos';
  const ext        = mediaType === 'Image' ? 'png'    : 'mp4';
  const fileName   = `${daySlot}AI.${ext}`;
  const mimeType   = mediaType === 'Image' ? 'image/png' : 'video/mp4';

  const dir = await resolveRelativePath(rootHandle, [platform, subfolder]);

  let fileHandle;
  try {
    fileHandle = await dir.getFileHandle(fileName, { create: false });
  } catch {
    throw new Error(`File not found in vault: ${platform}/${subfolder}/${fileName}`);
  }

  const file   = await fileHandle.getFile();
  const buffer = await file.arrayBuffer();
  return { buffer, mimeType, fileName };
}
