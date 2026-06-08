import pytest

from aha.vault_slots import last_filled_text_day, resolve_batch_days, next_text_day


def test_resolve_batch_auto_start(tmp_path, monkeypatch):
    monkeypatch.setattr("aha.vault_slots.slots_root", lambda: tmp_path / "Slots")
    slot = "facebook"
    base = tmp_path / "Slots" / slot / "2026" / "6" / "Texts"
    base.mkdir(parents=True)
    for d in (1, 2, 3, 4, 5):
        (base / f"{d}.txt").write_text(f"day {d}", encoding="utf-8")

    start, days = resolve_batch_days(slot, 2026, 6, 3)
    assert start == 6
    assert days == [6, 7, 8]
    assert last_filled_text_day(slot, 2026, 6) == 5
    assert next_text_day(slot, 2026, 6) == 6


def test_resolve_batch_not_enough_days(tmp_path, monkeypatch):
    monkeypatch.setattr("aha.vault_slots.slots_root", lambda: tmp_path / "Slots")
    slot = "x"
    with pytest.raises(ValueError, match="Not enough days"):
        resolve_batch_days(slot, 2026, 6, 10, start_day=28)
