from __future__ import annotations

import subprocess
import time

from bol.config import BOLConfig
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class NativeBrowserManager:
    """Launch and position native Google Chrome on macOS."""

    def __init__(self, config: BOLConfig) -> None:
        self.config = config

    def launch(self, url: str) -> None:
        logger.info("Launching native uninstrumented Chrome window to: %s", url)

        cmd = ["open", "-na", "Google Chrome", "--args", "--new-window", url]

        try:
            subprocess.Popen(cmd)
            logger.info("Chrome launch subprocess initiated successfully.")
            time.sleep(1.5)
            applescript = f'''
            tell application "Google Chrome"
                try
                    set windowList to every window
                    repeat with w in windowList
                        set t to title of w
                        if t contains "BOL Companion" or t contains "localhost:8000" or t contains "127.0.0.1:8000" then
                            set bounds of w to {{0, 50, 540, 1000}}
                        end if
                    end repeat
                end try
                try
                    set bounds of window 1 to {{{self.config.browser_window_x}, {self.config.browser_window_y}, {self.config.browser_window_x + self.config.browser_window_width}, {self.config.browser_window_y + self.config.browser_window_height}}}
                end try
            end tell
            '''
            subprocess.run(["osascript", "-e", applescript])
            logger.info("AppleScript window side-by-side positioning executed successfully.")
        except Exception as e:
            logger.error("Failed to launch native Chrome window: %s", e)


_browser_manager: NativeBrowserManager | None = None


def get_browser_manager(config: BOLConfig) -> NativeBrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = NativeBrowserManager(config)
    return _browser_manager
