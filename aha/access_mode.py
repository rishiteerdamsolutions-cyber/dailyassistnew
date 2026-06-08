"""BYOK vs Direct Access — internal product modes (not marketing copy)."""

from __future__ import annotations

from bol.config import BOLConfig, get_config

from aha.byok import resolve_gemini_api_key, resolve_openai_api_key


def has_byok_key(config: BOLConfig | None = None) -> bool:
    cfg = config or get_config()
    return bool(resolve_gemini_api_key(cfg) or resolve_openai_api_key(cfg))


def byok_required_message() -> str:
    return (
        "Caption generation uses your own API key. Open Settings, add your Gemini key, "
        "then try again."
    )
