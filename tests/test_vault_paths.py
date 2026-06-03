"""Vault slot sanitization tests."""

import pytest

from aha.vault_paths import safe_slot_name


def test_safe_slot_accepts_valid_names():
    assert safe_slot_name("My Campaign") == "My Campaign"
    assert safe_slot_name("slot-1_test") == "slot-1_test"


@pytest.mark.parametrize(
    "bad",
    ["../escape", "foo/bar", "..", "  ", "a/b"],
)
def test_safe_slot_rejects_traversal(bad):
    with pytest.raises(ValueError):
        safe_slot_name(bad)
