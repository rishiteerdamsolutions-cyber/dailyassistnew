"""
Global configuration for the Behavioral Operating Layer.

Uses pydantic-settings to load configuration from environment variables
and/or a .env file, with sensible defaults for macOS single-tenant operation.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


def _default_chrome_binary() -> str:
    """Return the default Chrome binary path for the current OS."""
    system = platform.system()
    if system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Windows":
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return "/usr/bin/google-chrome"


def _default_tesseract_cmd() -> str:
    """Return the default Tesseract binary path for the current OS."""
    system = platform.system()
    if system == "Darwin":
        # Apple Silicon default; Intel would be /usr/local/bin/tesseract
        return "/opt/homebrew/bin/tesseract"
    return "/usr/bin/tesseract"


class BOLConfig(BaseSettings):
    """Root configuration for the entire BOL system."""

    model_config = {"env_prefix": "BOL_", "env_file": ".env", "extra": "ignore"}

    # ── Paths ────────────────────────────────────────────────────────
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent,
        description="Root directory of the BOL project.",
    )
    data_dir: Path = Field(
        default=Path("data"),
        description="Runtime data directory (relative to project_root).",
    )
    templates_dir: Path = Field(
        default=Path("templates"),
        description="OpenCV template images directory (relative to project_root).",
    )

    # ── Platform ─────────────────────────────────────────────────────
    target_platform: Literal["linkedin", "x.com"] = Field(
        default="linkedin",
        description="Target social media platform.",
    )
    operating_system: Literal["Darwin", "Windows", "Linux"] = Field(
        default_factory=platform.system,
        description="Host operating system (auto-detected).",
    )

    # ── Chrome ───────────────────────────────────────────────────────
    chrome_binary: str = Field(
        default_factory=_default_chrome_binary,
        description="Path to the Google Chrome binary.",
    )
    chrome_profile_dir: str = Field(
        default="Default",
        description="Chrome user profile directory name (e.g., 'Profile 1').",
    )

    # ── Tesseract ────────────────────────────────────────────────────
    tesseract_cmd: str = Field(
        default_factory=_default_tesseract_cmd,
        description="Path to the Tesseract OCR binary.",
    )

    # ── Timing ───────────────────────────────────────────────────────
    timing_pool_size: int = Field(
        default=1000,
        ge=100,
        description="Number of unique latency values per platform timing pool.",
    )

    # ── Visual Cortex ────────────────────────────────────────────────
    template_match_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for OpenCV template matching.",
    )
    ocr_confidence_threshold: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum confidence for pytesseract OCR results.",
    )

    # ── Posting ──────────────────────────────────────────────────────
    posting_hour_start: int = Field(
        default=7,
        ge=0,
        le=23,
        description="Earliest hour (local time) for posting.",
    )
    posting_hour_end: int = Field(
        default=23,
        ge=0,
        le=23,
        description="Latest hour (local time) for posting.",
    )
    posting_peak_start: int = Field(
        default=9,
        ge=0,
        le=23,
        description="Start of peak posting hours.",
    )
    posting_peak_end: int = Field(
        default=20,
        ge=0,
        le=23,
        description="End of peak posting hours.",
    )

    # ── Tenant ───────────────────────────────────────────────────────
    tenant_id: str = Field(
        default="default",
        description="Unique tenant identifier for single-tenant isolation.",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description="Target timezone for calendar and scheduling logic.",
    )

    # ── Derived paths ────────────────────────────────────────────────
    @property
    def resolved_data_dir(self) -> Path:
        """Absolute path to the data directory."""
        if self.data_dir.is_absolute():
            return self.data_dir
        return self.project_root / self.data_dir

    @property
    def resolved_templates_dir(self) -> Path:
        """Absolute path to the templates directory."""
        if self.templates_dir.is_absolute():
            return self.templates_dir
        return self.project_root / self.templates_dir

    @property
    def timing_db_path(self) -> Path:
        """Path to the timing pools SQLite database."""
        return self.resolved_data_dir / "timing_pools" / f"{self.tenant_id}.db"

    @property
    def content_dir(self) -> Path:
        """Path to the content queue directory."""
        return self.resolved_data_dir / "content"

    @property
    def calendar_state_path(self) -> Path:
        """Path to the calendar state file."""
        return self.resolved_data_dir / "calendar" / f"{self.tenant_id}_state.json"

    @property
    def profile_state_path(self) -> Path:
        """Path to the profile state file."""
        return self.resolved_data_dir / "profiles" / f"{self.tenant_id}_profile.json"


# ── Singleton accessor ───────────────────────────────────────────────
_config: BOLConfig | None = None


def get_config() -> BOLConfig:
    """Return the global BOL configuration singleton."""
    global _config
    if _config is None:
        _config = BOLConfig()
    return _config
