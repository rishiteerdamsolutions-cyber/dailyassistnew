"""
Tiny Guard Agents — specialized sub-agents that vote on physical actions.
"""
from __future__ import annotations

import numpy as np

from bol.modules.m12_swarm.council import SwarmDecision, swarm_council
from bol.utils.logging import get_logger
from bol.utils.platform import get_chrome_window_bounds, is_macos, is_windows

logger = get_logger(__name__)


class GuardAgent:
    def evaluate(
        self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict
    ) -> SwarmDecision:
        raise NotImplementedError


class SafetyGuard(GuardAgent):
    """Prevent misclicks outside the safe Chrome content area."""

    def __init__(self) -> None:
        self._screen_height: int | None = None

    def _get_screen_height(self) -> int:
        if self._screen_height is not None:
            return self._screen_height

        if is_windows():
            try:
                import pygetwindow as gw

                wins = gw.getAllWindows()
                if wins:
                    self._screen_height = max((w.top + w.height for w in wins if w.height), default=1080)
                    return self._screen_height
            except Exception:
                pass
            self._screen_height = 1080
            return self._screen_height

        self._screen_height = 900
        return self._screen_height

    def evaluate(
        self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict
    ) -> SwarmDecision:
        screen_h = self._get_screen_height()

        if is_macos():
            if y < 30:
                return SwarmDecision(
                    approved=False,
                    reason=f"y={y} is inside the macOS Menu Bar (top 30px).",
                    vetoed_by="SafetyGuard",
                )
            if y > screen_h - 80:
                return SwarmDecision(
                    approved=False,
                    reason=f"y={y} is inside the macOS Dock zone (bottom 80px, screen_h={screen_h}).",
                    vetoed_by="SafetyGuard",
                )

        if is_windows() and y > screen_h - 48:
            return SwarmDecision(
                approved=False,
                reason=f"y={y} is inside the Windows taskbar zone (bottom 48px, screen_h={screen_h}).",
                vetoed_by="SafetyGuard",
            )

        bounds = get_chrome_window_bounds()
        if bounds:
            bx, by, bw, bh = bounds
            if not (bx <= x <= bx + bw and by <= y <= by + bh):
                return SwarmDecision(
                    approved=False,
                    reason=f"({x},{y}) is OUTSIDE Chrome window bounds ({bx},{by},{bw},{bh}).",
                    vetoed_by="SafetyGuard",
                )

            chrome_relative_y = y - by
            if chrome_relative_y < 90:
                return SwarmDecision(
                    approved=False,
                    reason=f"y={y} (chrome_relative={chrome_relative_y}px) is inside Chrome URL/Tab bar.",
                    vetoed_by="SafetyGuard",
                )

        return SwarmDecision(approved=True, reason="Coordinates are within safe Chrome content area.")


class DuplicateGuard(GuardAgent):
    def evaluate(
        self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict
    ) -> SwarmDecision:
        bboxes = context.get("all_bboxes", [])
        target_text = context.get("target_text", "unknown")

        if len(bboxes) > 2 and not context.get("has_spatial_anchor", False):
            logger.warning(
                "[DuplicateGuard] Found %d matches for '%s' without spatial anchor.",
                len(bboxes),
                target_text,
            )

        return SwarmDecision(approved=True, reason="")


swarm_council.register_guard(SafetyGuard())
swarm_council.register_guard(DuplicateGuard())
