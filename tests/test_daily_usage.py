"""Unit tests for server-side daily limit helpers."""

from datetime import date
from unittest.mock import MagicMock, patch

from vercel_backend.usage import LIMIT_MESSAGE, normalize_platform, usage_date_utc


def test_normalize_platform_aliases():
    assert normalize_platform("fb") == "facebook"
    assert normalize_platform("IG") == "instagram"
    assert normalize_platform("twitter") == "x"


def test_usage_date_utc_is_date():
    assert isinstance(usage_date_utc(), date)


def test_check_available_blocks_when_already_posted():
    mock_admin = MagicMock()
    mock_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "x", "last_post_timestamp": "2026-06-08T12:00:00Z"}]
    )

    with patch("vercel_backend.usage.get_supabase_admin", return_value=mock_admin):
        from vercel_backend.usage import check_available

        result = check_available("AHA-TEST-KEY-1234", "facebook")

    assert result["allowed"] is False
    assert result["message"] == LIMIT_MESSAGE
    mock_admin.table.return_value.insert.assert_not_called()


def test_check_available_does_not_reserve():
    mock_admin = MagicMock()
    select_chain = mock_admin.table.return_value.select.return_value
    select_chain.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with patch("vercel_backend.usage.get_supabase_admin", return_value=mock_admin):
        from vercel_backend.usage import check_available

        result = check_available("AHA-TEST-KEY-5678", "instagram")

    assert result["allowed"] is True
    mock_admin.table.return_value.insert.assert_not_called()


def test_record_completed_post_inserts_once():
    mock_admin = MagicMock()
    select_chain = mock_admin.table.return_value.select.return_value
    select_chain.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

    with patch("vercel_backend.usage.get_supabase_admin", return_value=mock_admin):
        with patch("vercel_backend.usage._lookup_uid", return_value=None):
            from vercel_backend.usage import record_completed_post

            result = record_completed_post(
                "AHA-TEST-KEY-9999", "facebook", task_id="facebook_post"
            )

    assert result["recorded"] is True
    mock_admin.table.return_value.insert.assert_called_once()
