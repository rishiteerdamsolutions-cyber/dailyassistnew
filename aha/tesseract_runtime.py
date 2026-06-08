"""
Tesseract OCR — bundled in retail builds, system fallback in dev.

Retail Nuitka bundles live under:
  <bundle>/tesseract/bin/tesseract   (macOS/Linux)
  <bundle>/tesseract/tesseract.exe   (Windows)
  <bundle>/tesseract/tessdata/*.traineddata
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

_CONFIGURED = False


def _tesseract_search_roots() -> list[Path]:
    from aha.runtime_paths import resource_path

    return [
        resource_path("tesseract"),
        resource_path("vendor", "tesseract"),
    ]


def _mac_tesseract_candidates(root: Path) -> list[Path]:
    return [
        root / "bin" / "tesseract",
        root / "tesseract",
    ]


def _win_tesseract_candidates(root: Path) -> list[Path]:
    return [root / "tesseract.exe"]


def _linux_tesseract_candidates(root: Path) -> list[Path]:
    return [root / "bin" / "tesseract", root / "tesseract"]


def _platform_candidates(root: Path) -> list[Path]:
    system = platform.system()
    if system == "Darwin":
        return _mac_tesseract_candidates(root)
    if system == "Windows":
        return _win_tesseract_candidates(root)
    return _linux_tesseract_candidates(root)


def _bundled_tesseract_cmd() -> Path | None:
    for root in _tesseract_search_roots():
        if not root.is_dir():
            continue
        for candidate in _platform_candidates(root):
            if candidate.is_file():
                return candidate
    return None


def _bundled_tessdata_dir(cmd: Path) -> Path | None:
    root = cmd.parent.parent if cmd.parent.name == "bin" else cmd.parent
    tessdata = root / "tessdata"
    if tessdata.is_dir() and any(tessdata.glob("*.traineddata")):
        return tessdata
    alt = cmd.parent / "tessdata"
    if alt.is_dir() and any(alt.glob("*.traineddata")):
        return alt
    return None


def _prepend_lib_path(cmd: Path) -> None:
    """macOS: bundled dylibs often sit in tesseract/lib next to the binary."""
    root = cmd.parent.parent if cmd.parent.name == "bin" else cmd.parent
    lib_dir = root / "lib"
    if not lib_dir.is_dir():
        return
    if platform.system() == "Darwin":
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = (
            f"{lib_dir}{os.pathsep}{existing}" if existing else str(lib_dir)
        )
    elif platform.system() == "Windows":
        os.environ["PATH"] = str(lib_dir) + os.pathsep + os.environ.get("PATH", "")


def _system_tesseract_cmd() -> str | None:
    system = platform.system()
    if system == "Darwin":
        for path in (
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/usr/bin/tesseract",
        ):
            if Path(path).is_file():
                return path
        found = shutil.which("tesseract")
        return found
    if system == "Windows":
        for path in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if Path(path).is_file():
                return path
        return shutil.which("tesseract")
    return shutil.which("tesseract")


def resolve_tesseract_cmd() -> str:
    """Return the tesseract executable path (bundled first, then system)."""
    bundled = _bundled_tesseract_cmd()
    if bundled is not None:
        return str(bundled)
    system = _system_tesseract_cmd()
    if system:
        return system
    if platform.system() == "Darwin":
        return "/opt/homebrew/bin/tesseract"
    if platform.system() == "Windows":
        return r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    return "/usr/bin/tesseract"


def ensure_tesseract_configured() -> str:
    """
    Point pytesseract at bundled or system Tesseract. Idempotent.
    Returns the command path in use.
    """
    global _CONFIGURED
    cmd_path = resolve_tesseract_cmd()
    cmd = Path(cmd_path)

    if cmd.is_file():
        _prepend_lib_path(cmd)
        tessdata = _bundled_tessdata_dir(cmd)
        if tessdata is not None:
            os.environ["TESSDATA_PREFIX"] = str(tessdata)

    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = cmd_path
    except ImportError:
        pass

    _CONFIGURED = True
    return cmd_path


def tesseract_is_bundled() -> bool:
    return _bundled_tesseract_cmd() is not None


def tesseract_status() -> dict:
    cmd = resolve_tesseract_cmd()
    return {
        "cmd": cmd,
        "bundled": tesseract_is_bundled(),
        "configured": _CONFIGURED,
        "tessdata_prefix": os.environ.get("TESSDATA_PREFIX", ""),
    }
