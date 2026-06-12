"""
Tests for the QWERTY Typo Engine (Module 5).

Validates:
- QWERTY adjacency map completeness
- Proximity typo generation
- Case preservation
- Fatigue profile progression
- Keystroke sequence generation
"""

from __future__ import annotations

from bol.schemas.linguistic import FatigueProfile
from bol.schemas.policy import PersonalityVector


class TestQWERTYAdjacency:
    """Test the QWERTY keyboard adjacency map."""

    def test_common_keys_have_neighbors(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        # All common letters should have adjacency entries
        for char in "qwertyuiopasdfghjklzxcvbnm":
            assert char in engine.QWERTY_ADJACENCY, f"Missing adjacency for '{char}'"
            assert len(engine.QWERTY_ADJACENCY[char]) > 0, f"Empty adjacency for '{char}'"

    def test_adjacency_is_reciprocal(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        # If 'a' is adjacent to 's', then 's' should be adjacent to 'a'
        for char, neighbors in engine.QWERTY_ADJACENCY.items():
            for neighbor in neighbors:
                if neighbor in engine.QWERTY_ADJACENCY:
                    assert char in engine.QWERTY_ADJACENCY[neighbor], (
                        f"'{char}' is adjacent to '{neighbor}' but not vice versa"
                    )


class TestTypoGeneration:
    """Test proximity typo generation."""

    def test_typo_is_adjacent(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        for _ in range(50):
            typo = engine.get_proximity_typo("f")
            assert typo in engine.QWERTY_ADJACENCY.get("f", ["f"]), (
                f"Typo '{typo}' is not adjacent to 'f'"
            )

    def test_case_preservation(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        for _ in range(30):
            typo = engine.get_proximity_typo("F")
            assert typo.isupper(), f"Uppercase input should produce uppercase typo, got '{typo}'"

    def test_unknown_char_returns_self(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        assert engine.get_proximity_typo("€") == "€"
        assert engine.get_proximity_typo("™") == "™"

    def test_typo_differs_from_original(self) -> None:
        from bol.modules.m5_linguistic.typo import TypoEngine

        engine = TypoEngine()
        # Most typos should differ from the original
        different_count = 0
        for _ in range(100):
            original = "h"
            typo = engine.get_proximity_typo(original)
            if typo != original:
                different_count += 1
        assert different_count > 80, "Most typos should differ from original"


class TestFatigueProfile:
    """Test progressive fatigue model."""

    def test_wpm_degrades_over_time(self) -> None:
        profile_start = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.08,
            characters_typed=0,
        )
        profile_end = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.08,
            characters_typed=500,
        )

        assert profile_end.current_wpm < profile_start.current_wpm

    def test_typo_rate_increases(self) -> None:
        profile_start = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.08,
            base_typo_rate=0.015,
            typo_growth_rate=0.005,
            characters_typed=0,
        )
        profile_end = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.08,
            base_typo_rate=0.015,
            typo_growth_rate=0.005,
            characters_typed=500,
        )

        assert profile_end.current_typo_rate > profile_start.current_typo_rate

    def test_wpm_has_floor(self) -> None:
        profile = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.12,
            characters_typed=10000,  # Very long text
        )
        assert profile.current_wpm >= 15.0, "WPM should have a floor"

    def test_typo_rate_has_ceiling(self) -> None:
        profile = FatigueProfile(
            base_wpm=60.0,
            decay_rate=0.08,
            base_typo_rate=0.015,
            typo_growth_rate=0.005,
            characters_typed=10000,
        )
        assert profile.current_typo_rate <= 0.08, "Typo rate should be capped"

    def test_char_delay_increases_with_fatigue(self) -> None:
        profile_fresh = FatigueProfile(base_wpm=60.0, decay_rate=0.08, characters_typed=0)
        profile_tired = FatigueProfile(base_wpm=60.0, decay_rate=0.08, characters_typed=500)

        assert profile_tired.current_char_delay_ms > profile_fresh.current_char_delay_ms


class TestFatigueEngine:
    """Test the FatigueEngine class."""

    def test_create_profile_from_personality(self) -> None:
        from bol.modules.m5_linguistic.fatigue import FatigueEngine

        personality = PersonalityVector(
            name="Test",
            description="Test personality",
            base_wpm_min=45,
            base_wpm_max=75,
            fatigue_rate=0.08,
            typo_rate_modifier=1.0,
        )
        engine = FatigueEngine(personality)
        profile = engine.create_profile()

        assert 45 <= profile.base_wpm <= 75
        assert 0.05 <= profile.decay_rate <= 0.12
        assert profile.characters_typed == 0

    def test_space_gets_longer_delay(self) -> None:
        from bol.modules.m5_linguistic.fatigue import FatigueEngine

        personality = PersonalityVector(
            name="Test",
            description="Test",
            base_wpm_min=60,
            base_wpm_max=60,
            fatigue_rate=0.08,
            typo_rate_modifier=1.0,
        )
        engine = FatigueEngine(personality)
        profile = FatigueProfile(base_wpm=60.0, decay_rate=0.08, characters_typed=0)

        # Average multiple samples to reduce noise
        letter_delays = [engine.calculate_delay_ms(profile, "a") for _ in range(50)]
        space_delays = [engine.calculate_delay_ms(profile, " ") for _ in range(50)]

        avg_letter = sum(letter_delays) / len(letter_delays)
        avg_space = sum(space_delays) / len(space_delays)

        assert avg_space > avg_letter, "Space should have longer delay than letters"
