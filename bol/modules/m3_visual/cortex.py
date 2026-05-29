"""
Visual Cortex — Public API for Module 3.

Composes screen capture, template matching, OCR, and targeting
into a unified visual perception interface.
"""

from __future__ import annotations

import cv2
import numpy as np

from bol.config import BOLConfig
from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine
from bol.modules.m3_visual.targeting import TargetingEngine
from bol.modules.m3_visual.template import TemplateMatcher
from bol.modules.m3_visual.ai_vision import AIVisionEngine
from bol.schemas.kinematic import CursorTarget
from bol.schemas.visual import BoundingBox, ScreenCapture
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class VisualCortex:
    """
    Unified visual perception API that completely decouples
    automation logic from the browser DOM.
    """

    def __init__(self, config: BOLConfig) -> None:
        """
        Initialize all visual subsystems from configuration.

        Parameters
        ----------
        config : BOLConfig
            Global BOL configuration.
        """
        self._capture = ScreenCapturePipeline()
        self._templates = TemplateMatcher(
            templates_dir=config.resolved_templates_dir / config.target_platform,
            threshold=config.template_match_threshold,
        )
        self._ocr = OCREngine(
            tesseract_cmd=config.tesseract_cmd,
            confidence_threshold=config.ocr_confidence_threshold,
        )
        self._targeting = TargetingEngine()
        self._ai_vision = AIVisionEngine(config)

    def locate_element(self, template_name: str) -> CursorTarget | None:
        """
        Locate a UI element by template matching and compute a click target.

        Parameters
        ----------
        template_name : str
            Name of the template image (without .png extension).

        Returns
        -------
        CursorTarget | None
            Off-center click target, or None if element not found.
        """
        _, screen = self._capture.capture_full_screen()
        match = self._templates.match(screen, template_name)

        if match is None:
            logger.info("Element not found: %s", template_name)
            return None

        target = self._targeting.compute_click_target(match.bounding_box)
        logger.info(
            "Located element '%s' at (%d, %d) conf=%.3f → click (%d, %d)",
            template_name,
            match.bounding_box.x, match.bounding_box.y,
            match.confidence,
            target.click_x, target.click_y,
        )
        return target

    def locate_text(self, text: str) -> CursorTarget | None:
        """
        Locate text on screen via OCR and compute a click target.

        Parameters
        ----------
        text : str
            Text to search for.

        Returns
        -------
        CursorTarget | None
            Off-center click target on the first match, or None.
        """
        _, screen = self._capture.capture_full_screen()
        boxes = self._ocr.find_text_on_screen(screen, text)

        if not boxes:
            logger.info("Text not found on screen: '%s'", text)
            return None

        # Use the first (best) match
        target = self._targeting.compute_click_target(boxes[0])
        logger.info(
            "Located text '%s' at (%d, %d) → click (%d, %d)",
            text, boxes[0].x, boxes[0].y, target.click_x, target.click_y,
        )
        return target

    def locate_by_intent(self, intent: str) -> CursorTarget | None:
        """
        Locate a UI element by semantic intent using AI Vision, and compute a click target.

        Parameters
        ----------
        intent : str
            The high-level user intent (e.g., "book air india flight").

        Returns
        -------
        CursorTarget | None
            Off-center click target, or None if element not found.
        """
        _, screen = self._capture.capture_full_screen()
        target_text = self._ai_vision.get_target_text_for_intent(screen, intent)

        if not target_text:
            logger.info("Could not resolve intent '%s' to an on-screen target.", intent)
            return None

        logger.info("Resolved intent '%s' -> target text: '%s'. Passing to OCR.", intent, target_text)
        
        # Now find this text on screen using OCR
        boxes = self._ocr.find_text_on_screen(screen, target_text)
        if not boxes:
            logger.info("OCR failed to find the text '%s' that AI requested.", target_text)
            return None

        # Use the best match
        target = self._targeting.compute_click_target(boxes[0])
        logger.info(
            "Located intent text '%s' at (%d, %d) → click (%d, %d)",
            target_text, boxes[0].x, boxes[0].y, target.click_x, target.click_y,
        )
        return target

    def scan_for_notifications(self) -> list[BoundingBox]:
        """
        Scan the screen for red notification badges using HSV color detection.

        Returns
        -------
        list[BoundingBox]
            Bounding boxes of detected notification badges.
        """
        _, screen = self._capture.capture_full_screen()
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

        # Red spans two HSV ranges (wraps around 0/180)
        mask_low = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask_high = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask_low, mask_high)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        badges: list[BoundingBox] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter by badge-like size (8-40px)
            if 8 <= w <= 40 and 8 <= h <= 40:
                badges.append(BoundingBox(x=x, y=y, width=w, height=h, confidence=1.0))

        logger.debug("Found %d notification badges", len(badges))
        return badges

    def capture_current_state(self) -> tuple[ScreenCapture, np.ndarray]:
        """Capture the current screen state."""
        return self._capture.capture_full_screen()
