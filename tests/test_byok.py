"""BYOK resolution and API key response shape."""

from unittest.mock import patch

from bol.config import BOLConfig

from aha.byok import (
    apply_byok_to_config,
    canonical_provider,
    resolve_gemini_api_key,
    tier2_api_key_missing_message,
)
from aha.license import get_api_keys, set_api_key, delete_api_key


def test_canonical_provider_aliases():
    assert canonical_provider("google") == "google"
    assert canonical_provider("gemini") == "google"
    assert canonical_provider("openai") == "openai"


def test_get_api_keys_nested_shape():
    with patch("aha.license.load_config", return_value={"api_keys": {"google": "sk-test-key-12345678"}}):
        out = get_api_keys()
    assert "api_keys" in out
    assert "google" in out["api_keys"]
    assert "..." in out["api_keys"]["google"]


def test_resolve_gemini_prefers_byok_over_env():
    config = BOLConfig(gemini_api_key="env-key")
    with patch("aha.byok.get_raw_api_key", return_value="byok-key"):
        assert resolve_gemini_api_key(config) == "byok-key"


def test_apply_byok_to_config():
    config = BOLConfig(gemini_api_key="env-g", openai_api_key=None)

    def side(provider):
        if provider in ("google", "gemini"):
            return "g-byok"
        if provider == "openai":
            return "o-byok"
        return None

    with patch("aha.byok.get_raw_api_key", side_effect=side):
        apply_byok_to_config(config)
    assert config.gemini_api_key == "g-byok"
    assert config.openai_api_key == "o-byok"


def test_tier2_missing_message_when_no_keys():
    config = BOLConfig(gemini_api_key=None, openai_api_key=None)
    with patch("aha.byok.genai", object()):
        msg = tier2_api_key_missing_message(config, use_openai=False)
    assert msg is not None
    assert "Settings" in msg


def test_set_api_key_canonical_storage(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("aha.license.CONFIG_FILE", cfg_file)
    monkeypatch.setattr("aha.license.ensure_aha_dir", lambda: None)
    result = set_api_key("gemini", "secret-gemini-key-value")
    assert result["success"]
    assert result["provider"] == "google"
    delete_api_key("google")
