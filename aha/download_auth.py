"""Paid-subscription gate for app downloads."""

from __future__ import annotations

import os
from pathlib import Path

from aha.subscription import license_row_is_active

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "downloads"
ALLOWED_PACKAGES = {
    "mac": "AHA-mac.zip",
    "win": "AHA-win.zip",
}

# Vercel excludes downloads/ — host zips on Supabase/GitHub and set these URLs.
_DOWNLOAD_URL_ENV = {
    "mac": "AHA_DOWNLOAD_MAC_URL",
    "win": "AHA_DOWNLOAD_WIN_URL",
}


def download_url(platform: str) -> str | None:
    key = _DOWNLOAD_URL_ENV.get(platform)
    if not key:
        return None
    url = os.environ.get(key, "").strip()
    return url or None


def package_available(platform: str) -> bool:
    return package_path(platform) is not None or bool(download_url(platform))


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

    filename = ALLOWED_PACKAGES.get(platform, "AHA.zip")
    path = package_path(platform)
    if path:
        return {
            "ok": True,
            "kind": "file",
            "path": str(path),
            "filename": filename,
        }

    url = download_url(platform)
    if url:
        return {"ok": True, "kind": "url", "url": url, "filename": filename}

    return {
        "ok": False,
        "reason": "package_missing",
        "message": (
            f"Installer not available yet. Build {filename} (scripts/build_desktop_release.sh), "
            f"upload to cloud storage, and set {_DOWNLOAD_URL_ENV.get(platform)} on Vercel — "
            f"or place the file in downloads/ for local server.py."
        ),
    }
