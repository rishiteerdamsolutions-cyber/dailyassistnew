"""
Off-center click coordinate targeting engine.

Ensures the system NEVER clicks the exact mathematical center
of a UI element, applying bounded random offsets within the
bounding box perimeter.
"""

from __future__ import annotations

import secrets

from bol.schemas.kinematic import CursorTarget
from bol.schemas.visual import BoundingBox


class TargetingEngine:
    """
    Computes off-center click coordinates within a bounding box.

    The offset is 15-40% from center toward any direction,
    guaranteeing the exact center is never selected.
    """

    _MARGIN_PX = 2  # Minimum margin from bounding box edges

    def compute_click_target(self, bbox: BoundingBox) -> CursorTarget:
        """
        Compute an off-center click point within a bounding box.

        Parameters
        ----------
        bbox : BoundingBox
            The UI element's bounding box.

        Returns
        -------
        CursorTarget
            Click target with offset coordinates.
        """
        center_x = bbox.x + bbox.width // 2
        center_y = bbox.y + bbox.height // 2

        half_w = max(bbox.width // 2 - self._MARGIN_PX, 1)
        half_h = max(bbox.height // 2 - self._MARGIN_PX, 1)

        offset_x, offset_y = self._generate_offset(half_w, half_h)

        # Ensure offset is never zero on both axes
        if offset_x == 0 and offset_y == 0:
            offset_x = 1 if secrets.randbelow(2) == 0 else -1

        click_x = center_x + offset_x
        click_y = center_y + offset_y

        # Clamp to bounding box with margin
        click_x = max(bbox.x + self._MARGIN_PX, min(click_x, bbox.right - self._MARGIN_PX))
        click_y = max(bbox.y + self._MARGIN_PX, min(click_y, bbox.bottom - self._MARGIN_PX))

        return CursorTarget(
            bounding_box_x=bbox.x,
            bounding_box_y=bbox.y,
            bounding_box_width=bbox.width,
            bounding_box_height=bbox.height,
            click_x=click_x,
            click_y=click_y,
            offset_from_center_x=click_x - center_x,
            offset_from_center_y=click_y - center_y,
        )

    def _generate_offset(self, half_width: int, half_height: int) -> tuple[int, int]:
        """
        Generate a random offset from center.

        Magnitude: 15-40% of half_width/half_height.
        Direction: random quadrant selection.
        """
        # Offset percentage: 3% to 12% (small offset for precision on web buttons)
        pct_x = 3 + secrets.randbelow(10)  # 3 to 12
        pct_y = 3 + secrets.randbelow(10)

        # Calculate pixel offset
        mag_x = max(int(half_width * pct_x / 100), 1)
        mag_y = max(int(half_height * pct_y / 100), 1)

        # Random direction per axis
        sign_x = 1 if secrets.randbelow(2) == 0 else -1
        sign_y = 1 if secrets.randbelow(2) == 0 else -1

        return sign_x * mag_x, sign_y * mag_y
