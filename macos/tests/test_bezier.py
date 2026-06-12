"""
Tests for the Cubic Bezier trajectory engine (Module 2).

Validates:
- Control point generation
- Trajectory sampling (start/end point accuracy)
- Curve smoothness
- Overshoot and correction
- Duration calculation
"""

from __future__ import annotations

import math

from bol.schemas.kinematic import Point2D, BezierControlPoints


class TestBezierControlPoints:
    """Test control point generation."""

    def test_control_points_structure(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=100.0, y=100.0)
        end = Point2D(x=500.0, y=400.0)
        cp = BezierEngine.generate_control_points(start, end)

        assert cp.p0 == start
        assert cp.p3 == end
        # P1 and P2 should not be at start or end
        assert cp.p1 != start
        assert cp.p2 != end

    def test_control_points_bounded(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=100.0, y=100.0)
        end = Point2D(x=500.0, y=400.0)

        # Run multiple times to check bounds
        for _ in range(20):
            cp = BezierEngine.generate_control_points(start, end)
            # Control points should be within reasonable bounds of start/end
            for p in [cp.p1, cp.p2]:
                assert -200 < p.x < 800, f"Control point X out of bounds: {p.x}"
                assert -200 < p.y < 700, f"Control point Y out of bounds: {p.y}"


class TestBezierTrajectory:
    """Test trajectory sampling."""

    def test_trajectory_starts_at_p0(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=100.0, y=200.0)
        end = Point2D(x=400.0, y=300.0)
        cp = BezierEngine.generate_control_points(start, end)
        trajectory = BezierEngine.sample_trajectory(cp, num_steps=50)

        assert len(trajectory) == 50
        # First point should be very close to start
        assert abs(trajectory[0].x - start.x) < 1.0
        assert abs(trajectory[0].y - start.y) < 1.0

    def test_trajectory_ends_near_p3(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=100.0, y=200.0)
        end = Point2D(x=400.0, y=300.0)
        cp = BezierEngine.generate_control_points(start, end)
        trajectory = BezierEngine.sample_trajectory(cp, num_steps=50)

        # Last point should be very close to end
        assert abs(trajectory[-1].x - end.x) < 1.0
        assert abs(trajectory[-1].y - end.y) < 1.0

    def test_trajectory_is_smooth(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=0.0, y=0.0)
        end = Point2D(x=500.0, y=500.0)
        cp = BezierEngine.generate_control_points(start, end)
        trajectory = BezierEngine.sample_trajectory(cp, num_steps=100)

        # Check that consecutive points are not too far apart
        for i in range(1, len(trajectory)):
            dx = trajectory[i].x - trajectory[i - 1].x
            dy = trajectory[i].y - trajectory[i - 1].y
            dist = math.sqrt(dx * dx + dy * dy)
            assert dist < 50.0, f"Jump too large between points {i-1} and {i}: {dist}"

    def test_trajectory_not_linear(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        start = Point2D(x=0.0, y=0.0)
        end = Point2D(x=400.0, y=0.0)
        cp = BezierEngine.generate_control_points(start, end)
        trajectory = BezierEngine.sample_trajectory(cp, num_steps=50)

        # At least some points should have non-zero Y (curve deviates from straight line)
        y_values = [p.y for p in trajectory[5:-5]]  # Exclude near-endpoints
        max_deviation = max(abs(y) for y in y_values)
        assert max_deviation > 1.0, "Trajectory appears linear — should be curved"


class TestBezierDuration:
    """Test duration calculation."""

    def test_duration_scales_with_distance(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        short_dist = 100.0
        long_dist = 800.0
        dur_short = BezierEngine.calculate_duration_ms(short_dist)
        dur_long = BezierEngine.calculate_duration_ms(long_dist)

        assert dur_long > dur_short, "Longer distance should take longer"

    def test_duration_positive(self) -> None:
        from bol.modules.m2_kinematic.bezier import BezierEngine

        duration = BezierEngine.calculate_duration_ms(50.0)
        assert duration > 0


class TestOvershoot:
    """Test overshoot and correction behavior."""

    def test_overshoot_extends_trajectory(self) -> None:
        from bol.modules.m2_kinematic.overshoot import OvershootEngine

        target = Point2D(x=400.0, y=300.0)
        # Create a simple trajectory approaching the target
        trajectory = [
            Point2D(x=100.0, y=100.0),
            Point2D(x=200.0, y=175.0),
            Point2D(x=300.0, y=250.0),
            Point2D(x=400.0, y=300.0),
        ]

        engine = OvershootEngine()
        extended = engine.apply_overshoot(trajectory, target)

        # Extended trajectory should have more points
        assert len(extended) >= len(trajectory)

    def test_overshoot_ends_near_target(self) -> None:
        from bol.modules.m2_kinematic.overshoot import OvershootEngine

        target = Point2D(x=400.0, y=300.0)
        trajectory = [
            Point2D(x=100.0, y=100.0),
            Point2D(x=250.0, y=200.0),
            Point2D(x=400.0, y=300.0),
        ]

        engine = OvershootEngine()
        extended = engine.apply_overshoot(trajectory, target)

        # Final point should be close to target
        final = extended[-1]
        assert abs(final.x - target.x) < 5.0
        assert abs(final.y - target.y) < 5.0

    def test_should_overshoot_probability(self) -> None:
        from bol.modules.m2_kinematic.overshoot import OvershootEngine

        engine = OvershootEngine()
        # Run many trials — short distances should overshoot less often
        short_count = sum(1 for _ in range(200) if engine.should_overshoot(50.0))
        long_count = sum(1 for _ in range(200) if engine.should_overshoot(600.0))

        # Long distances should overshoot more often on average
        # Allow for randomness but expect a trend
        assert long_count > short_count * 0.5, "Long distances should overshoot more"
