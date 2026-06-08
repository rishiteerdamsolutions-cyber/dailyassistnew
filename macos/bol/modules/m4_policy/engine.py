"""
Policy Engine — Public API for Module 4.

Orchestrates personality selection, Markov state management,
and interruption evaluation into a unified behavioral policy interface.
"""

from __future__ import annotations

import secrets
from datetime import datetime

from bol.modules.m4_policy.interruptions import InterruptionEngine
from bol.modules.m4_policy.markov import MarkovChainEngine
from bol.modules.m4_policy.personality import select_personality
from bol.schemas.policy import (
    InterruptionEvent,
    MarkovStateEnum,
    PersonalityVector,
    SessionState,
)
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyEngine:
    """
    Behavioral Policy & State Engine.

    Manages the psychological state of the interaction session
    using personality vectors and a Markov chain engine.
    """

    def __init__(self, personality: PersonalityVector | None = None) -> None:
        if personality is None:
            personality = select_personality()
        self._personality = personality
        self._markov = MarkovChainEngine(personality)
        self._interruptions = InterruptionEngine(personality)
        self._session_state: SessionState | None = None
        logger.info("PolicyEngine initialized with personality: %s", personality.name)

    def initialize_session(self) -> SessionState:
        """
        Initialize a new interaction session.

        Rolls the personality, sets up the Markov chain,
        and evaluates initial interruptions.
        """
        seed = secrets.randbits(64)
        self._session_state = SessionState(
            personality=self._personality,
            current_markov_state=MarkovStateEnum.IDLE,
            session_start=datetime.now(),
            post_count=0,
            seed=seed,
        )

        # Check for init-time interruptions
        init_interrupt = self._interruptions.should_interrupt("init")
        if init_interrupt is not None:
            self._session_state.interruptions_triggered.append(init_interrupt)

        logger.info(
            "Session initialized: personality='%s', seed=%d, interruptions=%d",
            self._personality.name,
            seed,
            len(self._session_state.interruptions_triggered),
        )
        return self._session_state

    def get_current_state(self) -> MarkovStateEnum:
        """Get the current Markov chain state."""
        return self._markov.current_state

    def advance_state(self) -> MarkovStateEnum:
        """Advance the Markov chain to the next state."""
        new_state = self._markov.advance()
        if self._session_state is not None:
            self._session_state.current_markov_state = new_state
        return new_state

    def should_interrupt(self, context: str) -> InterruptionEvent | None:
        """Check if an interruption should occur in the given context."""
        event = self._interruptions.should_interrupt(context)
        if event is not None and self._session_state is not None:
            self._session_state.interruptions_triggered.append(event)
        return event

    def get_state_duration_ms(self) -> float:
        """Get a randomized duration for the current state."""
        return self._markov.get_state_duration_ms()

    @property
    def personality(self) -> PersonalityVector:
        """The active personality vector."""
        return self._personality

    @property
    def session(self) -> SessionState | None:
        """The current session state."""
        return self._session_state
