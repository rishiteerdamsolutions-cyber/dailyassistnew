"""
Kinematic Synthesizer — Public API for Module 2.

Orchestrates Bezier trajectory generation, overshoot correction,
and scroll physics into a unified motion planning interface.
"""

from __future__ import annotations

from bol.modules.m2_kinematic.bezier import BezierEngine
from bol.modules.m2_kinematic.overshoot import OvershootEngine
from bol.modules.m2_kinematic.scroll import ScrollEngine
from bol.schemas.kinematic import (
    BezierPath,
    CursorTarget,
    Point2D,
    ScrollDirection,
    ScrollProfile,
)
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class KinematicSynthesizer:
    """
    Unified motion planning API composing Bezier curves,
    overshoot correction, and scroll physics.
    """

    def __init__(self) -> None:
        self._bezier = BezierEngine()
        self._overshoot = OvershootEngine()
        self._scroll = ScrollEngine()

    def generate_movement(
        self, start: Point2D, target: CursorTarget, num_steps: int = 80
    ) -> BezierPath:
        """
        Generate a complete cursor movement trajectory to a target.

        Parameters
        ----------
        start : Point2D
            Current cursor position.
        target : CursorTarget
            Target with off-center click coordinates.
        num_steps : int
            Number of trajectory sample points.

        Returns
        -------
        BezierPath
            Complete trajectory with optional overshoot.
        """
        end = Point2D(x=float(target.click_x), y=float(target.click_y))
        distance = start.distance_to(end)

        # Generate Bezier control points and sample trajectory
        control_points = BezierEngine.generate_control_points(start, end)
        trajectory = BezierEngine.sample_trajectory(control_points, num_steps)

        # Apply overshoot based on distance
        includes_overshoot = False
        if distance > 50 and self._overshoot.should_overshoot(distance):
            trajectory = self._overshoot.apply_overshoot(trajectory, end)
            includes_overshoot = True

        duration = BezierEngine.calculate_duration_ms(distance)

        path = BezierPath(
            control_points=control_points,
            trajectory_points=trajectory,
            total_duration_ms=duration,
            num_steps=len(trajectory),
            includes_overshoot=includes_overshoot,
        )

        logger.debug(
            "Generated movement: %.0fpx, %d steps, %.0fms, overshoot=%s",
            distance, len(trajectory), duration, includes_overshoot,
        )
        return path

    def generate_scroll(
        self, distance_px: int, direction: ScrollDirection
    ) -> ScrollProfile:
        """
        Generate a scroll operation profile.

        Parameters
        ----------
        distance_px : int
            Total scroll distance in pixels.
        direction : ScrollDirection
            Scroll direction.

        Returns
        -------
        ScrollProfile
            Complete scroll plan with velocity curve and stutters.
        """
        profile = self._scroll.generate_scroll_profile(distance_px, direction)
        logger.debug(
            "Generated scroll: %dpx %s, %d steps, %.0fms, %d stutters",
            distance_px, direction.value, profile.num_steps,
            profile.total_duration_ms, len(profile.micro_stutters),
        )
        return profile
