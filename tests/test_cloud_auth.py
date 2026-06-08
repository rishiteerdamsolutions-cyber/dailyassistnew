import os
from unittest.mock import MagicMock, patch

import pytest

from vercel_backend.cloud_auth import cloud_auth_required, validate_cloud_caller


def test_cloud_auth_not_required_by_default(monkeypatch):
    monkeypatch.delenv("AHA_REQUIRE_CLOUD_AUTH", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert cloud_auth_required() is False


def test_cloud_auth_required_on_production_vercel(monkeypatch):
    monkeypatch.delenv("AHA_REQUIRE_CLOUD_AUTH", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert cloud_auth_required() is True


def test_validate_allows_missing_token_when_auth_optional(monkeypatch):
    monkeypatch.setenv("AHA_REQUIRE_CLOUD_AUTH", "0")
    assert validate_cloud_caller("AHA-TEST-KEY-1234", None) == ""


def test_validate_rejects_missing_token_when_required(monkeypatch):
    monkeypatch.setenv("AHA_REQUIRE_CLOUD_AUTH", "1")
    with pytest.raises(ValueError, match="Sign in"):
        validate_cloud_caller("AHA-TEST-KEY-1234", None)


def test_validate_rejects_license_uid_mismatch(monkeypatch):
    monkeypatch.setenv("AHA_REQUIRE_CLOUD_AUTH", "1")
    admin = MagicMock()
    table = MagicMock()
    admin.table.return_value = table
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"uid": "owner-uid"}])
    )
    with patch("vercel_backend.cloud_auth.verify_firebase_token", return_value={"uid": "other-uid"}):
        with patch("vercel_backend.cloud_auth.get_supabase_admin", return_value=admin):
            with pytest.raises(ValueError, match="does not match"):
                validate_cloud_caller("AHA-TEST-KEY-1234", "fake-token")


def test_validate_accepts_matching_uid(monkeypatch):
    monkeypatch.setenv("AHA_REQUIRE_CLOUD_AUTH", "1")
    admin = MagicMock()
    table = MagicMock()
    admin.table.return_value = table
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"uid": "user-42"}])
    )
    with patch("vercel_backend.cloud_auth.verify_firebase_token", return_value={"uid": "user-42"}):
        with patch("vercel_backend.cloud_auth.get_supabase_admin", return_value=admin):
            assert validate_cloud_caller("AHA-TEST-KEY-1234", "good-token") == "user-42"
