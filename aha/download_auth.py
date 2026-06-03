"""Paid-subscription gate for app downloads."""

from __future__ import annotations

from pathlib import Path

from aha.subscription import license_row_is_active

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "downloads"
ALLOWED_PACKAGES = {
    "mac": "AHA-mac.zip",
    "win": "AHA-win.zip",
}


async def eligibility_for_uid(uid: str) -> dict:
    from aha.supabase_client import get_active_license

    row = get_active_license(uid)
    if not row:
        return {
            "allowed": False,
            "reason": "no_subscription",
            "message": "An active paid subscription is required to download AHA.",
        }
    return {
        "allowed": True,
        "plan": row.get("plan"),
        "expires_at": row.get("expires_at"),
        "license_key": row.get("license_key"),
    }


def package_path(platform: str) -> Path | None:
    name = ALLOWED_PACKAGES.get(platform)
    if not name:
        return None
    path = DOWNLOADS_DIR / name
    return path if path.is_file() else None


async def resolve_download(uid: str, platform: str) -> dict:
    elig = await eligibility_for_uid(uid)
    if not elig.get("allowed"):
        return {"ok": False, **elig}

    path = package_path(platform)
    if not path:
        return {
            "ok": False,
            "reason": "package_missing",
            "message": f"Installer not uploaded yet. Add {ALLOWED_PACKAGES.get(platform)} to the downloads/ folder.",
        }
    return {"ok": True, "path": str(path), "filename": path.name}
