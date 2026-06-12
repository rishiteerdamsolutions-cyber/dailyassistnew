"""
Predefined personality vector definitions.

Each personality skews timing, scroll depth, distraction frequency,
typo rates, and fatigue progression to simulate distinct human archetypes.
"""

from __future__ import annotations

import secrets

from bol.schemas.policy import PersonalityVector

# ── Personality Definitions ──────────────────────────────────────────

DISTRACTED_ACADEMIC = PersonalityVector(
    name="The Distracted Academic",
    description="Prone to distractions, deep reading, slow but thoughtful typing",
    timing_modifier=1.4,
    scroll_depth_min=500,
    scroll_depth_max=2000,
    distraction_probability=0.35,
    typo_rate_modifier=0.8,
    fatigue_rate=0.10,
    base_wpm_min=35,
    base_wpm_max=55,
    freeze_probability=0.25,
    ghost_draft_enabled=True,
)

METHODICAL_RECRUITER = PersonalityVector(
    name="The Methodical Recruiter",
    description="Efficient, goal-oriented, minimal distractions",
    timing_modifier=0.85,
    scroll_depth_min=200,
    scroll_depth_max=800,
    distraction_probability=0.10,
    typo_rate_modifier=0.6,
    fatigue_rate=0.05,
    base_wpm_min=55,
    base_wpm_max=80,
    freeze_probability=0.05,
    ghost_draft_enabled=False,
)

CASUAL_SCROLLER = PersonalityVector(
    name="The Casual Scroller",
    description="Relaxed browser, extensive feed scrolling, moderate engagement",
    timing_modifier=1.15,
    scroll_depth_min=800,
    scroll_depth_max=2500,
    distraction_probability=0.25,
    typo_rate_modifier=1.2,
    fatigue_rate=0.08,
    base_wpm_min=45,
    base_wpm_max=65,
    freeze_probability=0.15,
    ghost_draft_enabled=True,
)

ALL_PERSONALITIES: list[PersonalityVector] = [
    DISTRACTED_ACADEMIC,
    METHODICAL_RECRUITER,
    CASUAL_SCROLLER,
]


def select_personality() -> PersonalityVector:
    """Randomly select a personality vector using cryptographic entropy."""
    idx = secrets.randbelow(len(ALL_PERSONALITIES))
    return ALL_PERSONALITIES[idx]
