"""
Vision Button Library — Template matching against saved button screenshots.

Uses OpenCV matchTemplate to find saved button images on the live screen.
Zero footprint: pure pixel math, no JS, no DOM.

This solves the #1 OCR blind spot: icon-only buttons (+ on Instagram,
photo icons, send arrows) that have no readable text.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from bol.schemas.visual import BoundingBox
from bol.utils.logging import get_logger

logger = get_logger(__name__)


def _visionbuttons_root() -> Path:
    try:
        from aha.runtime_paths import resource_path

        bundled = resource_path("VISIONBUTTONS")
        if bundled.is_dir():
            return bundled
    except Exception:
        pass
    return Path(__file__).parent.parent.parent.parent / "VISIONBUTTONS"


def _platform_dirs() -> dict[str, Path]:
    """Resolve at runtime — Nuitka bundle paths differ from dev checkout."""
    root = _visionbuttons_root()
    return {
        "facebook": root / "facebookbuttons",
        "instagram": root / "instagrambuttons",
        "linkedin": root / "linkedinbuttons",
        "x": root / "xbuttons",
        "whatsapp": root / "whatsappbuttons",
    }


@dataclass
class TemplateMatch:
    template_name: str       # e.g. "instagram_share_button"
    bbox: BoundingBox        # location on screen
    confidence: float        # 0.0 – 1.0 (1.0 = perfect match)


class VisionButtonLibrary:
    """
    Finds saved button templates on the live screenshot using
    multi-scale OpenCV template matching.

    Usage:
        lib = VisionButtonLibrary()
        match = lib.find("instagram_share_button", screenshot_bgr)
        if match:
            click(match.bbox.center_x, match.bbox.center_y)
    """

    # Confidence threshold to accept a match (lower = more false positives)
    MIN_CONFIDENCE = 0.65

    # Templates are captured at Retina 2x density.
    # mss live captures at 1x logical resolution.
    # Primary scale is 0.5 (halve the template). Others handle zoom/variation.
    # We include very small scales (0.2 - 0.35) to match mobile templates against tiny desktop icons.
    SCALES = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.85, 1.0]

    def __init__(self) -> None:
        self._cache: dict[str, np.ndarray] = {}   # template_name → BGR image
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        """Pre-load all button templates into memory."""
        for platform, folder in _platform_dirs().items():
            if not folder.exists():
                continue
            for img_path in folder.glob("*.png"):
                name = img_path.stem   # e.g. "instagram_share_button"
                tmpl = cv2.imread(str(img_path))
                if tmpl is not None:
                    self._cache[name] = tmpl
                    logger.debug("Loaded template: %s (%dx%d)", name, tmpl.shape[1], tmpl.shape[0])

        logger.info("VisionButtonLibrary: %d templates loaded", len(self._cache))

    def reload(self) -> None:
        """Reload all templates from disk (call after adding new screenshots)."""
        self._cache.clear()
        self._load_all_templates()

    def find(
        self,
        template_name: str,
        screenshot_bgr: np.ndarray,
        min_confidence: float | None = None,
    ) -> TemplateMatch | None:
        """
        Search for a named button template in the screenshot.

        Parameters
        ----------
        template_name : str
            Stem of the template file, e.g. "instagram_share_button".
        screenshot_bgr : np.ndarray
            Live screen capture in BGR format.
        min_confidence : float | None
            Override default confidence threshold.

        Returns
        -------
        TemplateMatch | None
            Best match found, or None if below threshold.
        """
        threshold = min_confidence if min_confidence is not None else self.MIN_CONFIDENCE
        tmpl = self._cache.get(template_name)
        if tmpl is None:
            logger.warning("Template not found in library: %s", template_name)
            return None

        best_conf = 0.0
        best_loc = None
        best_scale = 1.0
        th, tw = tmpl.shape[:2]

        for scale in self.SCALES:
            scaled_tmpl = cv2.resize(tmpl, (max(1, int(tw * scale)), max(1, int(th * scale))))
            st_h, st_w = scaled_tmpl.shape[:2]

            if st_h > screenshot_bgr.shape[0] or st_w > screenshot_bgr.shape[1]:
                continue

            templates_to_check = [scaled_tmpl, cv2.bitwise_not(scaled_tmpl)]
            
            for tmpl_variant in templates_to_check:
                result = cv2.matchTemplate(screenshot_bgr, tmpl_variant, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > best_conf:
                    best_conf = max_val
                    best_loc = max_loc
                    best_scale = scale

        if best_conf < threshold or best_loc is None:
            logger.debug("Template '%s' not found (best conf=%.3f < %.3f)",
                         template_name, best_conf, threshold)
            return None

        # Compute bounding box in original screen coordinates
        matched_w = int(tw * best_scale)
        matched_h = int(th * best_scale)
        x, y = best_loc

        bbox = BoundingBox(
            x=x, y=y,
            width=matched_w, height=matched_h,
            confidence=best_conf,
        )
        logger.info("Template '%s' matched at (%d,%d) conf=%.3f scale=%.2f",
                    template_name, x, y, best_conf, best_scale)
        return TemplateMatch(template_name=template_name, bbox=bbox, confidence=best_conf)

    def find_all(
        self,
        template_name: str,
        screenshot_bgr: np.ndarray,
        min_confidence: float | None = None,
        nms_threshold: int = 15,
    ) -> list[TemplateMatch]:
        """
        Search for ALL instances of a named button template in the screenshot.
        Applies simple distance-based NMS to avoid overlapping matches.
        """
        threshold = min_confidence if min_confidence is not None else self.MIN_CONFIDENCE
        tmpl = self._cache.get(template_name)
        if tmpl is None:
            logger.warning("Template not found in library: %s", template_name)
            return []

        th, tw = tmpl.shape[:2]
        matches: list[TemplateMatch] = []
        raw_peaks = []

        for scale in self.SCALES:
            scaled_tmpl = cv2.resize(tmpl, (max(1, int(tw * scale)), max(1, int(th * scale))))
            st_h, st_w = scaled_tmpl.shape[:2]

            if st_h > screenshot_bgr.shape[0] or st_w > screenshot_bgr.shape[1]:
                continue

            # Check both normal and inverted (for dark mode compatibility)
            templates_to_check = [scaled_tmpl, cv2.bitwise_not(scaled_tmpl)]
            
            for tmpl_variant in templates_to_check:
                result = cv2.matchTemplate(screenshot_bgr, tmpl_variant, cv2.TM_CCOEFF_NORMED)
                yloc, xloc = np.where(result >= threshold)
                for (x, y) in zip(xloc, yloc):
                    conf = result[y, x]
                    raw_peaks.append((x, y, st_w, st_h, conf, scale))

        raw_peaks.sort(key=lambda p: p[4], reverse=True)
        final_peaks = []
        for p in raw_peaks:
            x, y, w, h, conf, scale = p
            overlap = False
            for fp in final_peaks:
                fx, fy, _, _, _, _ = fp
                if np.hypot(x - fx, y - fy) < nms_threshold:
                    overlap = True
                    break
            if not overlap:
                final_peaks.append(p)

        for p in final_peaks:
            x, y, w, h, conf, scale = p
            bbox = BoundingBox(x=x, y=y, width=w, height=h, confidence=float(conf))
            matches.append(TemplateMatch(template_name=template_name, bbox=bbox, confidence=float(conf)))

        logger.info("Template '%s' found %d instances above conf %.2f", template_name, len(matches), threshold)
        return matches

    def find_any(
        self,
        template_names: list[str],
        screenshot_bgr: np.ndarray,
        min_confidence: float | None = None,
    ) -> TemplateMatch | None:
        """
        Try multiple templates and return the best match found.
        Useful when a button might appear in different states.
        """
        best: TemplateMatch | None = None
        for name in template_names:
            m = self.find(name, screenshot_bgr, min_confidence)
            if m and (best is None or m.confidence > best.confidence):
                best = m
        return best

    def find_for_platform_action(
        self,
        platform: str,
        action: str,
        screenshot_bgr: np.ndarray,
    ) -> TemplateMatch | None:
        """
        Convenience: find a button by platform + action.

        Example: find_for_platform_action("instagram", "share", screenshot)
        will try: instagram_share_button, instagram_share_icon
        """
        candidates = [
            f"{platform}_{action}_button",
            f"{platform}_{action}_icon",
            f"{platform}_{action}",
        ]
        return self.find_any(candidates, screenshot_bgr)

    def list_templates(self) -> list[str]:
        """Return all loaded template names."""
        return sorted(self._cache.keys())
