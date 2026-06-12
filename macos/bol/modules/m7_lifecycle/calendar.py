"""
Calendar intelligence engine.

Manages holiday calendars, posting schedules, and daily
eligibility checks with timezone-aware time handling.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bol.schemas.lifecycle import (
    CalendarState,
    DayType,
    HolidayEntry,
    SessionDecision,
)
from bol.utils.logging import get_logger

logger = get_logger(__name__)

# Default holidays (US + India)
_DEFAULT_HOLIDAYS: list[HolidayEntry] = [
    # US holidays
    HolidayEntry(date=date(2026, 1, 1), name="New Year's Day", region="US"),
    HolidayEntry(date=date(2026, 1, 19), name="MLK Day", region="US"),
    HolidayEntry(date=date(2026, 2, 16), name="Presidents' Day", region="US"),
    HolidayEntry(date=date(2026, 5, 25), name="Memorial Day", region="US"),
    HolidayEntry(date=date(2026, 7, 4), name="Independence Day", region="US"),
    HolidayEntry(date=date(2026, 9, 7), name="Labor Day", region="US"),
    HolidayEntry(date=date(2026, 11, 26), name="Thanksgiving", region="US"),
    HolidayEntry(date=date(2026, 12, 25), name="Christmas", region="US"),
    # India holidays
    HolidayEntry(date=date(2026, 1, 26), name="Republic Day", region="IN"),
    HolidayEntry(date=date(2026, 8, 15), name="Independence Day", region="IN"),
    HolidayEntry(date=date(2026, 10, 2), name="Gandhi Jayanti", region="IN"),
    HolidayEntry(date=date(2026, 10, 31), name="Diwali (approx)", region="IN"),
]


class CalendarEngine:
    """
    Calendar intelligence managing posting eligibility,
    holiday awareness, and session scheduling.
    """

    def __init__(self, timezone: str, state_path: Path) -> None:
        self._tz = ZoneInfo(timezone)
        self._timezone = timezone
        self._state_path = state_path
        self._state = self._load_state()

    def get_day_type(self, check_date: date | None = None) -> DayType:
        """Classify a date as WORKDAY, WEEKEND, HOLIDAY, or VOID."""
        d = check_date or date.today()

        # Check void events
        for void in self._state.void_events:
            if void.start_date <= d <= void.end_date:
                return DayType.VOID

        # Check holidays
        for h in self._state.holidays:
            if h.date == d:
                return DayType.HOLIDAY

        # Check weekend
        if d.weekday() in self._state.weekend_days:
            return DayType.WEEKEND

        return DayType.WORKDAY

    def is_posting_allowed(self, check_date: date | None = None, check_hour: int | None = None) -> SessionDecision:
        """
        Check if posting is allowed right now.

        Returns
        -------
        SessionDecision
            Decision with reason and timing details.
        """
        today = check_date or date.today()
        day_type = self.get_day_type(today)
        current_hour = check_hour if check_hour is not None else self._get_local_hour()

        # Check void
        if day_type == DayType.VOID:
            return SessionDecision(
                should_execute=False,
                reason="Currently in a void period",
                day_type=day_type,
            )

        # Check holiday
        if day_type == DayType.HOLIDAY:
            return SessionDecision(
                should_execute=False,
                reason="Today is a holiday",
                day_type=day_type,
            )

        # Check if already posted today
        if self._state.last_post_date == today:
            return SessionDecision(
                should_execute=False,
                reason="Already posted today",
                day_type=day_type,
            )

        # Check posting hours (7 AM - 11 PM)
        if current_hour < 7 or current_hour >= 23:
            # Find next eligible date/time
            next_date = today if current_hour < 7 else today + timedelta(days=1)
            return SessionDecision(
                should_execute=False,
                reason=f"Outside posting hours (current: {current_hour}:00, window: 07:00-23:00)",
                day_type=day_type,
                next_eligible_date=next_date,
            )

        # Determine peak hours
        is_peak = 9 <= current_hour <= 20

        return SessionDecision(
            should_execute=True,
            reason="Posting allowed" + (" (peak hours)" if is_peak else " (off-peak)"),
            day_type=day_type,
            recommended_hour=current_hour if is_peak else 10,
        )

    def record_post(self) -> None:
        """Record that a post was made today."""
        self._state.last_post_date = date.today()
        self._state.total_posts += 1
        self.save_state()
        logger.info("Post recorded. Total posts: %d", self._state.total_posts)

    def _get_local_hour(self) -> int:
        """Get the current hour in the configured timezone."""
        return datetime.now(self._tz).hour

    def save_state(self) -> None:
        """Persist calendar state to JSON."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_path, "w") as f:
            json.dump(self._state.model_dump(mode="json"), f, indent=2, default=str)

    def _load_state(self) -> CalendarState:
        """Load or create calendar state."""
        if self._state_path.exists():
            try:
                with open(self._state_path) as f:
                    data = json.load(f)
                return CalendarState.model_validate(data)
            except Exception:
                logger.warning("Failed to load calendar state, creating fresh")

        state = CalendarState(
            timezone=self._timezone,
            holidays=_DEFAULT_HOLIDAYS,
        )
        return state

    @property
    def state(self) -> CalendarState:
        """Current calendar state."""
        return self._state
