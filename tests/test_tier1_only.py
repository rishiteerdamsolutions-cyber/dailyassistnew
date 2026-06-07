"""Tier-1-only product mode."""

import os
from unittest.mock import patch

from aha.product_mode import TIER1_ONLY_HELP, product_mode_payload, tier1_only_mode


def test_tier1_only_default_off_in_dev():
    with patch.dict(os.environ, {"AHA_TIER1_ONLY": "", "AHA_RETAIL_BUILD": ""}, clear=False):
        with patch("aha.runtime_paths.is_retail_build", return_value=False):
            assert tier1_only_mode() is False


def test_tier1_only_env_on():
    with patch.dict(os.environ, {"AHA_TIER1_ONLY": "1"}, clear=False):
        assert tier1_only_mode() is True


def test_tier1_only_env_off_overrides_retail():
    with patch.dict(os.environ, {"AHA_TIER1_ONLY": "0", "AHA_RETAIL_BUILD": "1"}, clear=False):
        assert tier1_only_mode() is False


def test_tier1_only_retail_default():
    with patch.dict(os.environ, {"AHA_TIER1_ONLY": ""}, clear=False):
        with patch("aha.runtime_paths.is_retail_build", return_value=True):
            assert tier1_only_mode() is True


def test_product_mode_payload():
    with patch("aha.product_mode.tier1_only_mode", return_value=True):
        payload = product_mode_payload()
    assert payload["tier1_only"] is True
    assert payload["tier2_enabled"] is False
    assert "Tier-1" in payload["label"]


def test_tier1_help_mentions_social():
    assert "Instagram" in TIER1_ONLY_HELP
    assert "git" in TIER1_ONLY_HELP
