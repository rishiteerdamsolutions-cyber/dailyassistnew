"""Paths for dev checkout vs Nuitka / PyInstaller retail bundle."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _main_compiled() -> bool:
    main = sys.modules.get("__main__")
    return bool(main and getattr(main, "__compiled__", False))


def _bundle_has_data() -> bool:
    """True when web/ or VISIONBUTTONS/ sit next to the compiled executable."""
    exe_dir = Path(sys.executable).resolve().parent
    return (exe_dir / "web").is_dir() or (exe_dir / "VISIONBUTTONS").is_dir()


def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        return True
    if _main_compiled():
        return True
    if _bundle_has_data():
        return True
    return False


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
    """Directory containing bundled web/, VISIONBUTTONS/, etc."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if is_frozen() or _bundle_has_data():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    """Project root — dev tree or compiled bundle root."""
    root = bundle_root()
    if (root / "VISIONBUTTONS").is_dir() or (root / "web").is_dir():
        return root
    dev = Path(__file__).resolve().parent.parent
    if (dev / "VISIONBUTTONS").is_dir():
        return dev
    return root


def install_bundle_paths() -> None:
    """When frozen, run with bundle root as cwd so relative web/ paths work."""
    if is_frozen() or _bundle_has_data():
        os.chdir(repo_root())


def resource_path(*parts: str) -> Path:
    return repo_root().joinpath(*parts)
