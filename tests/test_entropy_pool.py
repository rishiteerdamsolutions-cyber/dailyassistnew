"""
Tests for the Entropy Pool sampling-without-replacement engine.

Validates:
- Pool creation and basic properties
- Drawing without replacement
- Cycle exhaustion and auto-reset
- State serialization/deserialization
- No duplicate draws within a cycle
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bol.entropy.pool import EntropyPool


class TestEntropyPoolCreation:
    """Test pool initialization and basic properties."""

    def test_pool_creation_with_values(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2, 3, 4, 5])
        assert pool.size == 5
        assert pool.remaining == 5
        assert pool.consumed == 0
        assert pool.cycle_id == 0

    def test_pool_creation_empty_raises(self) -> None:
        try:
            EntropyPool(pool_id="test", values=[])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_pool_id(self) -> None:
        pool = EntropyPool(pool_id="my_pool", values=[10, 20, 30])
        assert pool.pool_id == "my_pool"


class TestEntropyPoolDraw:
    """Test drawing values from the pool."""

    def test_draw_reduces_remaining(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2, 3])
        pool.draw()
        assert pool.remaining == 2
        assert pool.consumed == 1

    def test_draw_returns_valid_value(self) -> None:
        values = [10, 20, 30, 40, 50]
        pool = EntropyPool(pool_id="test", values=values)
        drawn = pool.draw()
        assert drawn in values

    def test_no_duplicates_in_cycle(self) -> None:
        values = list(range(100))
        pool = EntropyPool(pool_id="test", values=values)
        drawn = [pool.draw() for _ in range(100)]
        assert len(set(drawn)) == 100, "All drawn values must be unique within a cycle"

    def test_draw_n(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2, 3, 4, 5])
        drawn = pool.draw_n(3)
        assert len(drawn) == 3
        assert len(set(drawn)) == 3
        assert pool.remaining == 2

    def test_exhaustion_flag(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2])
        assert not pool.is_exhausted
        pool.draw()
        pool.draw()
        assert pool.is_exhausted


class TestEntropyPoolCycles:
    """Test cycle exhaustion and reset behavior."""

    def test_auto_reset_on_exhaustion(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2, 3])
        # Exhaust the pool
        pool.draw()
        pool.draw()
        pool.draw()
        assert pool.is_exhausted
        # Drawing again should auto-reset
        value = pool.draw()
        assert value in [1, 2, 3]
        assert pool.cycle_id == 1
        assert pool.remaining == 2

    def test_cycle_id_increments(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1])
        pool.draw()  # Exhaust cycle 0
        pool.draw()  # Triggers cycle 1, draws from it
        assert pool.cycle_id == 1

    def test_manual_reset(self) -> None:
        pool = EntropyPool(pool_id="test", values=[1, 2, 3])
        pool.draw()
        pool.draw()
        pool.reset()
        assert pool.remaining == 3
        assert pool.consumed == 0
        assert pool.cycle_id == 0


class TestEntropyPoolSerialization:
    """Test state persistence."""

    def test_to_state_dict_and_back(self) -> None:
        pool = EntropyPool(pool_id="persist_test", values=[10, 20, 30, 40, 50])
        pool.draw()
        pool.draw()

        state = pool.to_state_dict()
        restored = EntropyPool.from_state_dict(state)

        assert restored.pool_id == pool.pool_id
        assert restored.size == pool.size
        assert restored.remaining == pool.remaining
        assert restored.consumed == pool.consumed
        assert restored.cycle_id == pool.cycle_id

    def test_save_and_load_file(self) -> None:
        pool = EntropyPool(pool_id="file_test", values=[100, 200, 300])
        pool.draw()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            pool.save_to_file(path)
            loaded = EntropyPool.load_from_file(path)
            assert loaded.pool_id == pool.pool_id
            assert loaded.remaining == pool.remaining
            assert loaded.cycle_id == pool.cycle_id
        finally:
            path.unlink(missing_ok=True)

    def test_peek_remaining(self) -> None:
        pool = EntropyPool(pool_id="peek", values=[1, 2, 3, 4, 5])
        pool.draw()
        remaining = pool.peek_remaining()
        assert len(remaining) == 4
        # Peeking should not consume
        assert pool.remaining == 4


class TestEntropyPoolRepr:
    """Test string representation."""

    def test_repr(self) -> None:
        pool = EntropyPool(pool_id="repr_test", values=[1, 2, 3])
        repr_str = repr(pool)
        assert "repr_test" in repr_str
        assert "size=3" in repr_str
        assert "remaining=3" in repr_str
