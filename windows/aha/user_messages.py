"""User-facing copy — keep assistant tone, not automation jargon."""

from __future__ import annotations


def rest_cooldown_message(hours: float | int) -> str:
    """Shown when Direct Access chat token window is exhausted (rolling cooldown)."""
    h = max(1, int(round(float(hours))))
    if h == 1:
        return (
            "You've been using computer for hours now, take some rest "
            "and comeback after 1 hour."
        )
    return (
        f"You've been using computer for hours now, take some rest "
        f"and comeback after {h} hours."
    )
