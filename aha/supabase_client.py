"""
Supabase client — single shared instance for the FastAPI process.

Environment variables (set in .env):
    SUPABASE_URL          https://wuvapuamgkrtoyeumsjd.supabase.co
    SUPABASE_ANON_KEY     sb_publishable_...  (safe to bundle with app)
    SUPABASE_SERVICE_KEY  eyJ...              (server-side only, never expose to client)
"""

from __future__ import annotations

import os
from functools import lru_cache

# ── Supabase project settings ────────────────────────────────────────────────
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://wuvapuamgkrtoyeumsjd.supabase.co"
)
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY", "sb_publishable_Xc27yow5Gy9bhh81o8pEBw_mMWAuZCt"
)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


@lru_cache(maxsize=1)
def get_supabase():
    """Return the shared anon-key Supabase client (respects RLS)."""
    try:
        from supabase import create_client
    except ImportError:
        raise RuntimeError("supabase package not installed. Run: pip install supabase")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin():
    """Return the service-role Supabase client (bypasses RLS — server only).

    Falls back to the anon client if the service key is not set,
    which is safe during local dev before a production key is available.
    """
    try:
        from supabase import create_client
    except ImportError:
        raise RuntimeError("supabase package not installed. Run: pip install supabase")

    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return create_client(SUPABASE_URL, key)


# ── Helper: upsert user row after Firebase sign-in ─────────────────────────

def upsert_user(uid: str, email: str, display_name: str | None = None) -> dict:
    """Create or update the aha_users row for this Firebase uid."""
    client = get_supabase_admin()
    data = {
        "uid": uid,
        "email": email,
        "display_name": display_name or "",
    }
    result = (
        client.table("aha_users")
        .upsert(data, on_conflict="uid")
        .execute()
    )
    return result.data[0] if result.data else data


# ── Helper: license check via Supabase ──────────────────────────────────────

def get_active_license(uid: str) -> dict | None:
    """Return the user's active license row, or None."""
    try:
        client = get_supabase_admin()
        result = (
            client.table("aha_licenses")
            .select("*")
            .eq("uid", uid)
            .eq("is_active", True)
            .order("activated_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def activate_cloud_license(uid: str, license_key: str, plan: str = "core") -> dict:
    """Insert a license record for this user."""
    client = get_supabase_admin()
    result = (
        client.table("aha_licenses")
        .upsert(
            {"uid": uid, "license_key": license_key, "plan": plan, "is_active": True},
            on_conflict="license_key",
        )
        .execute()
    )
    return result.data[0] if result.data else {}


# ── Helper: vault metadata sync ─────────────────────────────────────────────

def sync_vault_meta(
    uid: str,
    slot: str,
    year: int,
    month: int,
    day: int,
    has_text: bool,
    has_image: bool,
    has_video: bool,
) -> None:
    """Upsert one vault calendar cell to Supabase (best-effort, non-blocking)."""
    try:
        client = get_supabase_admin()
        client.table("aha_vault_meta").upsert(
            {
                "uid": uid,
                "slot": slot,
                "year": year,
                "month": month,
                "day": day,
                "has_text": has_text,
                "has_image": has_image,
                "has_video": has_video,
            },
            on_conflict="uid,slot,year,month,day",
        ).execute()
    except Exception:
        pass  # Offline or misconfigured — local vault still works


# ── Helper: vault storage (upload to Supabase Storage) ─────────────────────

def upload_vault_file(
    uid: str,
    slot: str,
    year: int,
    month: int,
    day: int,
    media_type: str,
    file_bytes: bytes,
    ext: str,
) -> str | None:
    """Upload a vault file to Supabase Storage.

    Path:  aha-vault/{uid}/{slot}/{year}/{month}/{day}/{media_type}{ext}
    Returns the storage path, or None on failure.
    """
    try:
        client = get_supabase_admin()
        path = f"{uid}/{slot}/{year}/{month}/{day}/{media_type}{ext}"
        client.storage.from_("aha-vault").upload(
            path,
            file_bytes,
            {"upsert": "true"},
        )
        return path
    except Exception:
        return None
