from __future__ import annotations

import os
import sys
import subprocess
import time
import cv2
import base64
import numpy as np
from PIL import Image

from bol.config import BOLConfig
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class NativeBrowserManager:
    """
    Manages launching and positioning a native, uninstrumented Google Chrome window
    on the desktop, enabling completely undetectable physical automation.
    """

    def __init__(self, config: BOLConfig) -> None:
        self.config = config

    def launch(self, url: str) -> None:
        """Launch a native Chrome window at the configured position and dimensions."""
        logger.info("Launching native uninstrumented Chrome window to: %s", url)
        
        system = sys.platform
        if system == "darwin":
            # macOS command to open new Chrome window
            cmd = [
                "open", "-na", "Google Chrome", "--args",
                "--new-window", url
            ]
        elif system == "win32":
            # Windows command to open new Chrome window
            chrome_path = self.config.chrome_binary or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            cmd = [
                chrome_path,
                f"--window-position={self.config.browser_window_x},{self.config.browser_window_y}",
                f"--window-size={self.config.browser_window_width},{self.config.browser_window_height}",
                "--new-window", url
            ]
        else:
            # Linux fallback
            cmd = [
                "google-chrome",
                f"--window-position={self.config.browser_window_x},{self.config.browser_window_y}",
                f"--window-size={self.config.browser_window_width},{self.config.browser_window_height}",
                "--new-window", url
            ]

        try:
            subprocess.Popen(cmd)
            logger.info("Chrome launch subprocess initiated successfully.")
            
            # Position windows side-by-side on macOS using AppleScript
            if system == "darwin":
                time.sleep(1.5) # Wait for window to register
                applescript = f'''
                -- Resize companion app window in Chrome (if active)
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
                end tell

                -- Resize companion app window in Safari (if active)
                tell application "Safari"
                    try
                        set windowList to every window
                        repeat with w in windowList
                            set n to name of w
                            if n contains "BOL Companion" or n contains "localhost" or n contains "127.0.0.1" then
                                set bounds of w to {{0, 50, 540, 1000}}
                            end if
                        end repeat
                    end try
                end tell

                -- Position the newly created Chrome window to the right half
                tell application "Google Chrome"
                    try
                        set bounds of window 1 to {{{self.config.browser_window_x}, {self.config.browser_window_y}, {self.config.browser_window_x + self.config.browser_window_width}, {self.config.browser_window_y + self.config.browser_window_height}}}
                    end try
                end tell
                '''
                subprocess.run(["osascript", "-e", applescript])
                logger.info("AppleScript window side-by-side positioning executed successfully.")
            else:
                # Give Chrome window time to open and draw on Windows/Linux
                time.sleep(3.0)
        except Exception as e:
            logger.error("Failed to launch native Chrome window: %s", e)


# Global singleton
_browser_manager: NativeBrowserManager | None = None


def get_browser_manager(config: BOLConfig) -> NativeBrowserManager:
    """Access the global NativeBrowserManager singleton instance."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = NativeBrowserManager(config)
    return _browser_manager
