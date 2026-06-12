"""
Linguistic schemas — Data contracts for Module 5 (Linguistic Variance & Typo Engine).

Defines text payloads, typo specifications, fatigue profiles,
and per-keystroke event streams.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextPayload(BaseModel):
    """A text payload prepared for keyboard entry."""

    raw_text: str = Field(description="Original API-generated text.")
    processed_text: str = Field(description="Text after variance processing.")
    character_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)


class TypoSpec(BaseModel):
    """Specification for a single injected typo."""

    model_config = {"frozen": True}

    position: int = Field(ge=0, description="Character index where the typo occurs.")
    original_char: str = Field(min_length=1, max_length=1, description="The correct character.")
    replacement_char: str = Field(min_length=1, max_length=1, description="The typo character (QWERTY-adjacent).")
    realization_delay_ms: float = Field(
        gt=0,
        description="Delay before the user 'realizes' the typo and begins correction.",
    )
    correction_backspaces: int = Field(
        default=1, ge=1,
        description="Number of backspace characters to issue for correction.",
    )


class FatigueProfile(BaseModel):
    """Progressive fatigue model parameters."""

    base_wpm: float = Field(gt=0, description="Starting words-per-minute.")
    decay_rate: float = Field(
        ge=0.05, le=0.12,
        description="WPM reduction per 100 characters typed (0.08 = 8%).",
    )
    base_typo_rate: float = Field(
        default=0.015, ge=0.0, le=0.1,
        description="Starting probability of a typo per character.",
    )
    typo_growth_rate: float = Field(
        default=0.005, ge=0.0,
        description="Typo probability increase per 100 characters.",
    )
    characters_typed: int = Field(default=0, ge=0, description="Running count of characters typed.")

    @property
    def current_wpm(self) -> float:
        """Current WPM after fatigue degradation."""
        degradation = 1.0 - (self.decay_rate * (self.characters_typed / 100.0))
        return max(self.base_wpm * max(degradation, 0.4), 15.0)  # Floor at 40% of base or 15 WPM

    @property
    def current_typo_rate(self) -> float:
        """Current typo probability after fatigue scaling."""
        return min(
            self.base_typo_rate + (self.typo_growth_rate * (self.characters_typed / 100.0)),
            0.08,  # Cap at 8%
        )

    @property
    def current_char_delay_ms(self) -> float:
        """Current inter-character delay in milliseconds based on WPM."""
        # Average word = 5 characters → chars/min = WPM * 5
        chars_per_minute = self.current_wpm * 5.0
        return (60.0 / chars_per_minute) * 1000.0  # Convert to ms


class KeystrokeEvent(BaseModel):
    """A single keystroke event in the character stream."""

    character: str = Field(min_length=1, max_length=1, description="Character to type.")
    delay_before_ms: float = Field(ge=0, description="Delay before this keystroke (ms).")
    is_typo: bool = Field(default=False, description="Whether this is a typo character.")
    is_correction: bool = Field(default=False, description="Whether this is a correction (backspace).")
    typo_spec: TypoSpec | None = Field(
        default=None,
        description="Details of the typo if is_typo is True.",
    )


class KeystrokeSequence(BaseModel):
    """Complete sequence of keystroke events for a text payload."""

    events: list[KeystrokeEvent] = Field(description="Ordered list of keystroke events.")
    total_duration_ms: float = Field(ge=0, description="Total typing duration.")
    typo_count: int = Field(ge=0, description="Number of typos injected.")
    correction_count: int = Field(ge=0, description="Number of corrections issued.")
    effective_wpm_start: float = Field(gt=0, description="WPM at the start of typing.")
    effective_wpm_end: float = Field(gt=0, description="WPM at the end of typing.")
