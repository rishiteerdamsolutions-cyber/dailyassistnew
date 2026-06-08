"""
Gemini API proxy — all desktop LLM calls route through Vercel.

Option 1 (BYOK): client sends user's api_key; server pass-through only.
Option 2 (License): client sends license_key; server attaches GEMINI_API_KEY.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from aha.subscription import license_row_is_active
from aha.supabase_client import get_supabase_admin
from vercel_backend.cloud_auth import validate_cloud_caller
from vercel_backend.token_quota import check_direct_access_quota

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_MASTER_KEY = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get(
    "BOL_GEMINI_API_KEY", ""
).strip()


def _validate_license(license_key: str) -> dict | None:
    admin = get_supabase_admin()
    result = (
        admin.table("aha_licenses")
        .select("uid, plan, expires_at, is_active")
        .eq("license_key", license_key)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    if not license_row_is_active(row):
        return None
    return row


def resolve_gemini_key(*, license_key: str, byok_key: str | None) -> tuple[str, str]:
    """
    Return (api_key, auth_mode) where auth_mode is 'byok' or 'license'.
    Raises ValueError on invalid auth.
    """
    key = (byok_key or "").strip()
    if key:
        return key, "byok"

    lic = (license_key or "").strip()
    if not lic:
        raise ValueError("License key or BYOK API key required.")

    if not _validate_license(lic):
        raise ValueError("Invalid or expired license.")

    if not _MASTER_KEY:
        raise ValueError("Server Gemini key not configured.")

    return _MASTER_KEY, "license"


def _log_proxy_call(user_id: str, auth_mode: str, model: str) -> None:
    try:
        admin = get_supabase_admin()
        admin.table("aha_gemini_proxy_log").insert(
            {"user_id": user_id, "auth_mode": auth_mode, "model": model}
        ).execute()
    except Exception:
        pass


def proxy_generate_content(
    *,
    license_key: str,
    byok_key: str | None,
    model: str,
    contents: list[dict[str, Any]],
    system_instruction: str | None = None,
    generation_config: dict[str, Any] | None = None,
    firebase_id_token: str | None = None,
) -> dict[str, Any]:
    """
    Forward a generateContent request to Gemini REST API.
    *contents* uses the Gemini REST schema (role + parts).
    """
    byok = (byok_key or "").strip()
    if not byok:
        validate_cloud_caller(license_key, firebase_id_token)
        quota = check_direct_access_quota(license_key)
        if not quota.get("allowed"):
            raise ValueError(quota.get("message") or "Direct Access limit reached.")

    api_key, auth_mode = resolve_gemini_key(
        license_key=license_key, byok_key=byok_key
    )
    user_id = (license_key or "").strip() or f"byok:{api_key[:8]}"

    body: dict[str, Any] = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if generation_config:
        body["generationConfig"] = generation_config

    url = f"{_GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Gemini API error ({exc.code}): {detail}") from exc

    _log_proxy_call(user_id, auth_mode, model)

    candidates = payload.get("candidates") or []
    text = ""
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)

    return {"text": text, "raw": payload, "auth_mode": auth_mode}
