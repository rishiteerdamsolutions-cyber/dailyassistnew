"""
UI Element Detector — Pure computer vision, zero DOM access, zero footprint.

Detects ALL interactive elements (buttons, inputs, links, dropdowns, checkboxes)
from a raw screenshot using multi-strategy OpenCV analysis.

Returns numbered bounding boxes (Set-of-Marks) so the LLM only needs to pick
a number — never guess coordinates.
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional
from bol.schemas.visual import BoundingBox
from bol.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UIElement:
    """A detected interactive UI element."""
    index: int
    bbox: BoundingBox
    element_type: str          # 'button' | 'input' | 'link' | 'dropdown' | 'unknown'
    confidence: float          # 0.0 – 1.0
    ocr_text: str = ""         # text found inside this element (filled by caller)
    is_disabled: bool = False  # visually appears greyed out


class UIElementDetector:
    """
    Pure vision detector for interactive UI elements.
    No JS, no DOM, no browser APIs. Just pixel analysis.

    Strategy (applied in order, results merged + deduplicated):
    1. Filled rectangle detection  — coloured button backgrounds
    2. Border rectangle detection  — input fields, outlined buttons
    3. Canny + contour grouping    — complex/custom UI components
    4. Colour region clustering    — icon buttons, toggles
    """

    # Minimum/maximum element sizes in pixels
    MIN_W, MIN_H = 12, 10
    MAX_W_RATIO = 0.95   # fraction of screen width
    MAX_H_RATIO = 0.40   # fraction of screen height
    MIN_ASPECT = 0.3     # allow tall narrow elements (checkboxes)
    MAX_ASPECT = 20.0    # avoid full-width dividers

    # Deduplication IoU threshold
    IOU_THRESH = 0.50

    def detect(self, bgr: np.ndarray) -> list[UIElement]:
        """
        Run all detection strategies and return a deduplicated, indexed list.

        Parameters
        ----------
        bgr : np.ndarray
            Full screenshot in BGR format.

        Returns
        -------
        list[UIElement]
            Sorted top-to-bottom, left-to-right, with sequential .index values.
        """
        h, w = bgr.shape[:2]
        candidates: list[tuple[int, int, int, int, str, float]] = []  # (x,y,w,h,type,conf)

        candidates.extend(self._detect_filled_buttons(bgr, w, h))
        candidates.extend(self._detect_border_boxes(bgr, w, h))
        candidates.extend(self._detect_canny_contours(bgr, w, h))

        # Filter by size
        filtered = [
            c for c in candidates
            if c[2] >= self.MIN_W and c[3] >= self.MIN_H
            and c[2] <= w * self.MAX_W_RATIO
            and c[3] <= h * self.MAX_H_RATIO
            and self.MIN_ASPECT <= c[2] / max(c[3], 1) <= self.MAX_ASPECT
        ]

        # Non-maximum suppression (keep highest-confidence within each cluster)
        kept = self._nms(filtered)

        # Sort spatially: top-to-bottom, left-to-right
        kept.sort(key=lambda c: (c[1] // 20, c[0]))

        elements: list[UIElement] = []
        for idx, (x, y, ew, eh, etype, conf) in enumerate(kept):
            is_disabled = self._check_disabled(bgr, x, y, ew, eh)
            elements.append(UIElement(
                index=idx,
                bbox=BoundingBox(x=x, y=y, width=ew, height=eh, confidence=conf),
                element_type=etype,
                confidence=conf,
                is_disabled=is_disabled,
            ))

        logger.debug("UIElementDetector: found %d elements", len(elements))
        return elements

    # ------------------------------------------------------------------
    # Strategy 1: Filled coloured rectangles (solid CTA buttons)
    # ------------------------------------------------------------------
    def _detect_filled_buttons(self, bgr, sw, sh):
        results = []
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Look for regions of uniform colour that differ from their neighbours
        blurred = cv2.GaussianBlur(bgr, (3, 3), 0)
        lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)

        # Edges in colour space reveal button boundaries
        l_channel = lab[:, :, 0]
        edge_l = cv2.Canny(l_channel, 10, 40)

        # Dilate to connect nearby edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edge_l, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 30 or h < 14:
                continue
            aspect = w / max(h, 1)
            if 1.2 <= aspect <= 15 and 14 <= h <= 80:
                # Check for uniform fill inside
                roi = bgr[y:y+h, x:x+w]
                if roi.size == 0:
                    continue
                std = np.std(roi.reshape(-1, 3), axis=0).mean()
                if std < 45:  # low variance = solid background = likely button
                    results.append((x, y, w, h, 'button', 0.75))

        return results

    # ------------------------------------------------------------------
    # Strategy 2: Border/outline boxes (inputs, outlined buttons)
    # ------------------------------------------------------------------
    def _detect_border_boxes(self, bgr, sw, sh):
        results = []
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Use Canny with tight thresholds to find borders
        edges = cv2.Canny(gray, 30, 90)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 40 or h < 14:
                continue
            aspect = w / max(h, 1)
            if aspect < 0.5 or aspect > 20:
                continue

            # Check: does this contour form a closed rectangle?
            # Approximate to polygon and check rectangularity
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) < 4:
                continue

            # Input fields are typically tall relative to the content
            if 20 <= h <= 55 and w > 60:
                etype = 'input' if aspect >= 3 else 'button'
                results.append((x, y, w, h, etype, 0.70))
            elif 14 <= h <= 50 and 40 <= w:
                results.append((x, y, w, h, 'button', 0.65))

        return results

    # ------------------------------------------------------------------
    # Strategy 3: Canny + contour grouping for custom components
    # ------------------------------------------------------------------
    def _detect_canny_contours(self, bgr, sw, sh):
        results = []
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 2))
        dilated = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 30 or h < 12:
                continue
            aspect = w / max(h, 1)
            if 1.0 <= aspect <= 12 and 12 <= h <= 70:
                results.append((x, y, w, h, 'unknown', 0.55))

        return results

    # ------------------------------------------------------------------
    # Non-maximum suppression — remove overlapping duplicates
    # ------------------------------------------------------------------
    def _nms(self, candidates):
        if not candidates:
            return []

        # Sort by confidence descending
        candidates = sorted(candidates, key=lambda c: c[5], reverse=True)
        kept = []

        for c in candidates:
            cx, cy, cw, ch = c[0], c[1], c[2], c[3]
            is_dup = False
            for k in kept:
                iou = self._iou(cx, cy, cw, ch, k[0], k[1], k[2], k[3])
                if iou > self.IOU_THRESH:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(c)

        return kept

    @staticmethod
    def _iou(ax, ay, aw, ah, bx, by, bw, bh) -> float:
        ix1 = max(ax, bx)
        iy1 = max(ay, by)
        ix2 = min(ax + aw, bx + bw)
        iy2 = min(ay + ah, by + bh)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        union = aw * ah + bw * bh - inter
        return inter / max(union, 1)

    # ------------------------------------------------------------------
    # Check if an element appears visually disabled (greyed out)
    # ------------------------------------------------------------------
    def _check_disabled(self, bgr, x, y, w, h) -> bool:
        roi = bgr[y:y+h, x:x+w]
        if roi.size == 0:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_val = float(np.mean(gray))
        std_val = float(np.std(gray))
        # Disabled elements tend to be very light grey with low contrast
        return 180 <= mean_val <= 230 and std_val < 20

    # ------------------------------------------------------------------
    # Draw numbered overlays onto a copy of the image (for LLM vision)
    # ------------------------------------------------------------------
    def draw_som_overlay(
        self,
        bgr: np.ndarray,
        elements: list[UIElement],
        color: tuple[int, int, int] = (0, 220, 0),
        disabled_color: tuple[int, int, int] = (120, 120, 120),
    ) -> np.ndarray:
        """
        Draw green numbered boxes on every detected element.
        Disabled elements are drawn in grey.
        Returns a new image — original is not modified.
        """
        overlay = bgr.copy()
        for el in elements:
            b = el.bbox
            c = disabled_color if el.is_disabled else color
            cv2.rectangle(overlay, (b.x, b.y), (b.x + b.width, b.y + b.height), c, 2)

            # Label background
            label = f"[{el.index}]"
            font = cv2.FONT_HERSHEY_SIMPLEX
            fs, thick = 0.45, 1
            (tw, th), _ = cv2.getTextSize(label, font, fs, thick)
            lx, ly = b.x, max(b.y - 4, th + 2)
            cv2.rectangle(overlay, (lx, ly - th - 2), (lx + tw + 2, ly + 2), c, -1)
            cv2.putText(overlay, label, (lx + 1, ly), font, fs, (0, 0, 0), thick, cv2.LINE_AA)

        return overlay
