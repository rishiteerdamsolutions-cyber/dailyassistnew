"""
Policy schemas — Data contracts for Module 4 (Behavioral Policy & State Engine).

Defines personality vectors, Markov chain states, interruption events,
and session state tracking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MarkovStateEnum(str, Enum):
    """High-level behavioral states in the session Markov chain."""

    IDLE = "idle"
    SCROLLING = "scrolling"
    READING = "reading"
    COMPOSING = "composing"
    DISTRACTED = "distracted"
    POSTING = "posting"
    COOLING_DOWN = "cooling_down"
    EXITING = "exiting"


class InterruptionType(str, Enum):
    """Types of behavioral interruptions."""

    NOTIFICATION_LOOP = "notification_loop"
    MID_COMPOSITION_FREEZE = "mid_composition_freeze"
    GHOST_DRAFT = "ghost_draft"


class PersonalityVector(BaseModel):
    """A behavioral personality profile that skews session parameters."""

    model_config = {"frozen": True}

    name: str = Field(description="Human-readable personality name.")
    description: str = Field(description="Brief description of this personality archetype.")
    timing_modifier: float = Field(
        default=1.0, gt=0.0, le=3.0,
        description="Multiplier applied to all timing delays (>1 = slower).",
    )
    scroll_depth_min: int = Field(default=300, ge=0, description="Minimum scroll depth in pixels.")
    scroll_depth_max: int = Field(default=1500, ge=0, description="Maximum scroll depth in pixels.")
    distraction_probability: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Probability of triggering a distraction event.",
    )
    typo_rate_modifier: float = Field(
        default=1.0, gt=0.0, le=3.0,
        description="Multiplier for base typo frequency (>1 = more typos).",
    )
    fatigue_rate: float = Field(
        default=0.08, ge=0.0, le=0.25,
        description="WPM degradation rate per 100 characters (0.08 = 8%).",
    )
    base_wpm_min: int = Field(default=45, ge=20, description="Minimum base words-per-minute.")
    base_wpm_max: int = Field(default=75, le=120, description="Maximum base words-per-minute.")
    freeze_probability: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Probability of a mid-composition freeze.",
    )
    ghost_draft_enabled: bool = Field(
        default=True,
        description="Whether this personality ever does ghost drafts.",
    )


class MarkovTransition(BaseModel):
    """A single transition in the Markov chain with probability."""

    from_state: MarkovStateEnum
    to_state: MarkovStateEnum
    probability: float = Field(ge=0.0, le=1.0)


class MarkovState(BaseModel):
    """Current Markov chain state with transition table."""

    current_state: MarkovStateEnum = Field(default=MarkovStateEnum.IDLE)
    transitions: list[MarkovTransition] = Field(default_factory=list)
    state_duration_ms_min: float = Field(default=1000.0, gt=0)
    state_duration_ms_max: float = Field(default=10000.0, gt=0)


class InterruptionEvent(BaseModel):
    """A triggered behavioral interruption."""

    interruption_type: InterruptionType
    trigger_probability: float = Field(ge=0.0, le=1.0)
    duration_ms_min: float = Field(gt=0)
    duration_ms_max: float = Field(gt=0)
    triggered: bool = Field(default=False)
    triggered_at: datetime | None = Field(default=None)


class SessionState(BaseModel):
    """Complete state of the current interaction session."""

    personality: PersonalityVector
    current_markov_state: MarkovStateEnum = Field(default=MarkovStateEnum.IDLE)
    session_start: datetime = Field(default_factory=datetime.now)
    post_count: int = Field(default=0, ge=0)
    interruptions_triggered: list[InterruptionEvent] = Field(default_factory=list)
    is_ghost_draft_session: bool = Field(default=False)
    seed: int = Field(description="Random seed used to initialize this session.")
