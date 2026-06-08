"""
Server-side daily task limits — 1 task per platform per UTC day.

Desktop apps cannot bypass this by editing local files or changing the clock.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from aha.supabase_client import get_supabase_admin

LIMIT_MESSAGE = "You are out of limit until 12 AM"

# Platforms that share a single daily slot (normalize aliases)
_PLATFORM_ALIASES: dict[str, str] = {
    "fb": "facebook",
    "facebok": "facebook",
    "fcebk": "facebook",
    "instagram": "instagram",
    "insta": "instagram",
    "ig": "instagram",
    "linkedin": "linkedin",
    "li": "linkedin",
    "x": "x",
    "twitter": "x",
    "whatsapp": "whatsapp",
    "wa": "whatsapp",
}


def normalize_platform(platform: str) -> str:
    key = (platform or "").strip().lower()
    return _PLATFORM_ALIASES.get(key, key)


def usage_date_utc() -> date:
    return datetime.now(timezone.utc).date()


def _lookup_uid(license_key: str) -> str | None:
    try:
        admin = get_supabase_admin()
        result = (
            admin.table("aha_licenses")
            .select("uid")
            .eq("license_key", license_key)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("uid")
    except Exception:
        pass
    return None


def check_available(
    license_key: str,
    platform: str,
    *,
    task_type: str = "social",
) -> dict:
    """
    Read-only check — has this user already completed a verified post today?

    Does NOT reserve a slot. Interrupted flows never call record_completed_post,
    so users can retry after a power cut or app close.
    """
    user_id = (license_key or "").strip()
    plat = normalize_platform(platform)
    if not user_id:
        return {"allowed": False, "message": "License key required.", "platform": plat}
    if not plat:
        return {"allowed": False, "message": "Platform required.", "platform": plat}

    today = usage_date_utc()
    admin = get_supabase_admin()

    existing = (
        admin.table("aha_daily_usage")
        .select("id, last_post_timestamp")
        .eq("user_id", user_id)
        .eq("platform", plat)
        .eq("usage_date", today.isoformat())
        .limit(1)
        .execute()
    )
    if existing.data:
        return {
            "allowed": False,
            "message": LIMIT_MESSAGE,
            "platform": plat,
            "usage_date": today.isoformat(),
            "last_post_timestamp": existing.data[0].get("last_post_timestamp"),
        }

    return {
        "allowed": True,
        "message": "ok",
        "platform": plat,
        "usage_date": today.isoformat(),
    }


def record_completed_post(
    license_key: str,
    platform: str,
    *,
    task_type: str = "social",
    task_id: str | None = None,
) -> dict:
    """
    Record a verified completed post (called only after final-button screenshot check).
    """
    user_id = (license_key or "").strip()
    plat = normalize_platform(platform)
    if not user_id:
        return {"recorded": False, "message": "License key required."}
    if not plat:
        return {"recorded": False, "message": "Platform required."}

    today = usage_date_utc()
    admin = get_supabase_admin()

    existing = (
        admin.table("aha_daily_usage")
        .select("id")
        .eq("user_id", user_id)
        .eq("platform", plat)
        .eq("usage_date", today.isoformat())
        .limit(1)
        .execute()
    )
    if existing.data:
        return {
            "recorded": True,
            "message": "already_recorded",
            "platform": plat,
            "usage_date": today.isoformat(),
        }

    uid = _lookup_uid(user_id)
    row = {
        "user_id": user_id,
        "platform": plat,
        "usage_date": today.isoformat(),
        "task_type": task_type,
        "last_post_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if uid:
        row["uid"] = uid
    if task_id:
        row["task_type"] = f"{task_type}:{task_id}"

    try:
        admin.table("aha_daily_usage").insert(row).execute()
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "23505" in str(exc):
            return {
                "recorded": True,
                "message": "already_recorded",
                "platform": plat,
                "usage_date": today.isoformat(),
            }
        raise

    return {
        "recorded": True,
        "message": "ok",
        "platform": plat,
        "usage_date": today.isoformat(),
        "last_post_timestamp": row["last_post_timestamp"],
    }


# Backward-compatible alias (read-only; no longer reserves at start)
def check_and_reserve(license_key: str, platform: str, **kwargs) -> dict:
    return check_available(license_key, platform, **kwargs)


def fetch_usage_for_admin(*, days: int = 7, limit: int = 500) -> list[dict]:
    admin = get_supabase_admin()
    since = usage_date_utc()
    from datetime import timedelta

    start = (since - timedelta(days=max(days - 1, 0))).isoformat()
    result = (
        admin.table("aha_daily_usage")
        .select("user_id, uid, platform, usage_date, last_post_timestamp, task_type")
        .gte("usage_date", start)
        .order("last_post_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def usage_summary_today() -> dict:
    today = usage_date_utc().isoformat()
    admin = get_supabase_admin()
    result = (
        admin.table("aha_daily_usage")
        .select("platform, user_id")
        .eq("usage_date", today)
        .execute()
    )
    rows = result.data or []
    by_platform: dict[str, int] = {}
    users: set[str] = set()
    for row in rows:
        plat = row.get("platform") or "unknown"
        by_platform[plat] = by_platform.get(plat, 0) + 1
        if row.get("user_id"):
            users.add(row["user_id"])
    return {
        "usage_date": today,
        "total_tasks": len(rows),
        "unique_users": len(users),
        "by_platform": by_platform,
    }
