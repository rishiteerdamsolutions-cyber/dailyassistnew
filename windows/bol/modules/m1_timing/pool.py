"""
Timing pool value generator.

Generates pools of authentic-looking latency values using
a beta distribution shaped to match human reaction time patterns.
"""

from __future__ import annotations

import secrets

import numpy as np

from bol.schemas.timing import TimingConfig
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class TimingPoolGenerator:
    """Generates pools of unique, authentic-looking latency values."""

    @staticmethod
    def generate_pool(config: TimingConfig) -> list[float]:
        """
        Generate exactly ``config.pool_size`` unique continuous decimal
        millisecond values within the configured bounds.

        Values are shaped using a beta distribution to cluster around
        natural human reaction-time patterns while ensuring no round numbers.

        Parameters
        ----------
        config : TimingConfig
            Pool configuration with bounds and distribution parameters.

        Returns
        -------
        list[float]
            Sorted list of unique latency values in milliseconds.
        """
        # Seed a local RNG from cryptographic entropy — never the global state
        seed_bytes = secrets.token_bytes(32)
        seed_int = int.from_bytes(seed_bytes, "big") % (2**63)
        rng = np.random.Generator(np.random.PCG64(seed_int))

        pool_set: set[float] = set()
        range_span = config.max_latency_ms - config.min_latency_ms

        # Generate values in batches until we have enough unique ones
        batch_multiplier = 2
        while len(pool_set) < config.pool_size:
            needed = config.pool_size - len(pool_set)
            batch_size = needed * batch_multiplier

            # Beta distribution shapes the curve — alpha<beta skews left (faster reactions)
            raw = rng.beta(config.distribution_alpha, config.distribution_beta, size=batch_size)

            # Scale to target range
            scaled = config.min_latency_ms + raw * range_span

            # Add micro-jitter to ensure no round numbers
            jitter = rng.uniform(-0.49, 0.49, size=batch_size)
            values = scaled + jitter

            # Round to 2 decimal places and ensure uniqueness
            for v in values:
                rounded = round(float(v), 2)
                # Ensure it has exactly 2 decimal places (does not end in .0 or .x0)
                while round(rounded, 1) == rounded:
                    # Add sub-cent/cent jitter
                    jitter_val = rng.uniform(0.01, 0.99)
                    rounded = round(float(rounded + jitter_val), 2)
                # Ensure within bounds
                if config.min_latency_ms <= rounded <= config.max_latency_ms:
                    pool_set.add(rounded)
                if len(pool_set) >= config.pool_size:
                    break

            batch_multiplier += 1  # Increase batch size if uniqueness is hard

        result = sorted(list(pool_set))[: config.pool_size]
        logger.info(
            "Generated timing pool for '%s': %d values in [%.1f, %.1f]ms",
            config.platform, len(result), min(result), max(result),
        )
        return result
