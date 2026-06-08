"""
BYOK resolution: Companion-stored keys (~/.aha/config.json) with .env fallback.
"""

from __future__ import annotations

from bol.config import BOLConfig

from aha.license import get_raw_api_key

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Settings UI uses "google"; env uses BOL_GEMINI_API_KEY on gemini_api_key field.
_GEMINI_STORE_ALIASES = ("google", "gemini")


def canonical_provider(provider: str) -> str:
    """Normalize provider id for storage and lookup."""
    p = (provider or "").strip().lower()
    if p in _GEMINI_STORE_ALIASES:
        return "google"
    if p == "openai":
        return "openai"
    return p


def resolve_gemini_api_key(config: BOLConfig) -> str | None:
    """BYOK file first, then BOLConfig / .env."""
    for name in _GEMINI_STORE_ALIASES:
        key = get_raw_api_key(name)
        if key:
            return key
    return config.gemini_api_key


def resolve_openai_api_key(config: BOLConfig) -> str | None:
    key = get_raw_api_key("openai")
    if key:
        return key
    return config.openai_api_key


def apply_byok_to_config(config: BOLConfig) -> None:
    """Overlay resolved BYOK keys onto the live config object."""
    gemini = resolve_gemini_api_key(config)
    openai = resolve_openai_api_key(config)
    if gemini:
        config.gemini_api_key = gemini
    if openai:
        config.openai_api_key = openai


def tier2_api_key_missing_message(config: BOLConfig, *, use_openai: bool) -> str | None:
    """
    Return a user-facing message if Tier-2 LLM cannot run, else None.
    Call after apply_byok_to_config().
    """
    if use_openai:
        if config.openai_api_key:
            return None
        if config.gemini_api_key and genai is not None:
            return None
    else:
        if config.gemini_api_key and genai is not None:
            return None

    if genai is None:
        return (
            "Tier-2 assistance requires the google-generativeai package. "
            "Install project dependencies and try again."
        )

    return (
        "Tier-2 assistance needs your API key. Open Settings (gear icon in chat), "
        "select Google Gemini or OpenAI, save your key, then try again. "
        "You can also set BOL_GEMINI_API_KEY or BOL_OPENAI_API_KEY in a .env file."
    )
