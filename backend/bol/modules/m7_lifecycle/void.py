"""
Void event engine.

Generates and manages scheduled inactivity periods that break
perfectly regular posting patterns.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from bol.schemas.lifecycle import CalendarState, VoidEvent, VoidReason
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class VoidEngine:
    """
    Manages void events — scheduled periods of deliberate
    inactivity that break temporal regularity.
    """

    def __init__(self, calendar_state: CalendarState) -> None:
        self._state = calendar_state

    def generate_void_schedule(self, months_ahead: int = 3) -> list[VoidEvent]:
        """
        Generate approximately one void event every 3-6 weeks.

        Parameters
        ----------
        months_ahead : int
            How many months ahead to schedule.

        Returns
        -------
        list[VoidEvent]
            Generated void events.
        """
        voids: list[VoidEvent] = []
        today = date.today()
        end_date = today + timedelta(days=months_ahead * 30)

        # Build set of holiday dates to avoid
        holiday_dates: set[date] = set()
        for h in self._state.holidays:
            holiday_dates.add(h.date)

        cursor = today + timedelta(days=21 + secrets.randbelow(22))  # 3-6 weeks out

        while cursor < end_date:
            # Duration: 2-4 days (schema requires ge=2, le=5)
            duration = 2 + secrets.randbelow(3)  # 2 to 4
            void_end = cursor + timedelta(days=duration - 1)

            # Check for holiday conflict
            conflict = False
            for d_offset in range(duration):
                check = cursor + timedelta(days=d_offset)
                if check in holiday_dates:
                    conflict = True
                    break

            if not conflict:
                # Random reason
                reasons = list(VoidReason)
                reason = reasons[secrets.randbelow(len(reasons))]

                void = VoidEvent(
                    start_date=cursor,
                    end_date=void_end,
                    reason=reason,
                    duration_days=duration,
                )
                voids.append(void)
                logger.debug(
                    "Scheduled void: %s to %s (%s, %d days)",
                    cursor.isoformat(), void_end.isoformat(), reason.value, duration,
                )

            # Next void: 3-6 weeks from end of this one
            cursor = void_end + timedelta(days=21 + secrets.randbelow(22))

        # Store in calendar state
        self._state.void_events.extend(voids)
        return voids

    def is_in_void(self) -> bool:
        """Check if today falls within any active void event."""
        today = date.today()
        return any(v.start_date <= today <= v.end_date for v in self._state.void_events)

    def get_next_void(self) -> VoidEvent | None:
        """Return the next upcoming void event, or None."""
        today = date.today()
        future = [v for v in self._state.void_events if v.start_date > today]
        return min(future, key=lambda v: v.start_date) if future else None

    def get_active_void(self) -> VoidEvent | None:
        """Return the currently active void event, or None."""
        today = date.today()
        for v in self._state.void_events:
            if v.start_date <= today <= v.end_date:
                return v
        return None
