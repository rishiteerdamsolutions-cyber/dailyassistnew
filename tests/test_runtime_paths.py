"""Retail build guards — dev license bypass must not work in customer builds."""

import os

from aha.runtime_paths import bundle_root, is_frozen, is_retail_build, repo_root
from aha.subscription import allow_dev_license_keys


def test_is_retail_build_when_env_set(monkeypatch):
    monkeypatch.delenv("AHA_RETAIL_BUILD", raising=False)
    assert is_retail_build() is False
    monkeypatch.setenv("AHA_RETAIL_BUILD", "1")
    assert is_retail_build() is True


def test_allow_dev_license_disabled_in_retail(monkeypatch):
    monkeypatch.setenv("AHA_ALLOW_DEV_LICENSE", "1")
    monkeypatch.setenv("AHA_RETAIL_BUILD", "1")
    assert allow_dev_license_keys() is False


def test_allow_dev_license_enabled_in_dev_checkout(monkeypatch):
    monkeypatch.delenv("AHA_RETAIL_BUILD", raising=False)
    monkeypatch.setenv("AHA_ALLOW_DEV_LICENSE", "1")
    assert allow_dev_license_keys() is True


def test_is_frozen_false_in_tests():
    assert is_frozen() is False


def test_repo_root_has_visionbuttons_in_dev():
    root = repo_root()
    assert (root / "VISIONBUTTONS").is_dir()


def test_bundle_root_is_dev_tree_in_tests():
    root = bundle_root()
    assert root.is_dir()
