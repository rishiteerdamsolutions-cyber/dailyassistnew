"""
Human overshoot and correction engine.

Simulates the natural human behavior of overshooting a target
with the mouse cursor and then making micro-corrections.
"""

from __future__ import annotations

import math
import secrets

from bol.schemas.kinematic import Point2D


class OvershootEngine:
    """
    Applies human-like overshoot and damped spring correction
    to cursor trajectories near their target.
    """

    def should_overshoot(self, distance: float) -> bool:
        """
        Determine whether to apply overshoot based on movement distance.

        Probability scales with distance:
        - 30% at 100px
        - 50% at 300px
        - 70% at 500px+

        Parameters
        ----------
        distance : float
            Total movement distance in pixels.

        Returns
        -------
        bool
            True if overshoot should be applied.
        """
        # Logistic-ish curve: probability = 0.2 + 0.5 * (1 - e^(-d/300))
        prob = 0.2 + 0.5 * (1.0 - math.exp(-distance / 300.0))
        prob = min(prob, 0.8)
        return secrets.randbelow(1000) / 1000.0 < prob

    def apply_overshoot(
        self, trajectory: list[Point2D], target: Point2D
    ) -> list[Point2D]:
        """
        Extend a trajectory with overshoot and damped spring corrections.

        The cursor overshoots the target by 3-12px, then oscillates
        with exponential decay until settling on the target.

        Parameters
        ----------
        trajectory : list[Point2D]
            Original trajectory ending at or near the target.
        target : Point2D
            The intended final position.

        Returns
        -------
        list[Point2D]
            Extended trajectory with overshoot and correction points.
        """
        if len(trajectory) < 2:
            return trajectory

        result = list(trajectory)

        # Calculate approach direction from last two points
        last = trajectory[-1]
        prev = trajectory[-2]
        dx = last.x - prev.x
        dy = last.y - prev.y
        approach_speed = math.sqrt(dx * dx + dy * dy)

        if approach_speed < 0.5:
            return result

        # Normalize approach direction
        dir_x = dx / approach_speed
        dir_y = dy / approach_speed

        # Overshoot distance: 3-12px, scaled by approach speed
        overshoot_base = 3 + secrets.randbelow(10)  # 3 to 12
        overshoot_scale = min(approach_speed / 5.0, 2.0)
        overshoot_dist = overshoot_base * max(overshoot_scale, 0.5)

        # Overshoot point
        overshoot_pt = Point2D(
            x=target.x + dir_x * overshoot_dist,
            y=target.y + dir_y * overshoot_dist,
        )
        result.append(overshoot_pt)

        # Damped spring correction: 1-3 micro-corrections
        num_corrections = 1 + secrets.randbelow(3)  # 1 to 3
        zeta = 0.5 + secrets.randbelow(31) / 100.0  # 0.5 to 0.8 damping ratio
        omega = 2.0 * math.pi / 4.0  # Natural frequency

        current = overshoot_pt
        for i in range(1, num_corrections + 1):
            t = float(i) / (num_corrections + 1)
            decay = math.exp(-zeta * omega * t)
            oscillation = math.cos(omega * t)

            # Correction moves toward target with damped oscillation
            correction_x = target.x + (current.x - target.x) * decay * oscillation * 0.3
            correction_y = target.y + (current.y - target.y) * decay * oscillation * 0.3

            correction_pt = Point2D(x=correction_x, y=correction_y)
            result.append(correction_pt)
            current = correction_pt

        # Final settling point at target
        result.append(target)
        return result
