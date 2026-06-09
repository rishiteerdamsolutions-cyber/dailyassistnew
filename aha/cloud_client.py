"""
Desktop → Vercel cloud client for tamper-proof limits and Gemini proxy.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from aha.dev_mode import dev_gates_open
from aha.firebase_session import load_firebase_id_token
from aha.license import load_license
LIMIT_MESSAGE = "You are out of limit until 12 AM"

_DEFAULT_CLOUD = "https://www.dailyassist.xyz"


def cloud_api_base() -> str:
    return (
        os.environ.get("AHA_CLOUD_API_URL", "").strip()
        or os.environ.get("AHA_API_BASE", "").strip()
        or _DEFAULT_CLOUD
    ).rstrip("/")


def cloud_enforcement_enabled() -> bool:
    """Enforce server limits for all users; dev checkout skips with AHA_DEV_OPEN_GATES."""
    if dev_gates_open():
        return False
    if os.environ.get("AHA_SKIP_CLOUD_LIMITS", "").strip().lower() in ("1", "true", "yes"):
        return False
    return True


def cloud_proxy_enabled() -> bool:
    if dev_gates_open():
        return False
    if os.environ.get("AHA_SKIP_CLOUD_PROXY", "").strip().lower() in ("1", "true", "yes"):
        return False
    return True


def current_license_key() -> str:
    data = load_license()
    return (data.get("license_key") or "").strip()


def _with_auth(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    token = load_firebase_id_token()
    if token and not out.get("firebase_id_token"):
        out["firebase_id_token"] = token
    return out


def _post(path: str, payload: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    url = f"{cloud_api_base()}{path}"
    body = _with_auth(payload)
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except json.JSONDecodeError:
            detail = body
        raise RuntimeError(f"Cloud API error ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach cloud API at {cloud_api_base()}. Check your internet connection."
        ) from exc


def check_platform_limit(platform: str, *, license_key: str | None = None) -> dict:
    """
    Read-only check: has this platform already been posted today on the server?

    Same rule for BYOK and Direct Access — social velocity is not plan-dependent.
    Does not consume the daily slot — that happens only in confirm_platform_post()
    after the executor verifies the final publish button succeeded.
    """
    if not cloud_enforcement_enabled():
        return {"allowed": True, "message": "dev_skip"}

    key = (license_key or current_license_key()).strip()
    if not key:
        return {
            "allowed": False,
            "message": "Activate your AHA license before posting.",
        }

    result = _post(
        "/api/usage/check",
        {"license_key": key, "platform": platform, "task_type": "social"},
    )
    if not result.get("allowed"):
        result["message"] = LIMIT_MESSAGE
    return result


def verify_firebase_via_cloud(id_token: str) -> dict:
    """Retail desktop: verify Google token on dailyassist.xyz (no local Firebase JSON)."""
    result = _post("/api/auth/firebase_signin", {"id_token": id_token})
    if result.get("status") != "ok":
        raise ValueError(result.get("message", "Sign-in verification failed"))
    return {
        "uid": result["uid"],
        "email": result.get("email", ""),
    }


def cloud_license_sync(id_token: str) -> dict:
    """Pull subscription license from cloud after Firebase sign-in."""
    return _post("/api/license/sync", {"id_token": id_token})


def cloud_license_activate(license_key: str) -> dict:
    """Validate and activate a license key via cloud (retail has no Supabase service key)."""
    return _post("/api/license/activate", {"license_key": license_key})


def cloud_license_validate(license_key: str) -> dict:
    """Validate a license key via cloud without persisting locally."""
    return _post("/api/license/validate", {"license_key": license_key})


def confirm_platform_post(
    platform: str,
    *,
    task_id: str | None = None,
    license_key: str | None = None,
) -> dict:
    """Tell the server a verified post completed (final button + screenshot check)."""
    if not cloud_enforcement_enabled():
        return {"recorded": True, "message": "dev_skip"}

    key = (license_key or current_license_key()).strip()
    if not key:
        return {"recorded": False, "message": "License key required."}

    payload: dict[str, Any] = {
        "license_key": key,
        "platform": platform,
        "task_type": "social",
    }
    if task_id:
        payload["task_id"] = task_id

    return _post("/api/usage/confirm", payload)
