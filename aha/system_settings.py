"""Open OS privacy settings panes from the desktop companion."""

from __future__ import annotations

import subprocess
import sys

_MAC_PRIVACY_URLS = {
    "accessibility": (
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
    ),
    "screen": (
        "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture",
    ),
}


def open_privacy_pane(pane: str) -> bool:
    """Open Accessibility or Screen Recording settings (macOS)."""
    if sys.platform != "darwin":
        return False
    urls = _MAC_PRIVACY_URLS.get(pane)
    if not urls:
        return False
    for url in urls:
        try:
            subprocess.run(["open", url], check=False, timeout=5)
            return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False
