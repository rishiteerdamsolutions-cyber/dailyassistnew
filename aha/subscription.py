"""Subscription active/expired helpers — single source of truth."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional


def parse_expires_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def is_expired(expires_at: Any, *, now: Optional[datetime] = None) -> bool:
    exp = parse_expires_at(expires_at)
    if exp is None:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return exp < now


def license_row_is_active(row: dict) -> bool:
    """True only if row is active in DB and not past expires_at."""
    if not row:
        return False
    if not row.get("is_active", True):
        return False
    return not is_expired(row.get("expires_at"))


def allow_dev_license_keys() -> bool:
    from aha.runtime_paths import is_retail_build

    if is_retail_build():
        return False
    return os.environ.get("AHA_ALLOW_DEV_LICENSE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
