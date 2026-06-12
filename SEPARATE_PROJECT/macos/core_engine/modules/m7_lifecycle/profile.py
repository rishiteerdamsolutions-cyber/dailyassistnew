"""
Chrome profile manager.

Launches and shuts down the browser through OS-native commands,
never via process killing or instrumentation.
"""

from __future__ import annotations

import secrets
import subprocess
import time
from typing import TYPE_CHECKING

from bol.config import BOLConfig
from bol.utils.logging import get_logger
from bol.utils.platform import get_chrome_launch_command

if TYPE_CHECKING:
    from bol.modules.m6_bridge.bridge import AccessibilityBridge

logger = get_logger(__name__)


class ChromeProfileManager:
    """
    Manages Chrome browser lifecycle through OS-native commands.

    Uses the Accessibility Bridge for keyboard-driven shutdown
    and navigation. Never kills processes programmatically.
    """

    def __init__(
        self,
        config: BOLConfig,
        bridge: AccessibilityBridge | None = None,
    ) -> None:
        self._config = config
        self._bridge = bridge

    def set_bridge(self, bridge: AccessibilityBridge) -> None:
        """Inject the accessibility bridge (deferred to avoid circular deps)."""
        self._bridge = bridge

    def launch_browser(self) -> bool:
        """
        Launch Chrome with the configured profile.

        Starts the process in the background and waits for initialization.
        NEVER uses sys.exit().

        Returns
        -------
        bool
            True if the process started successfully.
        """
        cmd = get_chrome_launch_command(
            profile_dir=self._config.chrome_profile_dir,
            url=f"https://www.{self._config.target_platform}.com/feed",
        )

        logger.info("Launching browser: %s", " ".join(cmd))
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            logger.error("Failed to launch browser: %s", e)
            return False

        # Wait for browser to initialize (3-5 seconds with jitter)
        wait_s = 3.0 + secrets.randbelow(21) / 10.0  # 3.0 to 5.0
        time.sleep(wait_s)
        logger.info("Browser launched, waited %.1fs", wait_s)
        return True

    def shutdown_browser(self) -> None:
        """
        Shut down Chrome via OS keyboard shortcut (Cmd+Q).

        Waits 2 seconds for Chrome to serialize local storage.
        NEVER kills processes programmatically.
        """
        if self._bridge is None:
            logger.error("Cannot shutdown: accessibility bridge not set")
            return

        logger.info("Shutting down browser via Cmd+Q")
        self._bridge.execute_hotkey(("command", "q"))
        time.sleep(2.0)  # Wait for Chrome to serialize storage

    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL using the address bar.

        Uses keyboard shortcuts to select the address bar,
        type the URL, and press Enter.
        """
        if self._bridge is None:
            logger.error("Cannot navigate: accessibility bridge not set")
            return

        # Open address bar
        self._bridge.execute_hotkey(("command", "l"))
        time.sleep(0.3 + secrets.randbelow(3) / 10.0)  # 0.3-0.5s

        # Type URL via keystroke sequence
        from bol.schemas.linguistic import KeystrokeEvent

        events = [KeystrokeEvent(character=c, delay_before_ms=20.0) for c in url]
        self._bridge.execute_keystroke_sequence(events)

        time.sleep(0.2)

        # Press Enter
        self._bridge.execute_keystroke_sequence(
            [KeystrokeEvent(character="\n", delay_before_ms=100.0)]
        )
        logger.info("Navigated to: %s", url)
