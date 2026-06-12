"""
Linguistic Engine — Public API for Module 5.

Orchestrates typo injection, fatigue progression, and text variance
validation into a unified text processing pipeline.
"""

from __future__ import annotations

from pathlib import Path

from bol.modules.m5_linguistic.fatigue import FatigueEngine
from bol.modules.m5_linguistic.typo import TypoEngine
from bol.modules.m5_linguistic.variance import VarianceEngine
from bol.schemas.linguistic import (
    KeystrokeEvent,
    KeystrokeSequence,
    TextPayload,
)
from bol.schemas.policy import PersonalityVector
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class LinguisticEngine:
    """
    Unified text processing pipeline composing typo injection,
    fatigue modeling, and burstiness validation.
    """

    def __init__(
        self,
        personality: PersonalityVector,
        history_db_path: Path | None = None,
    ) -> None:
        self._typo = TypoEngine()
        self._fatigue = FatigueEngine(personality)
        self._variance = VarianceEngine(history_db_path)
        self._personality = personality

    def prepare_payload(self, text: str) -> TextPayload:
        """
        Prepare a text payload for keyboard entry.

        Validates against variance history and computes metrics.
        """
        # Validate but don't reject — log a warning
        if not self._variance.validate_text(text):
            logger.warning("Text failed burstiness validation — proceeding anyway")

        words = text.split()
        sentences = [s for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

        return TextPayload(
            raw_text=text,
            processed_text=text,
            character_count=len(text),
            word_count=len(words),
            sentence_count=len(sentences),
        )

    def generate_keystroke_sequence(self, payload: TextPayload) -> KeystrokeSequence:
        """
        Generate a complete keystroke sequence with typos, corrections, and fatigue.

        For each character:
        1. Calculate delay based on fatigue
        2. Check if a typo should be injected
        3. If typo: type wrong char → pause → backspace → correct char
        4. Track fatigue progression

        Returns
        -------
        KeystrokeSequence
            Complete sequence ready for execution by Module 6.
        """
        profile = self._fatigue.create_profile()
        events: list[KeystrokeEvent] = []
        typo_count = 0
        correction_count = 0
        chars_typed = 0
        wpm_start = profile.current_wpm

        for i, char in enumerate(payload.processed_text):
            delay = self._fatigue.calculate_delay_ms(profile, char)

            # Check for typo injection
            if char.isalpha() and self._typo.should_inject_typo(profile.current_typo_rate):
                typo_spec = self._typo.generate_typo_spec(i, char, profile)

                # 1. Type the wrong character
                events.append(KeystrokeEvent(
                    character=typo_spec.replacement_char,
                    delay_before_ms=delay,
                    is_typo=True,
                    typo_spec=typo_spec,
                ))
                chars_typed += 1

                # 2. Pause (realization delay)
                # 3. Backspace correction
                events.append(KeystrokeEvent(
                    character="\b",
                    delay_before_ms=typo_spec.realization_delay_ms,
                    is_correction=True,
                ))
                correction_count += 1

                # 4. Type the correct character
                events.append(KeystrokeEvent(
                    character=char,
                    delay_before_ms=self._fatigue.calculate_delay_ms(profile, char) * 0.8,
                ))
                typo_count += 1
                chars_typed += 1
            else:
                # Normal character
                events.append(KeystrokeEvent(
                    character=char,
                    delay_before_ms=delay,
                ))
                chars_typed += 1

            # Update fatigue
            profile = self._fatigue.update_profile(profile, chars_typed)

        total_duration = sum(e.delay_before_ms for e in events)
        wpm_end = profile.current_wpm

        logger.info(
            "Generated keystroke sequence: %d events, %d typos, %.0fms total, "
            "WPM %.1f→%.1f",
            len(events), typo_count, total_duration, wpm_start, wpm_end,
        )

        return KeystrokeSequence(
            events=events,
            total_duration_ms=total_duration,
            typo_count=typo_count,
            correction_count=correction_count,
            effective_wpm_start=wpm_start,
            effective_wpm_end=wpm_end,
        )

    def record_posted_text(self, text: str) -> None:
        """Record posted text to the variance history."""
        self._variance.record_text(text)
