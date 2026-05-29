"""
Native OS input wrapper using pyautogui.

All input actions are preceded by hardware jitter delays
to anchor the digital interaction signature to physical
hardware performance constraints.
"""

from __future__ import annotations

import time

import pyautogui

from bol.modules.m6_bridge.hardware import HardwareMonitor
from bol.schemas.bridge import HardwareJitter
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class NativeInput:
    """
    pyautogui wrapper that injects hardware-anchored jitter
    before every OS-level input action.
    """

    def __init__(self, hardware_monitor: HardwareMonitor) -> None:
        self._hw = hardware_monitor
        # Configure pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0  # We handle delays ourselves

    def move_cursor(self, x: float, y: float, duration_s: float = 0.0) -> None:
        """Move cursor to absolute position with hardware jitter."""
        self._apply_jitter_delay()
        pyautogui.moveTo(int(x), int(y), duration=duration_s)

    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at position with hardware jitter."""
        self._apply_jitter_delay()
        pyautogui.click(x, y, button=button)

    def type_character(self, char: str, delay_s: float = 0.0) -> None:
        """
        Type a single character with hardware jitter.

        For regular characters, uses pyautogui.press().
        """
        self._apply_jitter_delay()
        if len(char) == 1 and char.isalnum():
            pyautogui.press(char)
        elif char == " ":
            pyautogui.press("space")
        elif char == "\n":
            pyautogui.press("enter")
        elif char == "\t":
            pyautogui.press("tab")
        elif char == "\b":
            pyautogui.press("backspace")
        else:
            # For special characters, try write() which handles shift states
            pyautogui.write(char, interval=0)

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """Type a string of text with consistent inter-key interval."""
        self._apply_jitter_delay()
        pyautogui.write(text, interval=interval)

    def hotkey(self, *keys: str) -> None:
        """Execute a keyboard shortcut with hardware jitter."""
        self._apply_jitter_delay()
        pyautogui.hotkey(*keys)
        logger.debug("Hotkey: %s", "+".join(keys))

    def scroll(self, clicks: int) -> None:
        """Scroll with hardware jitter. Positive=up, negative=down."""
        self._apply_jitter_delay()
        pyautogui.scroll(clicks)

    def press_key(self, key: str) -> None:
        """Press a named key (e.g., 'enter', 'backspace')."""
        self._apply_jitter_delay()
        pyautogui.press(key)

    def _apply_jitter_delay(self) -> HardwareJitter:
        """Sample hardware and sleep for the computed jitter delay."""
        jitter = self._hw.get_jitter()
        time.sleep(jitter.computed_delay_ms / 1000.0)
        return jitter
