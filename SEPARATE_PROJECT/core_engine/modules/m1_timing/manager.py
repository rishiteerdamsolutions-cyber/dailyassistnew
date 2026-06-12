"""
Timing Manager — Public API for the Chrono-Entropy system.

Provides the interface for workflows to draw authentic delays
from platform-specific depletion pools.
"""

from __future__ import annotations

from pathlib import Path

from bol.modules.m1_timing.db import TimingDatabase
from bol.modules.m1_timing.pool import TimingPoolGenerator
from bol.schemas.timing import TimingAction, TimingConfig, TimingPoolStatus
from bol.utils.logging import get_logger

logger = get_logger(__name__)

# Default platform configurations
_DEFAULT_CONFIGS: dict[str, TimingConfig] = {
    "linkedin": TimingConfig(
        platform="linkedin",
        pool_size=1000,
        min_latency_ms=200.0,
        max_latency_ms=4500.0,
        distribution_alpha=2.0,
        distribution_beta=5.0,
    ),
    "x.com": TimingConfig(
        platform="x.com",
        pool_size=1000,
        min_latency_ms=150.0,
        max_latency_ms=3500.0,
        distribution_alpha=2.5,
        distribution_beta=5.5,
    ),
}


class TimingManager:
    """
    Public API for the Chrono-Entropy & Timing Manager.

    Manages platform-specific timing pools and provides delay values
    for workflow actions. Automatically initializes pools on first use
    and handles cycle exhaustion/reset.
    """

    def __init__(
        self,
        db_path: Path,
        configs: dict[str, TimingConfig] | None = None,
    ) -> None:
        """
        Initialize the timing manager.

        Parameters
        ----------
        db_path : Path
            Path to the SQLite database file.
        configs : dict[str, TimingConfig] | None
            Platform-specific configurations. If None, uses defaults.
        """
        self._db = TimingDatabase(db_path)
        self._configs = configs if configs is not None else dict(_DEFAULT_CONFIGS)

    def get_delay(
        self,
        platform: str,
        action: TimingAction | None = None,
    ) -> float:
        """
        Draw the next timing delay for a platform action.

        Returns the delay in **seconds** (millisecond pool value / 1000).
        If the pool is exhausted, automatically resets to a new cycle.

        Parameters
        ----------
        platform : str
            Target platform identifier.
        action : TimingAction | None
            Optional action category (reserved for future per-action tuning).

        Returns
        -------
        float
            Delay in seconds.
        """
        self._ensure_pool_initialized(platform)

        # Check if pool is exhausted and needs cycle reset
        available = self._db.get_available_count(platform)
        if available == 0:
            current_cycle = self._db.get_current_cycle(platform)
            new_cycle = current_cycle + 1
            self._db.reset_cycle(platform, new_cycle)
            logger.info(
                "Pool exhausted for '%s'. Reset to cycle %d.", platform, new_cycle
            )

        value_ms = self._db.draw_value(platform)
        delay_s = value_ms / 1000.0
        logger.debug(
            "Drew delay %.3fs (%.2fms) for '%s' action=%s",
            delay_s, value_ms, platform, action,
        )
        return delay_s

    def get_pool_status(self, platform: str) -> TimingPoolStatus:
        """Get the current status of a platform's timing pool."""
        self._ensure_pool_initialized(platform)

        consumed = self._db.get_consumed_count(platform)
        available = self._db.get_available_count(platform)
        total = consumed + available
        cycle = self._db.get_current_cycle(platform)

        return TimingPoolStatus(
            platform=platform,
            pool_size=total,
            consumed_count=consumed,
            remaining_count=available,
            cycle_id=cycle,
            exhaustion_percentage=round((consumed / total) * 100, 2) if total > 0 else 0.0,
        )

    def apply_personality_modifier(self, base_delay: float, modifier: float) -> float:
        """
        Apply a personality timing modifier to a base delay.

        Parameters
        ----------
        base_delay : float
            Original delay in seconds.
        modifier : float
            Personality timing multiplier (>1 = slower, <1 = faster).

        Returns
        -------
        float
            Modified delay in seconds.
        """
        return base_delay * modifier

    def _ensure_pool_initialized(self, platform: str) -> None:
        """Create and populate the pool if it doesn't exist yet."""
        if self._db.pool_exists(platform):
            return

        if platform not in self._configs:
            # Create a default config for unknown platforms
            self._configs[platform] = TimingConfig(platform=platform)

        config = self._configs[platform]
        values = TimingPoolGenerator.generate_pool(config)
        self._db.initialize_pool(platform, values, cycle_id=0)

    def close(self) -> None:
        """Close the database connection."""
        self._db.close()
