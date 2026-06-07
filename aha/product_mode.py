"""Product mode flags — Tier-1-only launch vs full assistant."""

from __future__ import annotations

import os

TIER1_ONLY_HELP = (
    "That ask needs general computer assistance with an AI key — coming in a future update.\n\n"
    "Right now AHA helps with:\n"
    "• Social posting — Instagram, Facebook, LinkedIn, X, WhatsApp\n"
    "• Dev workspace — git push, .env.local, SSH keys, open project\n"
    "• System — connect Bluetooth devices, open folders\n\n"
    "Try: \"post today's photo on Instagram\" or \"push dailyassist to git\""
)


def tier1_only_mode() -> bool:
    """True when retail launch ships Tier-1 flows only (no BYOK / Tier-2 LLM)."""
    from aha.runtime_paths import is_retail_build

    raw = os.environ.get("AHA_TIER1_ONLY", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    # Default: retail builds launch Tier-1 only until Tier-2 is ready.
    return is_retail_build()


def product_mode_payload() -> dict:
    tier1 = tier1_only_mode()
    return {
        "tier1_only": tier1,
        "tier2_enabled": not tier1,
        "label": "Tier-1 precision" if tier1 else "Full assistant",
    }
