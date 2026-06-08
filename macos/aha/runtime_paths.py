"""Paths for dev checkout vs PyInstaller retail bundle."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_retail_build() -> bool:
    """True for customer desktop builds — disables dev license bypass."""
    if is_frozen():
        return True
    return os.environ.get("AHA_RETAIL_BUILD", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def bundle_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def install_bundle_paths() -> None:
    """When frozen, run with bundle root as cwd so relative web/ paths work."""
    if is_frozen():
        root = bundle_root()
        os.chdir(root)


def resource_path(*parts: str) -> Path:
    return bundle_root().joinpath(*parts)
