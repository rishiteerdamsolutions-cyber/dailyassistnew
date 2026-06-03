"""Subscription expiry and download eligibility helpers."""

from datetime import datetime, timedelta, timezone

from aha.subscription import is_expired, license_row_is_active


def test_is_expired_past():
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert is_expired(past) is True


def test_is_expired_future():
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    assert is_expired(future) is False


def test_license_row_inactive_when_expired():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert license_row_is_active({"is_active": True, "expires_at": past}) is False


def test_license_row_active_when_valid():
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    assert license_row_is_active({"is_active": True, "expires_at": future}) is True


def test_license_row_inactive_flag():
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    assert license_row_is_active({"is_active": False, "expires_at": future}) is False
