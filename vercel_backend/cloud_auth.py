"""
Validate desktop → Vercel cloud requests.

When cloud auth is required, callers must send a Firebase ID token that matches
the license_key owner in Supabase — prevents spoofing with a stolen key alone.
"""

from __future__ import annotations

import os

from aha.firebase_auth import verify_firebase_token
from aha.supabase_client import get_supabase_admin


def cloud_auth_required() -> bool:
    raw = os.environ.get("AHA_REQUIRE_CLOUD_AUTH", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return os.environ.get("VERCEL_ENV") == "production"


def _license_uid(license_key: str) -> str | None:
    key = (license_key or "").strip()
    if not key:
        return None
    try:
        admin = get_supabase_admin()
        result = (
            admin.table("aha_licenses")
            .select("uid")
            .eq("license_key", key)
            .limit(1)
            .execute()
        )
        if result.data:
            return (result.data[0].get("uid") or "").strip() or None
    except Exception:
        pass
    return None


def validate_cloud_caller(
    license_key: str,
    firebase_id_token: str | None,
) -> str:
    """
    Return Firebase uid when validated.

    Raises ValueError when auth fails.
    """
    lic = (license_key or "").strip()
    if not lic:
        raise ValueError("License key required.")

    token = (firebase_id_token or "").strip()
    if not token:
        if cloud_auth_required():
            raise ValueError(
                "Sign in to AHA with Google before using cloud features."
            )
        return ""

    try:
        claims = verify_firebase_token(token)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    uid = (claims.get("uid") or "").strip()
    if not uid:
        raise ValueError("Invalid Firebase token.")

    owner = _license_uid(lic)
    if not owner:
        raise ValueError("Invalid or expired license.")
    if owner != uid:
        raise ValueError("License does not match your signed-in account.")

    return uid
