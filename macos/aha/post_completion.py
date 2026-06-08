"""
Record a verified social post — vault tick + cloud server confirmation.

Only called after the executor confirms the final publish button succeeded.
Interrupted flows (power cut, app closed) never reach here, so daily limits stay open.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from aha.storage_vault import vault_root
from bol.utils.logging import get_logger

logger = get_logger(__name__)

AHA_DIR = Path.home() / ".aha"
LOCAL_LOG = AHA_DIR / "verified_posts.json"


def _slot_name_for_platform(platform: str) -> str:
    return (platform or "").strip().lower()


def mark_vault_posted(
    platform: str,
    *,
    year: int | None = None,
    month: int | None = None,
    day: int | None = None,
    task_id: str = "",
) -> Path | None:
    """Write a tick file under the platform vault slot for today's calendar day."""
    today = date.today()
    y = year if year is not None else today.year
    m = month if month is not None else today.month
    d = day if day is not None else today.day

    slot = _slot_name_for_platform(platform)
    posted_dir = vault_root() / "Slots" / slot / str(y) / str(m) / "Posted"
    try:
        posted_dir.mkdir(parents=True, exist_ok=True)
        tick_path = posted_dir / f"{d}.tick"
        payload = {
            "platform": slot,
            "task_id": task_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "verified": True,
            "calendar_day": d,
            "calendar_month": m,
            "calendar_year": y,
        }
        tick_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Vault tick written: %s", tick_path)
        return tick_path
    except OSError as exc:
        logger.warning("Could not write vault tick for %s: %s", platform, exc)
        return None


def _append_local_log(platform: str, task_id: str) -> None:
    try:
        AHA_DIR.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if LOCAL_LOG.exists():
            data = json.loads(LOCAL_LOG.read_text(encoding="utf-8"))
        today = date.today().isoformat()
        data.setdefault(today, {})
        data[today][platform] = {
            "task_id": task_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "verified": True,
        }
        LOCAL_LOG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not update local post log: %s", exc)


def is_vault_day_posted(slot: str, year: int, month: int, day: int) -> bool:
    tick = vault_root() / "Slots" / slot / str(year) / str(month) / "Posted" / f"{day}.tick"
    return tick.exists() and tick.stat().st_size > 0


def complete_verified_post(
    platform: str,
    task_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Vault tick + cloud server record. Call only after publish verification passed.
    """
    from aha.cloud_client import confirm_platform_post

    params = params or {}
    today = date.today()
    mark_vault_posted(
        platform,
        year=today.year,
        month=today.month,
        day=today.day,
        task_id=task_id,
    )
    _append_local_log(platform, task_id)

    cloud_result: dict[str, Any] = {"recorded": False}
    try:
        cloud_result = confirm_platform_post(platform, task_id=task_id)
    except Exception as exc:
        logger.error("Cloud post confirmation failed for %s: %s", platform, exc)
        cloud_result = {"recorded": False, "error": str(exc)}

    return {
        "vault_tick": True,
        "platform": platform,
        "task_id": task_id,
        "cloud": cloud_result,
    }
