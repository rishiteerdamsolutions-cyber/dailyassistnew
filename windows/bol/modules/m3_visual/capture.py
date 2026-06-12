"""
Screen capture pipeline using mss.

Provides fast screen grabbing from the graphics buffer,
converting captures to formats usable by OpenCV and Pillow.
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime

import cv2
import mss
import numpy as np

from bol.schemas.visual import ScreenCapture, ScreenRegion
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class ScreenCapturePipeline:
    """
    High-performance screen capture pipeline using mss.

    Captures screen regions and converts them to numpy arrays
    suitable for OpenCV processing. Includes a 100ms cache
    to avoid redundant captures.
    """

    def __init__(self) -> None:
        self._sct = mss.mss()
        self._last_capture: tuple[ScreenCapture, np.ndarray] | None = None
        self._last_capture_time: float = 0.0

    def capture_full_screen(
        self, monitor_index: int = 1
    ) -> tuple[ScreenCapture, np.ndarray]:
        """
        Capture the full screen of the specified monitor.

        Parameters
        ----------
        monitor_index : int
            Monitor index (0=all monitors, 1=primary).

        Returns
        -------
        tuple[ScreenCapture, numpy.ndarray]
            Capture metadata and BGR image array for OpenCV.
        """
        # Check cache (100ms window)
        now = time.time()
        if self._last_capture is not None and (now - self._last_capture_time) < 0.1:
            return self._last_capture

        monitor = self._sct.monitors[monitor_index]
        region = ScreenRegion(
            monitor_index=monitor_index,
            left=monitor["left"],
            top=monitor["top"],
            width=monitor["width"],
            height=monitor["height"],
        )
        return self._capture(region)

    def capture_region(
        self, region: ScreenRegion
    ) -> tuple[ScreenCapture, np.ndarray]:
        """
        Capture a specific screen region.

        Parameters
        ----------
        region : ScreenRegion
            The region to capture.

        Returns
        -------
        tuple[ScreenCapture, numpy.ndarray]
            Capture metadata and BGR image array for OpenCV.
        """
        return self._capture(region)

    def _capture(
        self, region: ScreenRegion
    ) -> tuple[ScreenCapture, np.ndarray]:
        """Internal capture implementation."""
        screenshot = self._sct.grab(region.to_mss_dict())

        # Convert BGRA → BGR for OpenCV
        img_bgra = np.array(screenshot)
        img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)

        capture = ScreenCapture(
            capture_id=self._generate_capture_id(),
            region=region,
            timestamp=datetime.now(),
            width=screenshot.width,
            height=screenshot.height,
        )

        # Update cache
        self._last_capture = (capture, img_bgr)
        self._last_capture_time = time.time()

        logger.debug(
            "Captured region %dx%d at (%d, %d)",
            region.width, region.height, region.left, region.top,
        )
        return capture, img_bgr

    @staticmethod
    def _generate_capture_id() -> str:
        """Generate a unique capture identifier."""
        return secrets.token_hex(8)
