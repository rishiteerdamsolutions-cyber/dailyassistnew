"""Admin access — Firebase email allowlist (+ optional secret for automation)."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request

from aha.firebase_auth import get_current_user

_ADMIN_SECRET = os.environ.get("AHA_ADMIN_SECRET", "").strip()


def admin_emails() -> set[str]:
    raw = os.environ.get("AHA_ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    allowed = admin_emails()
    if not allowed:
        return False
    return email.strip().lower() in allowed


async def require_admin(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    secret = request.headers.get("X-AHA-Admin-Secret", "").strip()
    if _ADMIN_SECRET and secret and secret == _ADMIN_SECRET:
        return {"uid": "admin-secret", "email": "admin@secret"}

    email = user.get("email")
    if not is_admin_email(email):
        raise HTTPException(
            status_code=403,
            detail="Admin access denied. Add your email to AHA_ADMIN_EMAILS in .env.",
        )
    return user
