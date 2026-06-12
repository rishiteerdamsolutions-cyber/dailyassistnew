"""
Markov chain state machine for session behavior.

Governs high-level behavioral state transitions influenced
by the active personality vector.
"""

from __future__ import annotations

import secrets

from bol.schemas.policy import (
    MarkovStateEnum,
    MarkovTransition,
    PersonalityVector,
)
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class MarkovChainEngine:
    """
    Personality-influenced Markov chain for behavioral state transitions.

    Transition probabilities are dynamically computed from the active
    personality vector and normalized to sum to 1.0 per state.
    """

    def __init__(self, personality: PersonalityVector) -> None:
        self._personality = personality
        self._current_state = MarkovStateEnum.IDLE
        self._transitions = self._build_transitions()

    @property
    def current_state(self) -> MarkovStateEnum:
        """Current Markov chain state."""
        return self._current_state

    def set_state(self, state: MarkovStateEnum) -> None:
        """Force-set the current state."""
        self._current_state = state
        logger.debug("State forced to: %s", state.value)

    def advance(self) -> MarkovStateEnum:
        """
        Advance to the next state based on transition probabilities.

        Returns
        -------
        MarkovStateEnum
            The new current state.
        """
        transitions = self._transitions.get(self._current_state, [])
        if not transitions:
            logger.warning("No transitions from state %s", self._current_state.value)
            return self._current_state

        # Select next state using weighted random selection
        roll = secrets.randbelow(10000) / 10000.0
        cumulative = 0.0
        for t in transitions:
            cumulative += t.probability
            if roll < cumulative:
                self._current_state = t.to_state
                logger.debug("State transition → %s (roll=%.4f)", t.to_state.value, roll)
                return self._current_state

        # Fallback to last transition
        self._current_state = transitions[-1].to_state
        return self._current_state

    def get_state_duration_ms(self) -> float:
        """
        Get a randomized duration for the current state.

        Duration is influenced by the personality timing modifier.
        """
        base_durations: dict[MarkovStateEnum, tuple[float, float]] = {
            MarkovStateEnum.IDLE: (1000, 5000),
            MarkovStateEnum.SCROLLING: (2000, 8000),
            MarkovStateEnum.READING: (3000, 12000),
            MarkovStateEnum.COMPOSING: (5000, 30000),
            MarkovStateEnum.DISTRACTED: (3000, 15000),
            MarkovStateEnum.POSTING: (1000, 3000),
            MarkovStateEnum.COOLING_DOWN: (5000, 20000),
            MarkovStateEnum.EXITING: (1000, 3000),
        }
        min_ms, max_ms = base_durations.get(self._current_state, (1000, 5000))
        range_ms = max_ms - min_ms
        base = min_ms + secrets.randbelow(int(range_ms))
        return base * self._personality.timing_modifier

    def _build_transitions(
        self,
    ) -> dict[MarkovStateEnum, list[MarkovTransition]]:
        """Build and normalize transition probabilities per state."""
        p = self._personality
        raw: dict[MarkovStateEnum, list[tuple[MarkovStateEnum, float]]] = {
            MarkovStateEnum.IDLE: [
                (MarkovStateEnum.SCROLLING, 0.7),
                (MarkovStateEnum.READING, 0.2),
                (MarkovStateEnum.DISTRACTED, p.distraction_probability * 0.5),
            ],
            MarkovStateEnum.SCROLLING: [
                (MarkovStateEnum.READING, 0.4),
                (MarkovStateEnum.COMPOSING, 0.3),
                (MarkovStateEnum.DISTRACTED, p.distraction_probability),
            ],
            MarkovStateEnum.READING: [
                (MarkovStateEnum.SCROLLING, 0.3),
                (MarkovStateEnum.COMPOSING, 0.5),
                (MarkovStateEnum.DISTRACTED, p.distraction_probability * 0.3),
            ],
            MarkovStateEnum.COMPOSING: [
                (MarkovStateEnum.POSTING, 0.7),
                (MarkovStateEnum.DISTRACTED, p.freeze_probability),
            ],
            MarkovStateEnum.DISTRACTED: [
                (MarkovStateEnum.SCROLLING, 0.5),
                (MarkovStateEnum.READING, 0.3),
                (MarkovStateEnum.COMPOSING, 0.2),
            ],
            MarkovStateEnum.POSTING: [
                (MarkovStateEnum.COOLING_DOWN, 1.0),
            ],
            MarkovStateEnum.COOLING_DOWN: [
                (MarkovStateEnum.EXITING, 1.0),
            ],
        }

        result: dict[MarkovStateEnum, list[MarkovTransition]] = {}
        for state, trans_list in raw.items():
            total = sum(prob for _, prob in trans_list)
            if total <= 0:
                total = 1.0
            normalized = [
                MarkovTransition(
                    from_state=state,
                    to_state=to_state,
                    probability=prob / total,
                )
                for to_state, prob in trans_list
            ]
            result[state] = normalized

        return result
