"""
Firebase Admin SDK initialisation and ID-token verification.

Vercel / cloud: set FIREBASE_SERVICE_ACCOUNT_JSON to the **entire** service
account JSON (one line). Do not paste only the private_key PEM.

Local: set FIREBASE_SERVICE_ACCOUNT_PATH to the downloaded .json file path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import HTTPException, Request

_INITIALIZED = False

_PEM_START = "-----BEGIN"


def _parse_service_account_json(raw: str) -> dict:
    """Parse service account JSON from env (supports escaped newlines in private_key)."""
    text = raw.strip()
    if text.startswith(_PEM_START):
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must be the full service account JSON "
            "(type, project_id, private_key, client_email, …), not only the private_key PEM. "
            "Firebase Console → Project settings → Service accounts → Generate new private key → "
            "paste the whole .json file as one line."
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON. Paste the complete "
            "service account file as a single line."
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must be a JSON object (service account file)."
        )
    if data.get("type") != "service_account":
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must have \"type\": \"service_account\"."
        )
    return data


def _on_vercel() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


def firebase_env_diagnostics() -> dict:
    """Safe deploy check — no secrets returned."""
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    diag: dict = {
        "on_vercel": _on_vercel(),
        "has_json_env": bool(raw),
        "json_char_count": len(raw),
        "json_looks_like_pem_only": raw.startswith(_PEM_START),
        "json_starts_with_brace": raw.startswith("{"),
        "has_path_env": bool(path),
        "path_looks_like_pem": path.startswith(_PEM_START),
        "path_is_existing_file": bool(path and Path(path).is_file()),
    }
    if raw:
        try:
            data = _parse_service_account_json(raw)
            diag["json_valid"] = True
            diag["project_id"] = data.get("project_id")
            diag["client_email"] = (data.get("client_email") or "")[:3] + "***"
        except Exception as exc:
            diag["json_valid"] = False
            diag["json_error"] = str(exc)
    else:
        diag["json_valid"] = False
        diag["json_error"] = "FIREBASE_SERVICE_ACCOUNT_JSON is empty in this environment."
    return diag


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

    sa_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()

    if sa_path.startswith(_PEM_START):
        raise RuntimeError(
            "Remove FIREBASE_SERVICE_ACCOUNT_PATH from Vercel (it contains the private key PEM). "
            "Use only FIREBASE_SERVICE_ACCOUNT_JSON with the full downloaded .json file."
        )

    if sa_json_str:
        cred = credentials.Certificate(_parse_service_account_json(sa_json_str))
    elif _on_vercel():
        raise RuntimeError(
            "On Vercel, FIREBASE_SERVICE_ACCOUNT_JSON must be set for Production (and Preview if you test there). "
            "Paste the entire service account .json as one line. Remove FIREBASE_SERVICE_ACCOUNT_PATH."
        )
    else:
        default_path = str(
            Path(__file__).resolve().parent.parent
            / "assist-daily-firebase-adminsdk-fbsvc-6e2f5d3e18.json"
        )
        local_path = sa_path or default_path
        if local_path.startswith("{"):
            cred = credentials.Certificate(_parse_service_account_json(local_path))
        elif Path(local_path).is_file():
            cred = credentials.Certificate(local_path)
        else:
            raise RuntimeError(
                f"Firebase service account file not found: {local_path!r}. "
                "Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH."
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
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return claims
