"""
Firebase Admin SDK initialisation and ID-token verification.

The service-account JSON path is read from the environment variable
FIREBASE_SERVICE_ACCOUNT_PATH (default: the file committed to the
workspace root during setup).  The credentials are loaded once and
reused for the lifetime of the process.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from fastapi import Request, HTTPException

_INITIALIZED = False


def _init_firebase() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        raise RuntimeError(
            "firebase-admin is not installed. Run: pip install firebase-admin"
        )

    if firebase_admin._apps:
        _INITIALIZED = True
        return

    # Prefer env var path, fall back to workspace-root file
    sa_path = os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT_PATH",
        str(Path(__file__).resolve().parent.parent / "assist-daily-firebase-adminsdk-fbsvc-6e2f5d3e18.json"),
    )

    sa_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json_str:
        cred = credentials.Certificate(json.loads(sa_json_str))
    elif Path(sa_path).exists():
        cred = credentials.Certificate(sa_path)
    else:
        raise RuntimeError(
            f"Firebase service account not found at '{sa_path}'. "
            "Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON."
        )

    firebase_admin.initialize_app(cred)
    _INITIALIZED = True


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded claims dict.

    Raises ValueError on invalid / expired tokens.
    """
    _init_firebase()
    from firebase_admin import auth

    try:
        return auth.verify_id_token(id_token)
    except Exception as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency — extract and verify the Firebase ID token.

    Clients send:  Authorization: Bearer <firebase-id-token>

    Returns the decoded token claims dict on success.
    Raises HTTP 401 on missing / invalid token.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Firebase ID token.")

    id_token = auth_header.removeprefix("Bearer ").strip()
    try:
        claims = verify_firebase_token(id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return claims
