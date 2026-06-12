"""
Visual schemas — Data contracts for Module 3 (Visual Cortex Engine).

Defines screen capture regions, template matching results,
OCR results, and bounding boxes.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScreenRegion(BaseModel):
    """A rectangular region of the screen to capture."""

    model_config = {"frozen": True}

    monitor_index: int = Field(default=1, ge=0, description="Monitor index (0=all, 1=primary).")
    left: int = Field(ge=0, description="Left edge X coordinate.")
    top: int = Field(ge=0, description="Top edge Y coordinate.")
    width: int = Field(gt=0, description="Region width in pixels.")
    height: int = Field(gt=0, description="Region height in pixels.")

    def to_mss_dict(self) -> dict[str, int]:
        """Convert to the dict format expected by mss.grab()."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


class ScreenCapture(BaseModel):
    """Metadata for a captured screen frame (image data held externally)."""

    model_config = {"arbitrary_types_allowed": True}

    capture_id: str = Field(description="Unique identifier for this capture.")
    region: ScreenRegion = Field(description="The region that was captured.")
    timestamp: datetime = Field(default_factory=datetime.now)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class BoundingBox(BaseModel):
    """A rectangular bounding box on the screen."""

    x: int = Field(ge=0, description="Left edge X coordinate.")
    y: int = Field(ge=0, description="Top edge Y coordinate.")
    width: int = Field(gt=0, description="Box width in pixels.")
    height: int = Field(gt=0, description="Box height in pixels.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Detection confidence score.")

    @property
    def center_x(self) -> int:
        """Exact center X coordinate."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Exact center Y coordinate."""
        return self.y + self.height // 2

    @property
    def right(self) -> int:
        """Right edge X coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge Y coordinate."""
        return self.y + self.height


class TemplateMatch(BaseModel):
    """Result of an OpenCV template matching operation."""

    template_name: str = Field(description="Name of the template that matched.")
    bounding_box: BoundingBox = Field(description="Location and size of the match.")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence (0-1).")
    scale: float = Field(default=1.0, gt=0, description="Scale at which the template matched.")


class OCRWord(BaseModel):
    """A single word extracted by OCR with its bounding box."""

    text: str = Field(description="The recognized text.")
    bounding_box: BoundingBox = Field(description="Bounding box around the word.")
    confidence: int = Field(ge=0, le=100, description="OCR confidence (0-100).")


class OCRResult(BaseModel):
    """Complete OCR extraction result from a screen region."""

    words: list[OCRWord] = Field(default_factory=list, description="All recognized words.")
    full_text: str = Field(default="", description="Concatenated full text.")
    capture_id: str = Field(default="", description="ID of the source screen capture.")

    def find_text(self, target: str) -> list[BoundingBox]:
        """Find all bounding boxes containing the target text (case-insensitive)."""
        results: list[BoundingBox] = []
        target_lower = target.lower()
        # Single-word match
        for word in self.words:
            if target_lower in word.text.lower():
                results.append(word.bounding_box)
        return results
