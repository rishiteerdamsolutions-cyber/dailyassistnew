"""
AHA License Validation & BYOK API Key Management.

Phase 1: Local-only license validation.
Stores license state in ~/.aha/license.json and API keys in ~/.aha/config.json.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

AHA_DIR = Path.home() / ".aha"
LICENSE_FILE = AHA_DIR / "license.json"
CONFIG_FILE = AHA_DIR / "config.json"

OFFLINE_GRACE_HOURS = 48
RECHECK_HOURS = 6

# ===========================================================================
# 1. License Management
# ===========================================================================


def ensure_aha_dir() -> None:
    """Create ~/.aha/ if it doesn't already exist."""
    try:
        AHA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # Non-fatal: subsequent reads/writes will fail gracefully on their own.
        print(f"[aha] Warning: could not create {AHA_DIR}: {exc}")


def load_license() -> dict:
    """Read the license file and return its contents (or empty dict)."""
    try:
        return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_license(data: dict) -> None:
    """Persist *data* to the license file."""
    try:
        ensure_aha_dir()
        LICENSE_FILE.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[aha] Warning: could not write license file: {exc}")


def validate_license(license_key: str) -> dict:
    """Validate a license key and persist the result.

    # TODO: Replace with remote license server validation in production.
    Phase 1 uses LOCAL-ONLY validation: any key matching the format
    ``AHA-XXXX-XXXX-XXXX`` (19 chars, starting with "AHA-") is accepted.
    """

    now_iso = datetime.now(timezone.utc).isoformat()

    # --- Local-only validation (Phase 1) ---
    if license_key.startswith("AHA-") and len(license_key) == 18:
        result = {
            "valid": True,
            "plan": "pro",
            "expires": "2099-12-31",
            "reason": None,
        }
    else:
        result = {
            "valid": False,
            "plan": None,
            "expires": None,
            "reason": "invalid_key",
        }

    # Persist alongside a timestamp so we can cache / grace-period later.
    license_data = {
        **result,
        "license_key": license_key,
        "last_validated": now_iso,
    }
    save_license(license_data)

    return result


def check_license_status() -> dict:
    """Return the current license status, re-validating if stale.

    * No license on disk → ``{"valid": False, "reason": "no_license"}``
    * Validated within ``RECHECK_HOURS`` → cached result
    * Stale → re-validate via :func:`validate_license`
    * Re-validation fails (network, etc.) but within ``OFFLINE_GRACE_HOURS``
      → cached **valid** result (offline grace)
    """

    data = load_license()

    if not data or "license_key" not in data:
        return {"valid": False, "reason": "no_license"}

    last_validated_str = data.get("last_validated")
    if last_validated_str:
        try:
            last_ts = datetime.fromisoformat(last_validated_str)
            age_hours = (
                datetime.now(timezone.utc) - last_ts
            ).total_seconds() / 3600.0

            # Still fresh – return cached result.
            if age_hours < RECHECK_HOURS:
                return {
                    "valid": data.get("valid", False),
                    "plan": data.get("plan"),
                    "expires": data.get("expires"),
                    "reason": data.get("reason"),
                }

            # Stale – attempt re-validation.
            try:
                return validate_license(data["license_key"])
            except Exception:
                # Re-validation failed (e.g. network error in a future
                # remote-check implementation).  Allow offline grace.
                if age_hours < OFFLINE_GRACE_HOURS and data.get("valid"):
                    return {
                        "valid": True,
                        "plan": data.get("plan"),
                        "expires": data.get("expires"),
                        "reason": "offline_grace",
                    }
                return {
                    "valid": False,
                    "reason": "revalidation_failed",
                }
        except (ValueError, TypeError):
            pass  # Malformed timestamp – fall through to re-validate.

    # No usable timestamp – try a fresh validation.
    try:
        return validate_license(data["license_key"])
    except Exception:
        return {"valid": False, "reason": "revalidation_failed"}


def activate_license(license_key: str) -> dict:
    """Validate and, if valid, persist the license."""
    result = validate_license(license_key)
    # validate_license already saves on success; nothing extra needed.
    return result


# ===========================================================================
# 2. API Key Management (BYOK)
# ===========================================================================

_DEFAULT_CONFIG: dict = {"api_keys": {}}


def load_config() -> dict:
    """Read the config file; return sensible defaults on any error."""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Ensure the expected top-level key exists.
        if "api_keys" not in data:
            data["api_keys"] = {}
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(_DEFAULT_CONFIG)


def save_config(data: dict) -> None:
    """Persist *data* to the config file."""
    try:
        ensure_aha_dir()
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[aha] Warning: could not write config file: {exc}")


def _mask_key(key: str) -> str:
    """Return a masked representation of an API key.

    * Keys longer than 8 chars → first 4 + "..." + last 4
    * Shorter keys → "****"
    """
    if len(key) > 8:
        return f"{key[:4]}...{key[-4:]}"
    return "****"


def set_api_key(provider: str, api_key: str) -> dict:
    """Store an API key for *provider*."""
    try:
        config = load_config()
        config["api_keys"][provider] = api_key
        save_config(config)
        return {"success": True, "provider": provider}
    except Exception as exc:
        return {"success": False, "provider": provider, "error": str(exc)}


def get_api_keys() -> dict:
    """Return all stored API keys with values masked."""
    config = load_config()
    return {
        provider: _mask_key(key)
        for provider, key in config.get("api_keys", {}).items()
    }


def delete_api_key(provider: str) -> dict:
    """Remove the API key for *provider*."""
    try:
        config = load_config()
        config.get("api_keys", {}).pop(provider, None)
        save_config(config)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_raw_api_key(provider: str):
    """Return the actual (unmasked) API key for internal use, or ``None``."""
    config = load_config()
    return config.get("api_keys", {}).get(provider)
