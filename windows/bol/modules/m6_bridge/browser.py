from __future__ import annotations

import subprocess
import time

from bol.config import BOLConfig
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class NativeBrowserManager:
    """Launch and position native Google Chrome on Windows."""

    def __init__(self, config: BOLConfig) -> None:
        self.config = config

    def launch(self, url: str) -> None:
        logger.info("Launching native uninstrumented Chrome window to: %s", url)

        chrome_path = self.config.chrome_binary or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        cmd = [
            chrome_path,
            f"--window-position={self.config.browser_window_x},{self.config.browser_window_y}",
            f"--window-size={self.config.browser_window_width},{self.config.browser_window_height}",
            "--new-window",
            url,
        ]

        try:
            subprocess.Popen(cmd)
            logger.info("Chrome launch subprocess initiated successfully.")
            time.sleep(3.0)
        except Exception as e:
            logger.error("Failed to launch native Chrome window: %s", e)


_browser_manager: NativeBrowserManager | None = None


def get_browser_manager(config: BOLConfig) -> NativeBrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = NativeBrowserManager(config)
    return _browser_manager
