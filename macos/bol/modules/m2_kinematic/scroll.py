"""
Sinusoidal scroll physics engine.

Generates scroll profiles with ease-in/ease-out velocity curves
and injected micro-stutter pauses simulating human reading.
"""

from __future__ import annotations

import math
import secrets

from bol.schemas.kinematic import MicroStutter, ScrollDirection, ScrollProfile


class ScrollEngine:
    """
    Generates scroll operation profiles with sinusoidal physics
    and micro-stutter reading pauses.
    """

    def generate_scroll_profile(
        self, distance_px: int, direction: ScrollDirection
    ) -> ScrollProfile:
        """
        Generate a complete scroll profile with velocity curve and stutters.

        Parameters
        ----------
        distance_px : int
            Total scroll distance in pixels.
        direction : ScrollDirection
            Scroll direction (UP or DOWN).

        Returns
        -------
        ScrollProfile
            Complete scroll plan with per-step delays and micro-stutters.
        """
        # Steps proportional to distance: 1 step per 15-25 pixels
        step_size = 15 + secrets.randbelow(11)  # 15 to 25
        num_steps = max(distance_px // step_size, 3)

        # Base delay per step
        base_delay_ms = 30.0 + secrets.randbelow(21)  # 30 to 50ms base

        # Generate sinusoidal step delays
        step_delays = self._calculate_step_delays(num_steps, base_delay_ms)

        # Inject micro-stutters (15-25% probability per step)
        stutter_prob = 0.15 + secrets.randbelow(11) / 100.0  # 0.15 to 0.25
        micro_stutters: list[MicroStutter] = []
        for i in range(num_steps):
            if secrets.randbelow(1000) / 1000.0 < stutter_prob:
                pause_ms = 50.0 + secrets.randbelow(251)  # 50 to 300ms
                micro_stutters.append(
                    MicroStutter(step_index=i, pause_ms=float(pause_ms))
                )

        total_delays = sum(step_delays)
        total_stutters = sum(s.pause_ms for s in micro_stutters)
        total_duration = total_delays + total_stutters

        return ScrollProfile(
            direction=direction,
            total_distance_px=distance_px,
            num_steps=num_steps,
            step_delays_ms=step_delays,
            micro_stutters=micro_stutters,
            total_duration_ms=total_duration,
        )

    def _calculate_step_delays(
        self, num_steps: int, base_delay_ms: float
    ) -> list[float]:
        """
        Calculate per-step delays following a sinusoidal ease-in/ease-out profile.

        Velocity: v(t) = V_max * sin²(πt/T)
        Delay is inversely proportional to velocity.

        Parameters
        ----------
        num_steps : int
            Number of scroll steps.
        base_delay_ms : float
            Base delay at peak velocity.

        Returns
        -------
        list[float]
            Per-step delays in milliseconds.
        """
        delays: list[float] = []
        for i in range(num_steps):
            # Normalized position: 0 to 1
            t = (i + 0.5) / num_steps

            # Sinusoidal velocity: sin²(πt)
            velocity = math.sin(math.pi * t) ** 2

            # Clamp velocity to avoid division by near-zero
            velocity = max(velocity, 0.1)

            # Delay inversely proportional to velocity
            # At peak velocity (sin²=1): delay = base_delay
            # At edges (sin²≈0.1): delay = base_delay * 10
            delay = base_delay_ms / velocity

            # Add small jitter (±10%)
            jitter = 1.0 + (secrets.randbelow(21) - 10) / 100.0
            delay *= jitter

            delays.append(round(delay, 2))

        return delays
