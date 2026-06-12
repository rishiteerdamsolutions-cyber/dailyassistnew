"""
BOL — Behavioral Operating Layer

Main entry point for the application.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bol.config import BOLConfig
from bol.utils.logging import get_logger, setup_logging
from bol.workflows.linkedin import LinkedInWorkflow

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="BOL — Behavioral Operating Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute a LinkedIn posting session:
  python -m bol.main --platform linkedin --text "My post content here"

  # Dry-run to check calendar and void eligibility:
  python -m bol.main --platform linkedin --dry-run

  # Browse-only session (no posting):
  python -m bol.main --platform linkedin
        """,
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="linkedin",
        help="Target platform (default: linkedin)",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="Post content text. If omitted, runs a browse-only session.",
    )
    parser.add_argument(
        "--text-file",
        type=Path,
        default=None,
        help="Path to a file containing the post content.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check eligibility without executing. Prints calendar/void status.",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/New_York",
        help="Timezone for calendar calculations (default: America/New_York)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override the data directory path.",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=None,
        help="Override the templates directory path.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Main application entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(debug=args.verbose)

    # Build config
    config_overrides: dict = {
        "target_platform": args.platform,
        "timezone": args.timezone,
    }
    if args.data_dir:
        config_overrides["data_dir"] = str(args.data_dir)
    if args.templates_dir:
        config_overrides["templates_dir"] = str(args.templates_dir)

    config = BOLConfig(**config_overrides)

    logger.info("BOL starting — platform=%s, timezone=%s", config.target_platform, config.timezone)

    # Read post text
    post_text = args.text
    if args.text_file and args.text_file.exists():
        post_text = args.text_file.read_text().strip()

    # Dry-run mode
    if args.dry_run:
        from bol.modules.m7_lifecycle import LifecycleController

        lifecycle = LifecycleController(config)
        decision = lifecycle.should_execute_today()
        print(f"Platform: {config.target_platform}")
        print(f"Timezone: {config.timezone}")
        print(f"Should Execute: {decision.should_execute}")
        print(f"Reason: {decision.reason}")
        print(f"Day type: {decision.day_type.value}")
        if decision.next_eligible_date:
            print(f"Next eligible: {decision.next_eligible_date}")
        if decision.recommended_hour:
            print(f"Recommended hour: {decision.recommended_hour}")

        # Show timing pool status
        from bol.modules.m1_timing import TimingManager

        timing = TimingManager(
            db_path=config.resolved_data_dir / "timing_pools" / f"{config.target_platform}.db"
        )
        status = timing.get_pool_status(config.target_platform)
        print(f"\nTiming Pool:")
        print(f"  Size: {status.pool_size}")
        print(f"  Consumed: {status.consumed_count}")
        print(f"  Remaining: {status.remaining_count}")
        print(f"  Cycle: {status.cycle_id}")
        print(f"  Exhaustion: {status.exhaustion_percentage}%")
        timing.close()

        return 0

    # Execute workflow
    if config.target_platform == "linkedin":
        workflow = LinkedInWorkflow(config)
        success = workflow.execute(post_text=post_text)
        return 0 if success else 1
    else:
        logger.error("Unsupported platform: %s", config.target_platform)
        return 1


if __name__ == "__main__":
    sys.exit(main())
