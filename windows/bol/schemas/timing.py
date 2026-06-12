"""
Timing schemas — Data contracts for Module 1 (Chrono-Entropy & Timing Manager).

Defines the structure of timing pools, individual timing records,
and configuration for platform-specific latency generation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TimingAction(str, Enum):
    """Categories of timed actions within a workflow."""

    PRE_CLICK = "pre_click"
    POST_CLICK = "post_click"
    PRE_SCROLL = "pre_scroll"
    POST_SCROLL = "post_scroll"
    PRE_TYPE = "pre_type"
    POST_TYPE = "post_type"
    NAVIGATION_WAIT = "navigation_wait"
    ELEMENT_SCAN = "element_scan"
    IDLE_PAUSE = "idle_pause"
    TRANSITION = "transition"


class TimingConfig(BaseModel):
    """Configuration for a platform-specific timing pool."""

    model_config = {"frozen": True}

    platform: str = Field(description="Target platform identifier (e.g., 'linkedin').")
    pool_size: int = Field(default=1000, ge=100, le=10000, description="Number of unique latency values in the pool.")
    min_latency_ms: float = Field(default=200.0, ge=50.0, description="Minimum latency in milliseconds.")
    max_latency_ms: float = Field(default=4500.0, le=15000.0, description="Maximum latency in milliseconds.")
    distribution_alpha: float = Field(default=2.0, ge=0.5, description="Beta distribution alpha parameter (shapes the curve).")
    distribution_beta: float = Field(default=5.0, ge=0.5, description="Beta distribution beta parameter (shapes the curve).")


class TimingRecord(BaseModel):
    """A single timing value within a depletion pool."""

    record_id: int = Field(description="Unique record identifier within the pool.")
    platform: str = Field(description="Platform this timing value belongs to.")
    value_ms: float = Field(description="The latency value in milliseconds (continuous decimal).")
    consumed: bool = Field(default=False, description="Whether this value has been used.")
    consumed_at: datetime | None = Field(default=None, description="Timestamp when this value was consumed.")
    cycle_id: int = Field(default=0, ge=0, description="The depletion cycle this record belongs to.")


class TimingPoolStatus(BaseModel):
    """Current status of a platform timing pool."""

    platform: str
    pool_size: int
    consumed_count: int
    remaining_count: int
    cycle_id: int
    exhaustion_percentage: float = Field(ge=0.0, le=100.0)

    @property
    def is_exhausted(self) -> bool:
        """Check if all values in the current cycle have been consumed."""
        return self.remaining_count == 0
