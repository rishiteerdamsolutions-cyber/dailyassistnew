"""
Tests for the Timing Pool depletion engine (Module 1).

Validates:
- Pool generation (1000 unique values)
- Value distribution (authentic-looking decimals)
- Extraction-without-replacement
- Cycle management
- SQLite persistence
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bol.schemas.timing import TimingConfig


class TestTimingPoolGeneration:
    """Test pool value generation."""

    def test_generates_correct_count(self) -> None:
        from bol.modules.m1_timing.pool import TimingPoolGenerator

        config = TimingConfig(
            platform="test",
            pool_size=100,
            min_latency_ms=200.0,
            max_latency_ms=4500.0,
        )
        values = TimingPoolGenerator.generate_pool(config)
        assert len(values) == 100

    def test_values_within_bounds(self) -> None:
        from bol.modules.m1_timing.pool import TimingPoolGenerator

        config = TimingConfig(
            platform="test",
            pool_size=100,
            min_latency_ms=300.0,
            max_latency_ms=3000.0,
        )
        values = TimingPoolGenerator.generate_pool(config)

        for v in values:
            assert 300.0 <= v <= 3000.0, f"Value {v} out of bounds"

    def test_values_are_unique(self) -> None:
        from bol.modules.m1_timing.pool import TimingPoolGenerator

        config = TimingConfig(platform="test", pool_size=1000)
        values = TimingPoolGenerator.generate_pool(config)
        assert len(set(values)) == 1000, "All 1000 values must be unique"

    def test_values_look_authentic(self) -> None:
        from bol.modules.m1_timing.pool import TimingPoolGenerator

        config = TimingConfig(platform="test", pool_size=100)
        values = TimingPoolGenerator.generate_pool(config)

        # Values should NOT be round numbers
        round_count = sum(1 for v in values if v == round(v))
        assert round_count == 0, "Values should have decimal precision"

        # Values should have at least 2 decimal places
        for v in values:
            decimal_str = f"{v:.10f}".rstrip("0").split(".")[1]
            assert len(decimal_str) >= 2, f"Value {v} lacks decimal precision"

    def test_default_pool_size_1000(self) -> None:
        from bol.modules.m1_timing.pool import TimingPoolGenerator

        config = TimingConfig(platform="linkedin")
        values = TimingPoolGenerator.generate_pool(config)
        assert len(values) == 1000


class TestTimingDatabase:
    """Test SQLite persistence layer."""

    def test_initialize_and_draw(self) -> None:
        from bol.modules.m1_timing.db import TimingDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            db = TimingDatabase(db_path)
            values = [100.5, 200.7, 300.3, 400.1, 500.9]
            db.initialize_pool("test", values, cycle_id=0)

            assert db.pool_exists("test")
            assert db.get_available_count("test") == 5
            assert db.get_consumed_count("test") == 0

            drawn = db.draw_value("test")
            assert drawn in values
            assert db.get_available_count("test") == 4
            assert db.get_consumed_count("test") == 1
        finally:
            db_path.unlink(missing_ok=True)

    def test_exhaustion_and_reset(self) -> None:
        from bol.modules.m1_timing.db import TimingDatabase

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            db = TimingDatabase(db_path)
            values = [10.0, 20.0, 30.0]
            db.initialize_pool("test", values, cycle_id=0)

            # Draw all values
            drawn = set()
            for _ in range(3):
                drawn.add(db.draw_value("test"))
            assert len(drawn) == 3
            assert db.get_available_count("test") == 0

            # Reset cycle
            db.reset_cycle("test", new_cycle_id=1)
            assert db.get_available_count("test") == 3
            assert db.get_current_cycle("test") == 1
        finally:
            db_path.unlink(missing_ok=True)


class TestTimingManager:
    """Test the public TimingManager API."""

    def test_get_delay_returns_seconds(self) -> None:
        from bol.modules.m1_timing.manager import TimingManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            config = TimingConfig(
                platform="test",
                pool_size=100,
                min_latency_ms=200.0,
                max_latency_ms=4500.0,
            )
            manager = TimingManager(db_path, configs={"test": config})
            delay = manager.get_delay("test")

            # Should be in seconds (200-4500ms → 0.2-4.5s)
            assert 0.1 <= delay <= 5.0, f"Delay {delay}s out of expected range"
        finally:
            db_path.unlink(missing_ok=True)

    def test_personality_modifier(self) -> None:
        from bol.modules.m1_timing.manager import TimingManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            manager = TimingManager(db_path)
            base = 1.0
            modified = manager.apply_personality_modifier(base, 1.5)
            assert modified == 1.5
        finally:
            db_path.unlink(missing_ok=True)

    def test_pool_status(self) -> None:
        from bol.modules.m1_timing.manager import TimingManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            config = TimingConfig(platform="status_test", pool_size=100)
            manager = TimingManager(db_path, configs={"status_test": config})
            manager.get_delay("status_test")  # Initialize and draw one
            status = manager.get_pool_status("status_test")
            assert status.platform == "status_test"
            assert status.pool_size == 100
            assert status.consumed_count == 1
            assert status.remaining_count == 99
        finally:
            db_path.unlink(missing_ok=True)
