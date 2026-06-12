"""
Bridge schemas — Data contracts for Module 6 (Native OS Accessibility Bridge).

Defines input commands, hardware jitter snapshots,
and click event structures.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class InputCommandType(str, Enum):
    """Types of low-level OS input commands."""

    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    KEY_PRESS = "key_press"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    TYPE_CHAR = "type_char"


class MouseButton(str, Enum):
    """Mouse button identifiers."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class InputCommand(BaseModel):
    """A generic low-level OS input command."""

    command_type: InputCommandType
    x: float | None = Field(default=None, description="Target X coordinate (for mouse commands).")
    y: float | None = Field(default=None, description="Target Y coordinate (for mouse commands).")
    button: MouseButton = Field(default=MouseButton.LEFT, description="Mouse button (for click commands).")
    key: str | None = Field(default=None, description="Key name (for keyboard commands).")
    keys: list[str] | None = Field(default=None, description="Key sequence (for hotkey commands).")
    character: str | None = Field(default=None, description="Character to type (for type_char).")
    scroll_clicks: int = Field(default=0, description="Number of scroll clicks (for scroll).")
    duration_ms: float = Field(default=0, ge=0, description="Movement/action duration in ms.")


class HardwareSnapshot(BaseModel):
    """Snapshot of the host machine's hardware performance at a point in time."""

    cpu_percent: float = Field(ge=0.0, le=100.0, description="Current CPU utilization percentage.")
    ram_percent: float = Field(ge=0.0, le=100.0, description="Current RAM utilization percentage.")
    timestamp: datetime = Field(default_factory=datetime.now)


class HardwareJitter(BaseModel):
    """Computed micro-delay based on current hardware load."""

    snapshot: HardwareSnapshot
    computed_delay_ms: float = Field(
        ge=0.0,
        description="Additional delay in ms to anchor to hardware performance.",
    )
    cpu_component_ms: float = Field(ge=0.0, description="Delay component from CPU load.")
    ram_component_ms: float = Field(ge=0.0, description="Delay component from RAM load.")


class ClickEvent(BaseModel):
    """A fully resolved click event ready for OS injection."""

    target_x: int = Field(ge=0, description="Final click X coordinate.")
    target_y: int = Field(ge=0, description="Final click Y coordinate.")
    button: MouseButton = Field(default=MouseButton.LEFT)
    pre_click_jitter: HardwareJitter | None = Field(
        default=None,
        description="Hardware jitter applied before the click.",
    )
    pre_click_delay_ms: float = Field(ge=0, description="Total pre-click delay including jitter.")
