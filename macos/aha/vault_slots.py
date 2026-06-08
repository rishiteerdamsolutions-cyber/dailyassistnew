"""Content Vault slot paths — calendar days under ~/Downloads/aha/Slots/."""

from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path

from aha.storage_vault import vault_root
from aha.vault_paths import safe_slot_name


def slots_root() -> Path:
    root = vault_root() / "Slots"
    root.mkdir(parents=True, exist_ok=True)
    return root


def month_dir(slot: str, year: int, month: int) -> Path:
    safe = safe_slot_name(slot)
    return slots_root() / safe / str(year) / str(month)


def text_path(slot: str, year: int, month: int, day: int) -> Path:
    return month_dir(slot, year, month) / "Texts" / f"{day}.txt"


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def day_has_text(slot: str, year: int, month: int, day: int) -> bool:
    p = text_path(slot, year, month, day)
    return p.exists() and p.stat().st_size > 0


def last_filled_text_day(slot: str, year: int, month: int) -> int:
    """Highest day number in this month that already has caption text."""
    last = 0
    for day in range(1, days_in_month(year, month) + 1):
        if day_has_text(slot, year, month, day):
            last = day
    return last


def next_text_day(slot: str, year: int, month: int) -> int:
    """First empty day after the last filled caption (1 if none yet)."""
    n = days_in_month(year, month)
    start = last_filled_text_day(slot, year, month) + 1
    if start > n:
        raise ValueError(f"Slot '{slot}' has no empty text days left in {year}-{month:02d}.")
    return start


def resolve_batch_days(
    slot: str,
    year: int,
    month: int,
    num_days: int,
    *,
    start_day: int | None = None,
) -> tuple[int, list[int]]:
    if num_days < 1:
        raise ValueError("num_days must be at least 1.")
    n = days_in_month(year, month)
    start = start_day if start_day is not None else next_text_day(slot, year, month)
    if start < 1 or start > n:
        raise ValueError(f"start_day must be 1..{n}.")
    end = start + num_days - 1
    if end > n:
        raise ValueError(
            f"Not enough days in {year}-{month:02d}: need {num_days} from day {start}, "
            f"but month ends on day {n}."
        )
    return start, list(range(start, end + 1))


def write_slot_text(slot: str, year: int, month: int, day: int, text: str) -> Path:
    from aha.storage_vault import atomic_write_text

    path = text_path(slot, year, month, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, (text or "").strip())
    return path


def current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month
