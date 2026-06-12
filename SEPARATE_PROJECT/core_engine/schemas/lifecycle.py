"""
Lifecycle schemas — Data contracts for Module 7 (Session & Profile Lifecycle Controller).

Defines profile configuration, calendar state, void events,
and session execution decisions.
"""

from __future__ import annotations

from datetime import date, datetime
import datetime as dt
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class VoidReason(str, Enum):
    """Reasons for a void (blackout) period."""

    VACATION = "vacation"
    ILLNESS = "illness"
    DIGITAL_DETOX = "digital_detox"
    WEEKEND_EXTENSION = "weekend_extension"


class DayType(str, Enum):
    """Classification of a calendar day."""

    WORKDAY = "workday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    VOID = "void"


class ProfileConfig(BaseModel):
    """Chrome profile configuration for a tenant."""

    tenant_id: str = Field(description="Unique tenant identifier.")
    chrome_binary: str = Field(description="Path to the Chrome binary.")
    profile_directory: str = Field(
        default="Default",
        description="Chrome profile directory name (e.g., 'Profile 1').",
    )
    user_data_dir: Path | None = Field(
        default=None,
        description="Custom Chrome user data directory. If None, uses system default.",
    )

    @property
    def chrome_args(self) -> list[str]:
        """Command-line arguments for launching Chrome with this profile."""
        args = [f"--profile-directory={self.profile_directory}"]
        if self.user_data_dir is not None:
            args.append(f"--user-data-dir={self.user_data_dir}")
        return args


class HolidayEntry(BaseModel):
    """A single holiday entry in the calendar."""

    model_config = {"frozen": True}

    date: dt.date = Field(description="Date of the holiday.")
    name: str = Field(description="Name of the holiday.")
    region: str = Field(default="US", description="Region/country code.")


class VoidEvent(BaseModel):
    """A multi-day blackout window."""

    start_date: date = Field(description="First day of the void period.")
    end_date: date = Field(description="Last day of the void period (inclusive).")
    reason: VoidReason = Field(description="Reason for the blackout.")
    duration_days: int = Field(ge=2, le=5, description="Total duration in days.")

    @property
    def is_active(self) -> bool:
        """Check if the void event is currently active."""
        today = date.today()
        return self.start_date <= today <= self.end_date


class CalendarState(BaseModel):
    """Complete calendar state for scheduling decisions."""

    timezone: str = Field(description="Target timezone (IANA format).")
    holidays: list[HolidayEntry] = Field(default_factory=list)
    void_events: list[VoidEvent] = Field(default_factory=list)
    weekend_days: list[int] = Field(
        default=[5, 6],
        description="ISO weekday numbers that are weekends (5=Saturday, 6=Sunday).",
    )
    last_post_date: date | None = Field(
        default=None,
        description="Date of the most recent successful post.",
    )
    total_posts: int = Field(default=0, ge=0, description="Lifetime post count.")


class SessionDecision(BaseModel):
    """Decision on whether to execute a posting session."""

    should_execute: bool = Field(description="Whether the system should post today.")
    reason: str = Field(description="Human-readable explanation of the decision.")
    day_type: DayType = Field(description="Classification of today.")
    next_eligible_date: date | None = Field(
        default=None,
        description="Next date when posting is eligible (if not today).",
    )
    recommended_hour: int | None = Field(
        default=None, ge=0, le=23,
        description="Recommended hour for posting (if should_execute is True).",
    )
    evaluated_at: datetime = Field(default_factory=datetime.now)
