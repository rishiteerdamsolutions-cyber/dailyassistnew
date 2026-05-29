"""
Kinematic schemas — Data contracts for Module 2 (Kinematic Motion Synthesizer).

Defines Bezier control points, trajectory paths, scroll profiles,
and cursor targeting structures.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """A 2D coordinate point on the screen."""

    model_config = {"frozen": True}

    x: float = Field(description="Horizontal pixel coordinate.")
    y: float = Field(description="Vertical pixel coordinate.")

    def distance_to(self, other: Point2D) -> float:
        """Euclidean distance to another point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class BezierControlPoints(BaseModel):
    """Four control points defining a cubic Bezier curve."""

    model_config = {"frozen": True}

    p0: Point2D = Field(description="Start point (current cursor position).")
    p1: Point2D = Field(description="First control point (influences departure angle).")
    p2: Point2D = Field(description="Second control point (influences arrival angle).")
    p3: Point2D = Field(description="End point (target position).")


class BezierPath(BaseModel):
    """A complete Bezier trajectory with sampled points and timing."""

    control_points: BezierControlPoints
    trajectory_points: list[Point2D] = Field(description="Sampled (x, y) positions along the curve.")
    total_duration_ms: float = Field(gt=0, description="Total movement duration in milliseconds.")
    num_steps: int = Field(gt=0, description="Number of discrete steps in the trajectory.")
    includes_overshoot: bool = Field(default=False, description="Whether overshoot correction is applied.")


class ScrollDirection(str, Enum):
    """Direction of a viewport scroll event."""

    UP = "up"
    DOWN = "down"


class MicroStutter(BaseModel):
    """A micro-pause injected during scrolling to simulate reading."""

    step_index: int = Field(ge=0, description="At which scroll step to pause.")
    pause_ms: float = Field(gt=0, description="Duration of the pause in milliseconds.")


class ScrollProfile(BaseModel):
    """A complete scroll operation profile with physics parameters."""

    direction: ScrollDirection
    total_distance_px: int = Field(gt=0, description="Total scroll distance in pixels.")
    num_steps: int = Field(gt=0, description="Number of discrete scroll steps.")
    step_delays_ms: list[float] = Field(description="Per-step delay in ms (sinusoidal velocity profile).")
    micro_stutters: list[MicroStutter] = Field(default_factory=list, description="Injected reading pauses.")
    total_duration_ms: float = Field(gt=0, description="Total scroll duration including stutters.")


class CursorTarget(BaseModel):
    """A computed click target with off-center offset applied."""

    bounding_box_x: int = Field(ge=0)
    bounding_box_y: int = Field(ge=0)
    bounding_box_width: int = Field(gt=0)
    bounding_box_height: int = Field(gt=0)
    click_x: int = Field(ge=0, description="Computed off-center click X coordinate.")
    click_y: int = Field(ge=0, description="Computed off-center click Y coordinate.")
    offset_from_center_x: int = Field(description="Pixel offset from bounding box center (X).")
    offset_from_center_y: int = Field(description="Pixel offset from bounding box center (Y).")
