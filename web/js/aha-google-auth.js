/**
 * Shared Google sign-in for marketing pages (subscribe, download, admin).
 * Uses redirect fallback when popups are blocked; persists session in localStorage.
 */
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
import {
  browserLocalPersistence,
  getAuth,
  getRedirectResult,
  GoogleAuthProvider,
  onAuthStateChanged,
  setPersistence,
  signInWithPopup,
  signInWithRedirect,
} from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js';

export const firebaseConfig = {
  apiKey: 'AIzaSyA_6P1QftvmS3_KM0v5kkCUOo7KP1eHPKw',
  authDomain: 'assist-daily.firebaseapp.com',
  projectId: 'assist-daily',
  storageBucket: 'assist-daily.firebasestorage.app',
  messagingSenderId: '204177096003',
  appId: '1:204177096003:web:03e82d5c4d5c8e489183f6',
  measurementId: 'G-PTDQSEND0N',
};

const POPUP_FALLBACK_CODES = new Set([
  'auth/popup-blocked',
  'auth/popup-closed-by-user',
  'auth/cancelled-popup-request',
  'auth/operation-not-supported-in-this-environment',
]);

export async function initGoogleAuth() {
  const auth = getAuth(initializeApp(firebaseConfig));
  await setPersistence(auth, browserLocalPersistence);
  const google = new GoogleAuthProvider();
  google.setCustomParameters({ prompt: 'select_account' });

  try {
    await getRedirectResult(auth);
  } catch (e) {
    console.warn('Google redirect sign-in:', e?.message || e);
  }

  return { auth, google };
}

export async function signInWithGoogle(auth, google) {
  try {
    await signInWithPopup(auth, google);
  } catch (e) {
    if (POPUP_FALLBACK_CODES.has(e?.code)) {
      await signInWithRedirect(auth, google);
      return;
    }
    throw e;
  }
}

export function watchAuth(auth, onUser) {
  return onAuthStateChanged(auth, onUser);
}

export async function notifyBackendSignIn(user) {
  try {
    const idToken = await user.getIdToken();
    await fetch('/api/auth/firebase_signin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    });
  } catch (e) {
    console.warn('Backend sign-in sync:', e?.message || e);
  }
}

export function formatAuthError(err) {
  const msg = (err?.message || String(err)).replace(/^Firebase:\s*/i, '');
  if (err?.code === 'auth/unauthorized-domain') {
    return msg + ' Add this site URL in Firebase Console → Authentication → Settings → Authorized domains.';
  }
  return msg;
}
