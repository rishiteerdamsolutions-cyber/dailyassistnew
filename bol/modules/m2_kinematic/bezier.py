"""
Cubic Bezier trajectory engine.

Implements the mathematical foundation for organic mouse cursor
movements using cubic Bezier curves with randomized control points.
"""

from __future__ import annotations

import math
import secrets

import numpy as np

from bol.schemas.kinematic import BezierControlPoints, Point2D


class BezierEngine:
    """
    Generates cubic Bezier curve trajectories for mouse movement.

    The core formula:
        B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
    """

    @staticmethod
    def generate_control_points(start: Point2D, end: Point2D) -> BezierControlPoints:
        """
        Generate randomized control points for a cubic Bezier curve.

        P₁ and P₂ are offset perpendicular to the direct start→end line,
        with distances proportional to the path length (15-40%).

        Parameters
        ----------
        start : Point2D
            Starting cursor position (P₀).
        end : Point2D
            Target position (P₃).

        Returns
        -------
        BezierControlPoints
            Four control points defining the cubic Bezier curve.
        """
        dx = end.x - start.x
        dy = end.y - start.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1.0:
            # Near-zero distance — return degenerate curve
            return BezierControlPoints(p0=start, p1=start, p2=end, p3=end)

        # Perpendicular direction (normalized)
        perp_x = -dy / distance
        perp_y = dx / distance

        # Offset magnitude: 15-40% of direct distance
        def _rand_offset() -> float:
            pct = 15 + secrets.randbelow(26)  # 15 to 40
            sign = 1 if secrets.randbelow(2) == 0 else -1
            return sign * distance * (pct / 100.0)

        offset1 = _rand_offset()
        offset2 = _rand_offset()

        # P1: ~25-35% along the direct path + perpendicular offset
        t1 = 0.25 + (secrets.randbelow(11) / 100.0)  # 0.25 to 0.35
        p1 = Point2D(
            x=start.x + dx * t1 + perp_x * offset1,
            y=start.y + dy * t1 + perp_y * offset1,
        )

        # P2: ~65-75% along the direct path + perpendicular offset
        t2 = 0.65 + (secrets.randbelow(11) / 100.0)  # 0.65 to 0.75
        p2 = Point2D(
            x=start.x + dx * t2 + perp_x * offset2,
            y=start.y + dy * t2 + perp_y * offset2,
        )

        return BezierControlPoints(p0=start, p1=p1, p2=p2, p3=end)

    @staticmethod
    def sample_trajectory(
        control_points: BezierControlPoints,
        num_steps: int = 80,
    ) -> list[Point2D]:
        """
        Sample discrete points along the cubic Bezier curve.

        Uses non-linear time parameterization (ease-out) so the cursor
        starts faster and decelerates near the target.

        Parameters
        ----------
        control_points : BezierControlPoints
            The four control points of the curve.
        num_steps : int
            Number of discrete points to sample.

        Returns
        -------
        list[Point2D]
            Sampled positions along the curve.
        """
        p0 = np.array([control_points.p0.x, control_points.p0.y])
        p1 = np.array([control_points.p1.x, control_points.p1.y])
        p2 = np.array([control_points.p2.x, control_points.p2.y])
        p3 = np.array([control_points.p3.x, control_points.p3.y])

        # Linear parameter space
        t_linear = np.linspace(0.0, 1.0, num_steps)

        # Apply ease-out: t_mapped = 1 - (1-t)^2 → faster start, slower end
        t_mapped = 1.0 - (1.0 - t_linear) ** 2

        # Cubic Bezier formula (vectorized)
        one_minus_t = 1.0 - t_mapped
        points_x = (
            one_minus_t**3 * p0[0]
            + 3 * one_minus_t**2 * t_mapped * p1[0]
            + 3 * one_minus_t * t_mapped**2 * p2[0]
            + t_mapped**3 * p3[0]
        )
        points_y = (
            one_minus_t**3 * p0[1]
            + 3 * one_minus_t**2 * t_mapped * p1[1]
            + 3 * one_minus_t * t_mapped**2 * p2[1]
            + t_mapped**3 * p3[1]
        )

        return [Point2D(x=float(x), y=float(y)) for x, y in zip(points_x, points_y)]

    @staticmethod
    def calculate_duration_ms(distance: float) -> float:
        """
        Calculate movement duration based on pixel distance.

        Formula: base 200ms + 2ms per pixel, with ±15% entropy jitter.

        Parameters
        ----------
        distance : float
            Euclidean distance in pixels.

        Returns
        -------
        float
            Duration in milliseconds.
        """
        base = 200.0 + 2.0 * distance
        # ±15% jitter
        jitter_pct = (secrets.randbelow(31) - 15) / 100.0  # -0.15 to +0.15
        return max(base * (1.0 + jitter_pct), 100.0)
