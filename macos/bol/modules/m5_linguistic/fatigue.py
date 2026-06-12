"""
Progressive fatigue model.

Simulates human typing fatigue: WPM decreases and typo rate
increases as more characters are typed.
"""

from __future__ import annotations

import secrets

from bol.schemas.linguistic import FatigueProfile
from bol.schemas.policy import PersonalityVector


class FatigueEngine:
    """
    Manages progressive typing fatigue based on personality parameters.

    Creates fatigue profiles and calculates per-character delays
    with entropy jitter, word-boundary pauses, and punctuation pauses.
    """

    _PUNCTUATION = set(".,;:!?\"'()-—")

    def __init__(self, personality: PersonalityVector) -> None:
        self._personality = personality

    def create_profile(self) -> FatigueProfile:
        """
        Create a new fatigue profile from personality parameters.

        Returns
        -------
        FatigueProfile
            Fresh fatigue state with personality-derived base values.
        """
        # Base WPM drawn from personality range
        wpm_range = self._personality.base_wpm_max - self._personality.base_wpm_min
        base_wpm = float(self._personality.base_wpm_min + secrets.randbelow(max(wpm_range + 1, 1)))

        # Decay rate: personality.fatigue_rate ± 0.02, clamped to [0.05, 0.12]
        decay_jitter = (secrets.randbelow(41) - 20) / 1000.0  # ±0.02
        decay_rate = max(0.05, min(0.12, self._personality.fatigue_rate + decay_jitter))

        # Base typo rate scaled by personality modifier
        base_typo_rate = 0.015 * self._personality.typo_rate_modifier

        return FatigueProfile(
            base_wpm=base_wpm,
            decay_rate=decay_rate,
            base_typo_rate=base_typo_rate,
            typo_growth_rate=0.005,
            characters_typed=0,
        )

    def calculate_delay_ms(self, profile: FatigueProfile, char: str) -> float:
        """
        Calculate the inter-key delay for a specific character.

        Applies entropy jitter and character-type multipliers.

        Parameters
        ----------
        profile : FatigueProfile
            Current fatigue state.
        char : str
            The character about to be typed.

        Returns
        -------
        float
            Delay in milliseconds before this keystroke.
        """
        base = profile.current_char_delay_ms

        # Entropy jitter: ±20%
        jitter = 1.0 + (secrets.randbelow(41) - 20) / 100.0  # 0.80 to 1.20
        delay = base * jitter

        # Character-type multipliers
        if char == " ":
            # Word boundary: 1.5-2.5x longer pause
            multiplier = 1.5 + secrets.randbelow(11) / 10.0  # 1.5 to 2.5
            delay *= multiplier
        elif char in self._PUNCTUATION:
            # Punctuation: 1.2-1.8x longer pause
            multiplier = 1.2 + secrets.randbelow(7) / 10.0  # 1.2 to 1.8
            delay *= multiplier
        elif char == "\n":
            # Newline: significant pause
            delay *= 2.0 + secrets.randbelow(11) / 10.0  # 2.0 to 3.0

        return max(delay, 10.0)  # Minimum 10ms

    def update_profile(self, profile: FatigueProfile, chars_typed: int) -> FatigueProfile:
        """
        Return a new FatigueProfile with updated character count.

        Parameters
        ----------
        profile : FatigueProfile
            Current profile.
        chars_typed : int
            New total characters typed.

        Returns
        -------
        FatigueProfile
            Updated profile with new character count.
        """
        return FatigueProfile(
            base_wpm=profile.base_wpm,
            decay_rate=profile.decay_rate,
            base_typo_rate=profile.base_typo_rate,
            typo_growth_rate=profile.typo_growth_rate,
            characters_typed=chars_typed,
        )
