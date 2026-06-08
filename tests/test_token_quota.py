from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from vercel_backend.token_quota import check_direct_access_quota


def _mock_admin(*, count: int):
    admin = MagicMock()
    table = MagicMock()
    admin.table.return_value = table
    chain = table.select.return_value
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.execute.return_value = MagicMock(count=count)
    return admin


def test_quota_allows_under_limit():
    with patch(
        "vercel_backend.token_quota.get_supabase_admin",
        return_value=_mock_admin(count=0),
    ):
        result = check_direct_access_quota("AHA-ABCD-EFGH-IJKL")
    assert result["allowed"] is True


def test_quota_blocks_per_minute_burst():
    with patch(
        "vercel_backend.token_quota.get_supabase_admin",
        return_value=_mock_admin(count=10),
    ):
        result = check_direct_access_quota("AHA-ABCD-EFGH-IJKL")
    assert result["allowed"] is False
    assert "rest" in result["message"].lower()
