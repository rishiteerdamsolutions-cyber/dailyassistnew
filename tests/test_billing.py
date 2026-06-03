"""Billing helpers (no live Razorpay calls)."""

import os

from aha.billing import PLANS, generate_license_key, public_billing_config


def test_generate_license_key_format():
    key = generate_license_key()
    assert key.startswith("AHA-")
    assert len(key) == 18


def test_public_billing_config_without_secrets():
    os.environ.pop("RAZORPAY_KEY_SECRET", None)
    os.environ.pop("RAZORPAY_KEY_ID", None)
    cfg = public_billing_config()
    assert "key_secret" not in str(cfg)
    assert "plans" in cfg
    assert "core_monthly" in PLANS
