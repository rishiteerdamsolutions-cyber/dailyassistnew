"""
Conditional interruption anchors.

Implements notification loops, mid-composition freezes,
and ghost draft behaviors as probabilistic triggers.
"""

from __future__ import annotations

import secrets
from datetime import datetime

from bol.schemas.policy import InterruptionEvent, InterruptionType, PersonalityVector
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class InterruptionEngine:
    """
    Evaluates and triggers behavioral interruptions based on
    personality parameters and contextual probability checks.
    """

    def __init__(self, personality: PersonalityVector) -> None:
        self._personality = personality

    def check_notification_loop(self) -> InterruptionEvent | None:
        """Check for a notification loop interruption (20% base probability)."""
        if self._roll(0.20):
            event = InterruptionEvent(
                interruption_type=InterruptionType.NOTIFICATION_LOOP,
                trigger_probability=0.20,
                duration_ms_min=5000.0,
                duration_ms_max=15000.0,
                triggered=True,
                triggered_at=datetime.now(),
            )
            logger.info("Notification loop triggered")
            return event
        return None

    def check_mid_composition_freeze(self) -> InterruptionEvent | None:
        """Check for a mid-composition freeze (probability from personality)."""
        prob = self._personality.freeze_probability
        if self._roll(prob):
            event = InterruptionEvent(
                interruption_type=InterruptionType.MID_COMPOSITION_FREEZE,
                trigger_probability=prob,
                duration_ms_min=20000.0,
                duration_ms_max=50000.0,
                triggered=True,
                triggered_at=datetime.now(),
            )
            logger.info("Mid-composition freeze triggered (%.0f%%)", prob * 100)
            return event
        return None

    def check_ghost_draft(self, days_since_last: int) -> InterruptionEvent | None:
        """
        Check for a ghost draft event.

        Only eligible if personality allows it and enough days have passed
        since the last ghost draft (14-28 day window).
        """
        if not self._personality.ghost_draft_enabled:
            return None

        # Eligible window: 14-28 days since last ghost draft
        if days_since_last < 14:
            return None

        # 30% trigger probability when eligible
        if self._roll(0.30):
            event = InterruptionEvent(
                interruption_type=InterruptionType.GHOST_DRAFT,
                trigger_probability=0.30,
                duration_ms_min=30000.0,
                duration_ms_max=120000.0,
                triggered=True,
                triggered_at=datetime.now(),
            )
            logger.info("Ghost draft triggered (days since last: %d)", days_since_last)
            return event
        return None

    def should_interrupt(self, context: str) -> InterruptionEvent | None:
        """
        Central interruption check based on context.

        Parameters
        ----------
        context : str
            Current context: 'init', 'composing', or 'calendar_check'.

        Returns
        -------
        InterruptionEvent | None
            Triggered event, or None.
        """
        if context == "init":
            return self.check_notification_loop()
        elif context == "composing":
            return self.check_mid_composition_freeze()
        elif context == "calendar_check":
            return self.check_ghost_draft(days_since_last=30)  # Default to eligible
        return None

    @staticmethod
    def _roll(probability: float) -> bool:
        """Roll against a probability using cryptographic entropy."""
        return secrets.randbelow(1000) / 1000.0 < probability
