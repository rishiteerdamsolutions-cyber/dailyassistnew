"""Local dev gates must never apply in retail or on Vercel."""

import os

from aha.dev_mode import dev_gates_open


def test_dev_gates_closed_by_default(monkeypatch):
    monkeypatch.delenv("AHA_DEV_OPEN_GATES", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("AHA_RETAIL_BUILD", raising=False)
    assert dev_gates_open() is False


def test_dev_gates_open_when_env_set(monkeypatch):
    monkeypatch.setenv("AHA_DEV_OPEN_GATES", "1")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("AHA_RETAIL_BUILD", raising=False)
    assert dev_gates_open() is True


def test_dev_gates_blocked_on_vercel(monkeypatch):
    monkeypatch.setenv("AHA_DEV_OPEN_GATES", "1")
    monkeypatch.setenv("VERCEL", "1")
    assert dev_gates_open() is False


def test_dev_gates_blocked_in_retail(monkeypatch):
    monkeypatch.setenv("AHA_DEV_OPEN_GATES", "1")
    monkeypatch.setenv("AHA_RETAIL_BUILD", "1")
    assert dev_gates_open() is False
