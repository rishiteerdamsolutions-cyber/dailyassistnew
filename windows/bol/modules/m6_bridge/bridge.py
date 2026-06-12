"""
Accessibility Bridge — Public API for Module 6.

High-level interface for executing clicks, cursor movements,
keystroke sequences, hotkeys, and scrolls through the OS
accessibility layer with isTrusted=true guarantees.
"""

from __future__ import annotations

import time

import pyautogui

from bol.modules.m6_bridge.hardware import HardwareMonitor
from bol.modules.m6_bridge.input import NativeInput
from bol.schemas.bridge import ClickEvent
from bol.schemas.kinematic import Point2D, ScrollProfile
from bol.schemas.linguistic import KeystrokeEvent
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class AccessibilityBridge:
    """
    High-level OS input bridge composing hardware monitoring
    and native input injection.
    """

    def __init__(self) -> None:
        self._hw = HardwareMonitor()
        self._input = NativeInput(self._hw)

    def execute_click(self, event: ClickEvent) -> None:
        """
        Execute a click event with pre-click delay.

        Parameters
        ----------
        event : ClickEvent
            Fully resolved click with target coordinates and jitter.
        """
        if event.pre_click_delay_ms > 0:
            time.sleep(event.pre_click_delay_ms / 1000.0)
        self._input.click(event.target_x, event.target_y, event.button.value)
        logger.debug("Click at (%d, %d) button=%s", event.target_x, event.target_y, event.button.value)

    def execute_movement(
        self, points: list[Point2D], total_duration_ms: float
    ) -> None:
        """
        Execute a cursor movement along a series of points.

        Parameters
        ----------
        points : list[Point2D]
            Trajectory points to follow.
        total_duration_ms : float
            Total movement duration in milliseconds.
        """
        if not points:
            return

        per_step_s = (total_duration_ms / len(points)) / 1000.0
        for point in points:
            self._input.move_cursor(point.x, point.y, duration_s=per_step_s)

    def execute_keystroke_sequence(self, events: list[KeystrokeEvent]) -> None:
        """
        Execute a sequence of keystroke events with timing.

        Parameters
        ----------
        events : list[KeystrokeEvent]
            Ordered keystroke events with delays.
        """
        for event in events:
            if event.delay_before_ms > 0:
                time.sleep(event.delay_before_ms / 1000.0)

            if event.is_correction:
                self._input.press_key("backspace")
            else:
                self._input.type_character(event.character)

    def execute_hotkey(self, keys: list[str] | tuple[str, ...]) -> None:
        """Execute a keyboard shortcut."""
        self._input.hotkey(*keys)

    def execute_scroll(self, scroll_profile: ScrollProfile) -> None:
        """
        Execute a scroll operation following the velocity profile.

        Parameters
        ----------
        scroll_profile : ScrollProfile
            Complete scroll plan with per-step delays and stutters.
        """
        # Build stutter lookup
        stutter_map = {s.step_index: s.pause_ms for s in scroll_profile.micro_stutters}

        # Direction: DOWN = negative clicks, UP = positive
        clicks_per_step = -3 if scroll_profile.direction.value == "down" else 3

        for i in range(scroll_profile.num_steps):
            # Apply step delay
            time.sleep(scroll_profile.step_delays_ms[i] / 1000.0)

            # Scroll
            self._input.scroll(clicks_per_step)

            # Check for micro-stutter at this step
            if i in stutter_map:
                time.sleep(stutter_map[i] / 1000.0)

    def get_cursor_position(self) -> Point2D:
        """Get the current cursor position."""
        pos = pyautogui.position()
        return Point2D(x=float(pos.x), y=float(pos.y))
