"""
Direct Access token budgets (license + our Gemini key).

BYOK users are not capped here — they pay their provider directly.
Social post limits apply to everyone via vercel_backend.usage.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from aha.supabase_client import get_supabase_admin
from aha.user_messages import rest_cooldown_message

_MAX_PER_MINUTE = int(os.environ.get("AHA_GEMINI_MAX_CALLS_PER_MINUTE", "6"))
_MAX_PER_HOUR = int(os.environ.get("AHA_GEMINI_MAX_CALLS_PER_HOUR", "40"))
_MAX_PER_DAY = int(os.environ.get("AHA_GEMINI_MAX_CALLS_PER_DAY", "150"))
_COOLDOWN_HOURS = float(os.environ.get("AHA_GEMINI_COOLDOWN_HOURS", "1"))


def cooldown_response(*, hours: float) -> dict:
    return {
        "allowed": False,
        "message": rest_cooldown_message(hours),
        "retry_after_hours": max(1, int(round(hours))),
    }


def _count_proxy_calls(license_key: str, *, since: datetime) -> int:
    try:
        admin = get_supabase_admin()
        result = (
            admin.table("aha_gemini_proxy_log")
            .select("id", count="exact")
            .eq("user_id", license_key)
            .eq("auth_mode", "license")
            .gte("created_at", since.isoformat())
            .execute()
        )
        return int(result.count or 0)
    except Exception:
        return 0


def check_direct_access_quota(license_key: str) -> dict:
    """
    Return {"allowed": True} or a cooldown dict.

    Checked on Vercel **before** forwarding to Gemini so spam never bills us.
    """
    key = (license_key or "").strip()
    if not key:
        return {"allowed": False, "message": "License key required."}

    now = datetime.now(timezone.utc)
    per_minute = _count_proxy_calls(key, since=now - timedelta(minutes=1))
    if per_minute >= _MAX_PER_MINUTE:
        return cooldown_response(hours=_COOLDOWN_HOURS)

    per_hour = _count_proxy_calls(key, since=now - timedelta(hours=1))
    if per_hour >= _MAX_PER_HOUR:
        return cooldown_response(hours=_COOLDOWN_HOURS)

    per_day = _count_proxy_calls(key, since=now - timedelta(days=1))
    if per_day >= _MAX_PER_DAY:
        return cooldown_response(hours=24)

    return {"allowed": True}
