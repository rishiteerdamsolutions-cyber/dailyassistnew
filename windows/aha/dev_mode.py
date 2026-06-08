"""Local-only developer gates — never enabled in retail or on Vercel."""

from __future__ import annotations

import os


def dev_gates_open() -> bool:
    """True when local agent dev should skip Firebase + license gates."""
    from aha.runtime_paths import is_retail_build

    if is_retail_build():
        return False
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        return False
    return os.environ.get("AHA_DEV_OPEN_GATES", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
