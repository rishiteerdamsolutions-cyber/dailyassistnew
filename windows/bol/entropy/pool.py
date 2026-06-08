"""
Entropy Pool — Generic sampling-without-replacement engine.

Provides a cryptographically seeded, state-persistent pool that
guarantees each value is consumed exactly once before any cycle reset.
Uses the ``secrets`` module exclusively — never ``random``.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class EntropyPool(Generic[T]):
    """
    A generic sampling-without-replacement engine.

    Maintains a pool of values where each value can only be drawn once
    per cycle. When all values are exhausted, a new cycle begins.
    State is serializable to JSON for cross-session persistence.

    Parameters
    ----------
    pool_id : str
        Unique identifier for this pool.
    values : list[T]
        The complete set of values in the pool.
    """

    def __init__(self, pool_id: str, values: list[T]) -> None:
        if not values:
            raise ValueError("EntropyPool requires at least one value.")
        self._pool_id = pool_id
        self._all_values: list[T] = list(values)
        self._available_indices: list[int] = list(range(len(values)))
        self._consumed_indices: list[int] = []
        self._cycle_id: int = 0
        self._draw_log: list[dict] = []

    @property
    def pool_id(self) -> str:
        """Unique identifier for this pool."""
        return self._pool_id

    @property
    def size(self) -> int:
        """Total number of values in the pool."""
        return len(self._all_values)

    @property
    def remaining(self) -> int:
        """Number of unconsumed values in the current cycle."""
        return len(self._available_indices)

    @property
    def consumed(self) -> int:
        """Number of consumed values in the current cycle."""
        return len(self._consumed_indices)

    @property
    def cycle_id(self) -> int:
        """Current depletion cycle number."""
        return self._cycle_id

    @property
    def is_exhausted(self) -> bool:
        """True if all values have been consumed in the current cycle."""
        return len(self._available_indices) == 0

    def draw(self) -> T:
        """
        Draw a single value from the pool without replacement.

        If the pool is exhausted, automatically starts a new cycle
        and reshuffles all values back into the available set.

        Returns
        -------
        T
            A value from the pool that has not been drawn this cycle.
        """
        if self.is_exhausted:
            self._start_new_cycle()

        # Use secrets for cryptographic-quality random selection
        idx_position = secrets.randbelow(len(self._available_indices))
        selected_index = self._available_indices.pop(idx_position)
        self._consumed_indices.append(selected_index)

        value = self._all_values[selected_index]
        self._draw_log.append({
            "cycle": self._cycle_id,
            "index": selected_index,
            "timestamp": datetime.now().isoformat(),
        })
        return value

    def draw_n(self, n: int) -> list[T]:
        """
        Draw ``n`` values from the pool without replacement.

        May span cycle boundaries if the pool is nearly exhausted.

        Parameters
        ----------
        n : int
            Number of values to draw.

        Returns
        -------
        list[T]
            List of drawn values.
        """
        if n < 1:
            raise ValueError("n must be at least 1.")
        return [self.draw() for _ in range(n)]

    def peek_remaining(self) -> list[T]:
        """Return all remaining (unconsumed) values without consuming them."""
        return [self._all_values[i] for i in self._available_indices]

    def _start_new_cycle(self) -> None:
        """Reset all values to available and increment the cycle counter."""
        self._cycle_id += 1
        self._available_indices = list(range(len(self._all_values)))
        self._consumed_indices = []

    def reset(self) -> None:
        """Force-reset the pool to cycle 0 with all values available."""
        self._cycle_id = 0
        self._available_indices = list(range(len(self._all_values)))
        self._consumed_indices = []
        self._draw_log = []

    # ── Serialization ────────────────────────────────────────────────

    def to_state_dict(self) -> dict:
        """Serialize pool state to a dictionary for persistence."""
        return {
            "pool_id": self._pool_id,
            "all_values": self._all_values,
            "available_indices": self._available_indices,
            "consumed_indices": self._consumed_indices,
            "cycle_id": self._cycle_id,
        }

    @classmethod
    def from_state_dict(cls, state: dict) -> EntropyPool:
        """Restore pool state from a serialized dictionary."""
        pool = cls(pool_id=state["pool_id"], values=state["all_values"])
        pool._available_indices = list(state["available_indices"])
        pool._consumed_indices = list(state["consumed_indices"])
        pool._cycle_id = state["cycle_id"]
        return pool

    def save_to_file(self, path: Path) -> None:
        """Persist pool state to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_state_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: Path) -> EntropyPool:
        """Load pool state from a JSON file."""
        with open(path) as f:
            state = json.load(f)
        return cls.from_state_dict(state)

    def __repr__(self) -> str:
        return (
            f"EntropyPool(id={self._pool_id!r}, "
            f"size={self.size}, "
            f"remaining={self.remaining}, "
            f"cycle={self._cycle_id})"
        )
