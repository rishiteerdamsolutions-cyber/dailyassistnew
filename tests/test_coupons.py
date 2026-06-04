"""Coupon validation (no Supabase required for format checks)."""

import os

from aha.admin_auth import admin_emails, is_admin_email


def test_admin_email_allowlist():
    os.environ["AHA_ADMIN_EMAILS"] = "Admin@Example.com, other@test.io"
    assert is_admin_email("admin@example.com")
    assert not is_admin_email("stranger@test.io")
    assert "other@test.io" in admin_emails()


def test_normalize_coupon_code():
    from aha.coupons import _normalize_code

    assert _normalize_code(" coupon100 ") == "COUPON100"
