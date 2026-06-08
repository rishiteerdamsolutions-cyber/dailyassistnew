"""Persist the latest Firebase ID token for desktop → cloud API calls."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_SESSION_PATH = Path.home() / ".aha" / "firebase_session.json"


def save_firebase_session(
    *,
    id_token: str,
    uid: str,
    email: str = "",
) -> None:
    token = (id_token or "").strip()
    if not token:
        return
    _SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id_token": token,
        "uid": uid,
        "email": email,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _SESSION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_firebase_id_token() -> str | None:
    try:
        if not _SESSION_PATH.exists():
            return None
        data = json.loads(_SESSION_PATH.read_text(encoding="utf-8"))
        token = (data.get("id_token") or "").strip()
        return token or None
    except (OSError, json.JSONDecodeError):
        return None


def clear_firebase_session() -> None:
    try:
        if _SESSION_PATH.exists():
            _SESSION_PATH.unlink()
    except OSError:
        pass
