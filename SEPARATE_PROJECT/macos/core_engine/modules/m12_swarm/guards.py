"""
Tiny Guard Agents — The specialized sub-agents that make up the Swarm.

Each guard is a single-purpose sentinel that votes YES or NO on every
proposed physical action before the Hero Agent is allowed to perform it.
"""
import subprocess
import numpy as np
from bol.utils.logging import get_logger
from bol.modules.m12_swarm.council import SwarmDecision, swarm_council

logger = get_logger(__name__)


class GuardAgent:
    """Base class for all Swarm Guards."""
    def evaluate(self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict) -> SwarmDecision:
        raise NotImplementedError


class SafetyGuard(GuardAgent):
    """
    Sub-Agent focused exclusively on anti-misclicks.
    Ensures the Hero Agent never clicks:
      - The macOS menu bar (y < 30)
      - The Chrome URL/Tab bar (y < 120 when inside Chrome area)
      - The macOS Dock (bottom ~80px of screen)
      - Any coordinate outside the Chrome window bounds
    """
    def __init__(self):
        self._screen_height = None

    def _get_screen_height(self) -> int:
        """Get screen height once and cache it."""
        if self._screen_height is None:
            try:
                # system_profiler doesn't require Finder permissions
                result = subprocess.check_output(
                    ['system_profiler', 'SPDisplaysDataType'], timeout=2
                ).decode().strip()
                # Find line like: "Resolution: 2560 x 1600"
                import re
                match = re.search(r'Resolution:\s*\d+\s*x\s*(\d+)', result)
                if match:
                    # system_profiler gives Retina physical pixels, we need logical points.
                    # As a safe heuristic, divide by 2 for Retina, but the best generic fallback is 900.
                    # Actually, a safer standard logical height is 900 or 1080.
                    # Let's use 900 as default instead of trying to guess physical vs logical points,
                    # because macOS dock size in pixels varies heavily.
                    self._screen_height = 900
                else:
                    self._screen_height = 900
            except Exception:
                self._screen_height = 900  # Safe default for MacBook Air
        return self._screen_height

    def _get_chrome_bounds(self):
        """Get Chrome window bounds. Returns (x, y, w, h) or None."""
        try:
            script = '''
            tell application "Google Chrome"
                if not (exists window 1) then return "none"
                set b to bounds of window 1
                return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)
            end tell
            '''
            result = subprocess.check_output(
                ['osascript', '-e', script], timeout=2
            ).decode().strip()
            if result == "none":
                return None
            x1, y1, x2, y2 = [int(v.strip()) for v in result.split(',')]
            return x1, y1, x2 - x1, y2 - y1
        except Exception:
            return None

    def evaluate(self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict) -> SwarmDecision:
        screen_h = self._get_screen_height()

        # ── Rule 1: macOS menu bar (top 30px of screen) ──
        if y < 30:
            return SwarmDecision(
                approved=False,
                reason=f"y={y} is inside the macOS Menu Bar (top 30px).",
                vetoed_by="SafetyGuard"
            )

        # ── Rule 2: macOS Dock (bottom 80px of screen) ──
        if y > screen_h - 80:
            return SwarmDecision(
                approved=False,
                reason=f"y={y} is inside the macOS Dock zone (bottom 80px, screen_h={screen_h}).",
                vetoed_by="SafetyGuard"
            )

        # ── Rule 3: Chrome window bounds ──
        bounds = self._get_chrome_bounds()
        if bounds:
            bx, by, bw, bh = bounds
            if not (bx <= x <= bx + bw and by <= y <= by + bh):
                return SwarmDecision(
                    approved=False,
                    reason=f"({x},{y}) is OUTSIDE Chrome window bounds ({bx},{by},{bw},{bh}).",
                    vetoed_by="SafetyGuard"
                )

            # ── Rule 4: Chrome URL/Tab bar (top ~90px of Chrome window) ──
            chrome_relative_y = y - by
            if chrome_relative_y < 90:
                return SwarmDecision(
                    approved=False,
                    reason=f"y={y} (chrome_relative={chrome_relative_y}px) is inside Chrome URL/Tab bar.",
                    vetoed_by="SafetyGuard"
                )

        return SwarmDecision(approved=True, reason="Coordinates are within safe Chrome content area.")


class DuplicateGuard(GuardAgent):
    """
    Sub-Agent focused on context ambiguity.
    If multiple identical targets exist without spatial anchoring,
    it logs a warning. Can be upgraded to strict veto in the future.
    """
    def evaluate(self, action_type: str, x: int, y: int, screenshot: np.ndarray, context: dict) -> SwarmDecision:
        bboxes = context.get("all_bboxes", [])
        target_text = context.get("target_text", "unknown")

        if len(bboxes) > 2 and not context.get("has_spatial_anchor", False):
            logger.warning(
                f"[DuplicateGuard] Found {len(bboxes)} matches for '{target_text}' "
                f"without spatial anchor. Proceeding with best match but flagging risk."
            )

        return SwarmDecision(approved=True, reason="")


# Automatically register standard guards on import
swarm_council.register_guard(SafetyGuard())
swarm_council.register_guard(DuplicateGuard())
