"""
OpenCV template matching engine.

Locates UI elements on screen by matching reference template
images at multiple scales using normalized cross-correlation.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from bol.schemas.visual import BoundingBox, TemplateMatch
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateMatcher:
    """
    Multi-scale template matching using OpenCV's TM_CCOEFF_NORMED.

    Loads reference template images and matches them against
    live screen captures at multiple scales for resilience.
    """

    _SCALES = [0.9, 0.95, 1.0, 1.05, 1.1]

    def __init__(self, templates_dir: Path, threshold: float = 0.75) -> None:
        """
        Initialize with a directory of PNG template images.

        Parameters
        ----------
        templates_dir : Path
            Directory containing reference template PNGs.
        threshold : float
            Minimum confidence for a valid match.
        """
        self._threshold = threshold
        self._templates: dict[str, np.ndarray] = {}
        self._load_templates(templates_dir)

    def _load_templates(self, templates_dir: Path) -> None:
        """Load all PNG templates and convert to grayscale."""
        if not templates_dir.exists():
            logger.warning("Templates directory does not exist: %s", templates_dir)
            return

        for png_path in templates_dir.glob("*.png"):
            name = png_path.stem
            img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self._templates[name] = img
                logger.info("Loaded template: %s (%dx%d)", name, img.shape[1], img.shape[0])

    def match(
        self, screen_bgr: np.ndarray, template_name: str
    ) -> TemplateMatch | None:
        """
        Match a named template against the screen at multiple scales.

        Parameters
        ----------
        screen_bgr : numpy.ndarray
            BGR screen capture.
        template_name : str
            Name of the template to match.

        Returns
        -------
        TemplateMatch | None
            Best match above threshold, or None.
        """
        if template_name not in self._templates:
            logger.warning("Template not found: %s", template_name)
            return None

        template = self._templates[template_name]
        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

        best_confidence = 0.0
        best_location = (0, 0)
        best_scale = 1.0
        best_size = (template.shape[1], template.shape[0])

        for scale in self._SCALES:
            resized = self._resize_template(template, scale)
            rh, rw = resized.shape[:2]

            # Skip if template is larger than screen
            if rw > screen_gray.shape[1] or rh > screen_gray.shape[0]:
                continue

            result = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_confidence:
                best_confidence = max_val
                best_location = max_loc
                best_scale = scale
                best_size = (rw, rh)

        if best_confidence >= self._threshold:
            bbox = BoundingBox(
                x=best_location[0],
                y=best_location[1],
                width=best_size[0],
                height=best_size[1],
                confidence=best_confidence,
            )
            return TemplateMatch(
                template_name=template_name,
                bounding_box=bbox,
                confidence=best_confidence,
                scale=best_scale,
            )

        logger.debug(
            "Template '%s' best match: %.3f (below threshold %.3f)",
            template_name, best_confidence, self._threshold,
        )
        return None

    def match_any(
        self, screen_bgr: np.ndarray, template_names: list[str]
    ) -> TemplateMatch | None:
        """Match any of the given templates, returning the best match."""
        best_match: TemplateMatch | None = None
        for name in template_names:
            match = self.match(screen_bgr, name)
            if match is not None:
                if best_match is None or match.confidence > best_match.confidence:
                    best_match = match
        return best_match

    @staticmethod
    def _resize_template(template: np.ndarray, scale: float) -> np.ndarray:
        """Resize a template by the given scale factor."""
        if abs(scale - 1.0) < 0.01:
            return template
        h, w = template.shape[:2]
        new_w = max(int(w * scale), 1)
        new_h = max(int(h * scale), 1)
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        return cv2.resize(template, (new_w, new_h), interpolation=interp)
