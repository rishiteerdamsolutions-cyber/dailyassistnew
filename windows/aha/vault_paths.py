"""Vault path helpers — slot sanitization shared by API and tests."""

from __future__ import annotations


def safe_slot_name(slot: str) -> str:
    """Return a sanitized slot name or raise ValueError."""
    safe = "".join(c for c in slot if c.isalnum() or c in (" ", "-", "_")).strip()
    if not safe or safe != slot:
        raise ValueError("Invalid slot name.")
    return safe
