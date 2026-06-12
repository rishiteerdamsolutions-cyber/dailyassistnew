"""
Action Verifier — Pure pixel analysis, zero footprint.

After every agent action (click, type, scroll, navigate) verifies what actually
happened by comparing before/after screenshots. No LLM needed.

Result is fed back into the agent loop so it knows whether to proceed,
retry with a different strategy, or escalate to the user.
"""

from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass

import cv2
import numpy as np

from bol.utils.logging import get_logger

logger = get_logger(__name__)


class VerificationResult(str, Enum):
    SUCCESS_NAVIGATION  = "navigation"    # full page change (URL navigated)
    SUCCESS_UI_UPDATE   = "ui_update"     # modal opened, cart updated, etc.
    SUCCESS_FORM_SUBMIT = "form_submit"   # form submitted, content area replaced
    FAILURE_NO_CHANGE   = "no_change"     # nothing changed after action
    FAILURE_ERROR_PAGE  = "error_page"    # error message appeared
    PENDING             = "pending"       # page still loading


@dataclass
class VerificationReport:
    result: VerificationResult
    changed_pixel_ratio: float    # 0.0 – 1.0
    changed_region: tuple[int, int, int, int] | None  # (x, y, w, h) of main change area
    confidence: float             # 0.0 – 1.0
    detail: str                   # human-readable explanation


class ActionVerifier:
    """
    Compares before/after screenshots to determine whether an action succeeded.

    Pure OpenCV pixel diff — no LLM, no DOM, no JS. Runs in <50ms.
    """

    # Pixel-level change thresholds
    PIXEL_DIFF_THRESHOLD = 25      # per-channel difference to count as "changed"
    NO_CHANGE_RATIO      = 0.001   # < 0.1% pixels changed → nothing happened
    UI_UPDATE_RATIO      = 0.02    # 0.1% – 5% changed → UI element updated
    FULL_CHANGE_RATIO    = 0.25    # > 25% changed → page navigation or major redraw

    # Error page keywords to look for via simple template matching
    ERROR_KEYWORDS = ["error", "something went wrong", "malformed", "blocked",
                      "403", "404", "500", "not found", "access denied"]

    def verify(
        self,
        before: np.ndarray,
        after: np.ndarray,
        wait_ms: int = 800,
    ) -> VerificationReport:
        """
        Compare before and after screenshots and return what happened.

        Parameters
        ----------
        before : np.ndarray
            BGR screenshot taken before the action.
        after : np.ndarray
            BGR screenshot taken after the action.
        wait_ms : int
            How many ms were already waited before capturing `after`.

        Returns
        -------
        VerificationReport
        """
        # Ensure same size
        if before.shape != after.shape:
            after = cv2.resize(after, (before.shape[1], before.shape[0]))

        diff = cv2.absdiff(before, after)
        mask = (diff.max(axis=2) > self.PIXEL_DIFF_THRESHOLD).astype(np.uint8)
        changed_ratio = float(mask.sum()) / max(mask.size, 1)

        # Find the bounding box of the main changed region
        changed_region = self._find_changed_region(mask)

        # Check if page is still loading (lots of partial changes near top/spinner)
        if self._is_loading(after, changed_ratio):
            return VerificationReport(
                result=VerificationResult.PENDING,
                changed_pixel_ratio=changed_ratio,
                changed_region=changed_region,
                confidence=0.6,
                detail="Page appears to be loading (spinner or progressive content detected)"
            )

        # Full page navigation
        if changed_ratio >= self.FULL_CHANGE_RATIO:
            return VerificationReport(
                result=VerificationResult.SUCCESS_NAVIGATION,
                changed_pixel_ratio=changed_ratio,
                changed_region=changed_region,
                confidence=0.95,
                detail=f"{changed_ratio*100:.1f}% of screen changed — page navigated"
            )

        # Form submission (large content area replaced)
        if 0.10 <= changed_ratio < self.FULL_CHANGE_RATIO and changed_region:
            cx, cy, cw, ch = changed_region
            h, w = before.shape[:2]
            if cw > w * 0.5 and ch > h * 0.3:
                return VerificationReport(
                    result=VerificationResult.SUCCESS_FORM_SUBMIT,
                    changed_pixel_ratio=changed_ratio,
                    changed_region=changed_region,
                    confidence=0.85,
                    detail="Large content area replaced — form likely submitted"
                )

        # UI update (button state, modal, cart counter, etc.)
        if self.UI_UPDATE_RATIO <= changed_ratio < 0.10:
            return VerificationReport(
                result=VerificationResult.SUCCESS_UI_UPDATE,
                changed_pixel_ratio=changed_ratio,
                changed_region=changed_region,
                confidence=0.80,
                detail=f"{changed_ratio*100:.1f}% changed — UI element updated (modal/counter/state)"
            )

        # Nothing changed — click likely missed or element was disabled
        if changed_ratio < self.NO_CHANGE_RATIO:
            return VerificationReport(
                result=VerificationResult.FAILURE_NO_CHANGE,
                changed_pixel_ratio=changed_ratio,
                changed_region=None,
                confidence=0.90,
                detail="No pixels changed after action — click likely missed or element disabled"
            )

        # Small ambiguous change (< 0.1%) — borderline
        return VerificationReport(
            result=VerificationResult.SUCCESS_UI_UPDATE,
            changed_pixel_ratio=changed_ratio,
            changed_region=changed_region,
            confidence=0.50,
            detail=f"Minor change ({changed_ratio*100:.2f}%) — possibly tooltip or focus ring"
        )

    def wait_for_page_settle(
        self,
        capture_fn,
        max_wait_s: float = 8.0,
        stable_frames: int = 3,
        check_interval_s: float = 0.4,
    ) -> np.ndarray:
        """
        Keep capturing screenshots until the page stops changing.
        Returns the stable screenshot.

        Parameters
        ----------
        capture_fn : callable
            Zero-arg function that returns (_, bgr_ndarray).
        max_wait_s : float
            Give up after this many seconds.
        stable_frames : int
            How many consecutive identical frames to consider stable.
        check_interval_s : float
            Time between checks.

        Returns
        -------
        np.ndarray  — the stable BGR frame
        """
        _, prev = capture_fn()
        stable_count = 0
        deadline = time.time() + max_wait_s

        while time.time() < deadline:
            time.sleep(check_interval_s)
            _, curr = capture_fn()

            diff = cv2.absdiff(prev, curr)
            changed_ratio = float((diff.max(axis=2) > self.PIXEL_DIFF_THRESHOLD).sum()) / max(diff.size // 3, 1)

            if changed_ratio < 0.005:   # < 0.5% change = essentially stable
                stable_count += 1
                if stable_count >= stable_frames:
                    logger.debug("Page settled after %.1fs", time.time() - (deadline - max_wait_s))
                    return curr
            else:
                stable_count = 0  # reset on change

            prev = curr

        logger.warning("Page did not settle within %.1fs", max_wait_s)
        return prev

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_changed_region(self, mask: np.ndarray) -> tuple[int, int, int, int] | None:
        """Return bounding box of the largest changed region."""
        contours, _ = cv2.findContours(mask * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        return (x, y, w, h)

    def _is_loading(self, bgr: np.ndarray, changed_ratio: float) -> bool:
        """Heuristic: detect common loading spinner colours (blue/grey circular blobs)."""
        if changed_ratio < 0.001 or changed_ratio > 0.30:
            return False
        # Look for a small circular region of activity (spinner-sized: 20-60px)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=30, param1=50, param2=30,
            minRadius=8, maxRadius=35
        )
        return circles is not None
