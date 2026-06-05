"""Tier-1 local precision flows — OS, dev, files (Mac + Windows)."""

from bol.modules.m9_local.executor import run_local_task
from bol.modules.m9_local.parser import detect_local_task

__all__ = ["detect_local_task", "run_local_task"]
