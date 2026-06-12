"""
LinkedIn posting workflow orchestrator.

Implements the complete LinkedIn session lifecycle:
1. Calendar & Void eligibility check
2. Browser launch with Chrome profile
3. Navigation to LinkedIn feed
4. Markov-driven behavioral simulation
5. Content composition with typo injection
6. Post submission
7. Cooling down & graceful shutdown

All interactions use the 7 BOL modules — zero DOM instrumentation.
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path

from bol.config import BOLConfig
from bol.modules.m1_timing import TimingManager
from bol.modules.m2_kinematic import KinematicSynthesizer
from bol.modules.m3_visual import VisualCortex
from bol.modules.m4_policy import PolicyEngine
from bol.modules.m5_linguistic import LinguisticEngine
from bol.modules.m6_bridge import AccessibilityBridge
from bol.modules.m7_lifecycle import LifecycleController
from bol.schemas.bridge import ClickEvent, MouseButton
from bol.schemas.kinematic import Point2D, ScrollDirection
from bol.schemas.policy import MarkovStateEnum
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class LinkedInWorkflow:
    """
    Complete LinkedIn session orchestrator.

    Composes all 7 BOL modules into a realistic, personality-driven
    LinkedIn interaction session.
    """

    def __init__(self, config: BOLConfig) -> None:
        self._config = config

        # Initialize all modules
        self._timing = TimingManager(
            db_path=config.resolved_data_dir / "timing_pools" / "linkedin.db"
        )
        self._kinematic = KinematicSynthesizer()
        self._visual = VisualCortex(config)
        self._policy = PolicyEngine()
        self._linguistic = LinguisticEngine(
            personality=self._policy.personality,
            history_db_path=config.resolved_data_dir / "content" / "variance_history.json",
        )
        self._bridge = AccessibilityBridge()
        self._lifecycle = LifecycleController(config)

        # Wire the bridge into the lifecycle controller
        self._lifecycle.set_bridge(self._bridge)

    def execute(self, post_text: str | None = None) -> bool:
        """
        Execute a complete LinkedIn session.

        Parameters
        ----------
        post_text : str | None
            Content to post. If None, runs a browse-only session.

        Returns
        -------
        bool
            True if the session completed successfully.
        """
        logger.info("═══ LinkedIn Workflow Starting ═══")

        # ── Step 1: Calendar & Void Check ──
        decision = self._lifecycle.should_execute_today()
        if not decision.should_execute:
            logger.info("Session blocked: %s", decision.reason)
            return False
        logger.info("Session allowed: %s", decision.reason)

        # ── Step 2: Initialize Behavioral Policy ──
        session = self._policy.initialize_session()
        logger.info(
            "Personality: '%s', Seed: %d",
            session.personality.name, session.seed,
        )

        # Check for init-time interruptions (notification loop)
        for interruption in session.interruptions_triggered:
            duration_ms = interruption.duration_ms_min + secrets.randbelow(
                int(interruption.duration_ms_max - interruption.duration_ms_min)
            )
            logger.info(
                "Init interruption: %s (%.1fs)",
                interruption.interruption_type.value, duration_ms / 1000,
            )
            time.sleep(duration_ms / 1000.0)

        # ── Step 3: Launch Browser ──
        if not self._lifecycle.launch_browser():
            logger.error("Failed to launch browser")
            return False

        try:
            # ── Step 4: Navigate to Feed ──
            self._lifecycle.navigate_to("https://www.linkedin.com/feed")
            delay = self._timing.get_delay("linkedin")
            delay = self._timing.apply_personality_modifier(delay, session.personality.timing_modifier)
            time.sleep(delay * 3)  # Extra wait for page load

            # ── Step 5: Markov-Driven Behavioral Loop ──
            self._run_behavioral_loop(post_text)

            # ── Step 6: Record & Cool Down ──
            if post_text is not None:
                self._lifecycle.record_session_completion()

            logger.info("═══ LinkedIn Workflow Completed Successfully ═══")
            return True

        finally:
            # ── Step 7: Graceful Shutdown ──
            cooldown = self._timing.get_delay("linkedin") * 2
            logger.info("Cooling down for %.1fs", cooldown)
            time.sleep(cooldown)
            self._lifecycle.shutdown_browser()

    def _run_behavioral_loop(self, post_text: str | None) -> None:
        """Execute the Markov state machine behavioral loop."""
        max_transitions = 15
        posted = False

        for i in range(max_transitions):
            state = self._policy.get_current_state()
            duration_ms = self._policy.get_state_duration_ms()
            logger.info(
                "State [%d/%d]: %s (%.1fs)",
                i + 1, max_transitions, state.value, duration_ms / 1000,
            )

            # Execute state behavior
            if state == MarkovStateEnum.IDLE:
                self._execute_idle(duration_ms)
            elif state == MarkovStateEnum.SCROLLING:
                self._execute_scroll(duration_ms)
            elif state == MarkovStateEnum.READING:
                self._execute_read(duration_ms)
            elif state == MarkovStateEnum.COMPOSING:
                if post_text is not None and not posted:
                    self._execute_compose(post_text)
                else:
                    self._execute_read(duration_ms)
            elif state == MarkovStateEnum.DISTRACTED:
                self._execute_distracted(duration_ms)
            elif state == MarkovStateEnum.POSTING:
                if post_text is not None and not posted:
                    self._execute_post()
                    posted = True
                    self._linguistic.record_posted_text(post_text)
            elif state == MarkovStateEnum.COOLING_DOWN:
                self._execute_cooldown(duration_ms)
            elif state == MarkovStateEnum.EXITING:
                logger.info("Exiting behavioral loop")
                break

            # Check for mid-state interruptions
            interruption = self._policy.should_interrupt(
                "composing" if state == MarkovStateEnum.COMPOSING else "init"
            )
            if interruption is not None:
                pause_ms = interruption.duration_ms_min + secrets.randbelow(
                    int(interruption.duration_ms_max - interruption.duration_ms_min)
                )
                logger.info(
                    "Interruption: %s (%.1fs)",
                    interruption.interruption_type.value, pause_ms / 1000,
                )
                time.sleep(pause_ms / 1000.0)

            # Advance Markov chain
            self._policy.advance_state()

    # ── State Implementations ──────────────────────────────────────

    def _execute_idle(self, duration_ms: float) -> None:
        """Idle: just wait with timing jitter."""
        delay = self._timing.get_delay("linkedin")
        time.sleep(delay + duration_ms / 1000.0 * 0.1)

    def _execute_scroll(self, duration_ms: float) -> None:
        """Scroll the feed using sinusoidal physics."""
        personality = self._policy.personality
        depth = personality.scroll_depth_min + secrets.randbelow(
            max(personality.scroll_depth_max - personality.scroll_depth_min, 1)
        )
        profile = self._kinematic.generate_scroll(depth, ScrollDirection.DOWN)
        self._bridge.execute_scroll(profile)

    def _execute_read(self, duration_ms: float) -> None:
        """Simulate reading a post (just a timed pause)."""
        time.sleep(duration_ms / 1000.0)

    def _execute_compose(self, text: str) -> None:
        """Compose a post by clicking the post button and typing."""
        # Locate and click "Start a post"
        target = self._visual.locate_text("Start a post")
        if target is None:
            target = self._visual.locate_element("start_post_button")
        if target is None:
            logger.warning("Could not find 'Start a post' button")
            return

        # Move cursor to target
        current_pos = self._bridge.get_cursor_position()
        path = self._kinematic.generate_movement(current_pos, target)
        self._bridge.execute_movement(path.trajectory_points, path.total_duration_ms)

        # Click
        delay = self._timing.get_delay("linkedin")
        click_event = ClickEvent(
            target_x=target.click_x,
            target_y=target.click_y,
            button=MouseButton.LEFT,
            pre_click_delay_ms=delay * 1000,
        )
        self._bridge.execute_click(click_event)

        # Wait for post dialog
        time.sleep(1.5 + secrets.randbelow(11) / 10.0)

        # Generate and execute keystroke sequence
        payload = self._linguistic.prepare_payload(text)
        keystrokes = self._linguistic.generate_keystroke_sequence(payload)
        self._bridge.execute_keystroke_sequence(keystrokes.events)

        logger.info(
            "Composed %d chars, %d typos, WPM %.1f→%.1f",
            payload.character_count,
            keystrokes.typo_count,
            keystrokes.effective_wpm_start,
            keystrokes.effective_wpm_end,
        )

    def _execute_post(self) -> None:
        """Click the Post button to submit the composed content."""
        target = self._visual.locate_text("Post")
        if target is None:
            target = self._visual.locate_element("post_submit_button")
        if target is None:
            logger.warning("Could not find 'Post' submit button")
            return

        current_pos = self._bridge.get_cursor_position()
        path = self._kinematic.generate_movement(current_pos, target)
        self._bridge.execute_movement(path.trajectory_points, path.total_duration_ms)

        delay = self._timing.get_delay("linkedin")
        click_event = ClickEvent(
            target_x=target.click_x,
            target_y=target.click_y,
            button=MouseButton.LEFT,
            pre_click_delay_ms=delay * 1000,
        )
        self._bridge.execute_click(click_event)
        logger.info("Post submitted!")

        # Wait for submission confirmation
        time.sleep(2.0 + secrets.randbelow(21) / 10.0)

    def _execute_distracted(self, duration_ms: float) -> None:
        """Simulate distraction: pause + random minor scroll."""
        # Long pause
        time.sleep(duration_ms / 1000.0 * 0.7)

        # Maybe a tiny scroll
        if secrets.randbelow(2) == 0:
            mini_scroll = self._kinematic.generate_scroll(
                50 + secrets.randbelow(100),
                ScrollDirection.DOWN if secrets.randbelow(2) == 0 else ScrollDirection.UP,
            )
            self._bridge.execute_scroll(mini_scroll)

    def _execute_cooldown(self, duration_ms: float) -> None:
        """Cool down: slow scroll and wait."""
        time.sleep(duration_ms / 1000.0)
