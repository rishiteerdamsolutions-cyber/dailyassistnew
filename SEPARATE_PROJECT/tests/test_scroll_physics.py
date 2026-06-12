"""
Tests for the Sinusoidal Scroll Physics engine (Module 2).

Validates:
- Scroll profile generation
- Sinusoidal velocity profile (ease-in/ease-out)
- Micro-stutter injection
- Duration calculations
"""

from __future__ import annotations

from bol.schemas.kinematic import ScrollDirection


class TestScrollProfileGeneration:
    """Test scroll profile creation."""

    def test_generates_valid_profile(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        profile = engine.generate_scroll_profile(500, ScrollDirection.DOWN)

        assert profile.direction == ScrollDirection.DOWN
        assert profile.total_distance_px == 500
        assert profile.num_steps > 0
        assert len(profile.step_delays_ms) == profile.num_steps
        assert profile.total_duration_ms > 0

    def test_step_count_proportional_to_distance(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        short = engine.generate_scroll_profile(100, ScrollDirection.DOWN)
        long = engine.generate_scroll_profile(1000, ScrollDirection.DOWN)

        assert long.num_steps > short.num_steps

    def test_scroll_direction_preserved(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        up_profile = engine.generate_scroll_profile(300, ScrollDirection.UP)
        down_profile = engine.generate_scroll_profile(300, ScrollDirection.DOWN)

        assert up_profile.direction == ScrollDirection.UP
        assert down_profile.direction == ScrollDirection.DOWN


class TestSinusoidalVelocity:
    """Test the ease-in/ease-out velocity profile."""

    def test_delays_follow_sinusoidal_pattern(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        profile = engine.generate_scroll_profile(800, ScrollDirection.DOWN)

        delays = profile.step_delays_ms
        if len(delays) > 6:
            # Start delays should be longer (slow start)
            start_avg = sum(delays[:3]) / 3
            # Middle delays should be shorter (peak speed)
            mid_idx = len(delays) // 2
            mid_avg = sum(delays[mid_idx - 1 : mid_idx + 2]) / 3
            # End delays should be longer again (slow end)
            end_avg = sum(delays[-3:]) / 3

            assert mid_avg < start_avg, "Middle should be faster than start"
            assert mid_avg < end_avg, "Middle should be faster than end"


class TestMicroStutters:
    """Test micro-stutter injection during scrolling."""

    def test_stutters_present_in_long_scrolls(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        # Generate many profiles and check that at least some have stutters
        stutter_found = False
        for _ in range(20):
            profile = engine.generate_scroll_profile(1000, ScrollDirection.DOWN)
            if len(profile.micro_stutters) > 0:
                stutter_found = True
                break
        assert stutter_found, "At least some long scrolls should have micro-stutters"

    def test_stutter_durations_in_range(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        for _ in range(50):
            profile = engine.generate_scroll_profile(800, ScrollDirection.DOWN)
            for stutter in profile.micro_stutters:
                assert 50.0 <= stutter.pause_ms <= 300.0, (
                    f"Stutter duration {stutter.pause_ms}ms out of range"
                )

    def test_stutter_indices_valid(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        for _ in range(30):
            profile = engine.generate_scroll_profile(600, ScrollDirection.DOWN)
            for stutter in profile.micro_stutters:
                assert 0 <= stutter.step_index < profile.num_steps


class TestScrollDuration:
    """Test total duration calculation."""

    def test_total_includes_stutters(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        profile = engine.generate_scroll_profile(500, ScrollDirection.DOWN)

        sum_delays = sum(profile.step_delays_ms)
        sum_stutters = sum(s.pause_ms for s in profile.micro_stutters)
        expected_total = sum_delays + sum_stutters

        # Allow small floating point tolerance
        assert abs(profile.total_duration_ms - expected_total) < 1.0

    def test_all_delays_positive(self) -> None:
        from bol.modules.m2_kinematic.scroll import ScrollEngine

        engine = ScrollEngine()
        profile = engine.generate_scroll_profile(400, ScrollDirection.DOWN)

        for delay in profile.step_delays_ms:
            assert delay > 0, "All step delays must be positive"
