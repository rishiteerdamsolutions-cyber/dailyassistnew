"""
Accessibility Bridge — Virtualized API for Cloud Brain.

This module replaces the physical PyAutoGUI OS-level execution with
a virtual event queue. Commands (movements, clicks, keystrokes)
are appended to a queue and serialized to JSON to be sent over
WebSockets to the Thin Client.
"""

from __future__ import annotations

import time

from bol.schemas.bridge import ClickEvent
from bol.schemas.kinematic import Point2D, ScrollProfile
from bol.schemas.linguistic import KeystrokeEvent
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class AccessibilityBridge:
    """
    Virtualized OS input bridge for Cloud Brain.
    """

    def __init__(self) -> None:
        self.action_queue = []
        self.virtual_cursor_x = 0.0
        self.virtual_cursor_y = 0.0

    def update_cursor(self, x: float, y: float) -> None:
        """Update the virtual cursor position from the thin client."""
        self.virtual_cursor_x = x
        self.virtual_cursor_y = y

    def get_actions(self) -> list[dict]:
        """Retrieve and flush the action queue."""
        actions = self.action_queue.copy()
        self.action_queue.clear()
        return actions

    def execute_click(self, event: ClickEvent) -> None:
        self.action_queue.append({
            "action": "click",
            "x": event.target_x,
            "y": event.target_y,
            "button": event.button.value,
            "pre_click_delay_ms": event.pre_click_delay_ms
        })
        self.virtual_cursor_x = event.target_x
        self.virtual_cursor_y = event.target_y
        logger.debug("Queued click at (%d, %d)", event.target_x, event.target_y)

    def execute_movement(
        self, points: list[Point2D], total_duration_ms: float
    ) -> None:
        if not points:
            return

        pts_dicts = [{"x": p.x, "y": p.y} for p in points]
        self.action_queue.append({
            "action": "move_path",
            "points": pts_dicts,
            "total_duration_ms": total_duration_ms
        })
        self.virtual_cursor_x = points[-1].x
        self.virtual_cursor_y = points[-1].y

    def execute_keystroke_sequence(self, events: list[KeystrokeEvent]) -> None:
        evs_dicts = []
        for e in events:
            evs_dicts.append({
                "character": e.character,
                "is_correction": e.is_correction,
                "delay_before_ms": e.delay_before_ms
            })
        self.action_queue.append({
            "action": "type_sequence",
            "events": evs_dicts
        })

    def execute_hotkey(self, keys: list[str] | tuple[str, ...]) -> None:
        self.action_queue.append({
            "action": "hotkey",
            "keys": list(keys)
        })

    def execute_scroll(self, scroll_profile: ScrollProfile) -> None:
        stutter_map = {s.step_index: s.pause_ms for s in scroll_profile.micro_stutters}
        self.action_queue.append({
            "action": "scroll",
            "direction": scroll_profile.direction.value,
            "num_steps": scroll_profile.num_steps,
            "step_delays_ms": scroll_profile.step_delays_ms,
            "stutter_map": stutter_map
        })

    def get_cursor_position(self) -> Point2D:
        return Point2D(x=self.virtual_cursor_x, y=self.virtual_cursor_y)
