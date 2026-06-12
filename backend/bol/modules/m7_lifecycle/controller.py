"""
Lifecycle Controller — Public API for Module 7.

Orchestrates calendar intelligence, void events, and Chrome
profile management into a unified session lifecycle interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bol.config import BOLConfig
from bol.modules.m7_lifecycle.calendar import CalendarEngine
from bol.modules.m7_lifecycle.void import VoidEngine
from bol.modules.m7_lifecycle.profile import ChromeProfileManager
from bol.schemas.lifecycle import SessionDecision
from bol.utils.logging import get_logger

if TYPE_CHECKING:
    from bol.modules.m6_bridge.bridge import AccessibilityBridge

logger = get_logger(__name__)


class LifecycleController:
    """
    Unified session lifecycle management composing calendar,
    void scheduling, and Chrome profile management.
    """

    def __init__(self, config: BOLConfig) -> None:
        self._config = config

        # Initialize subsystems
        self._calendar = CalendarEngine(
            timezone=config.timezone,
            state_path=config.resolved_data_dir / "calendar" / f"{config.target_platform}.json",
        )
        self._void = VoidEngine(self._calendar.state)
        self._profile = ChromeProfileManager(config)

        # Generate void schedule if none exists
        if not self._calendar.state.void_events:
            self._void.generate_void_schedule(months_ahead=3)
            self._calendar.save_state()

    def should_execute_today(self, check_date: date | None = None, check_hour: int | None = None) -> SessionDecision:
        """
        Determine if a session should execute today.

        Checks void events first, then calendar rules.
        """
        # Check void first
        if self._void.is_in_void():
            active = self._void.get_active_void()
            reason = f"In void period: {active.reason.value}" if active else "In void period"
            return SessionDecision(
                should_execute=False,
                reason=reason,
                day_type=self._calendar.get_day_type(check_date),
            )

        # Delegate to calendar
        return self._calendar.is_posting_allowed(check_date, check_hour)

    def launch_browser(self) -> bool:
        """Launch the configured Chrome profile."""
        return self._profile.launch_browser()

    def shutdown_browser(self) -> None:
        """Shut down Chrome gracefully via keyboard shortcut."""
        self._profile.shutdown_browser()

    def navigate_to(self, url: str) -> None:
        """Navigate to a URL via the address bar."""
        self._profile.navigate_to(url)

    def record_session_completion(self) -> None:
        """Record that a post was successfully made today."""
        self._calendar.record_post()
        self._calendar.save_state()

    def set_bridge(self, bridge: AccessibilityBridge) -> None:
        """Inject the accessibility bridge into the profile manager."""
        self._profile.set_bridge(bridge)
