"""
flows/linkedin.py — LinkedIn posting flow.

Supports four post variants driven by the `slots` dict:
  text-only   : slots = {"text": "...", "image": False, "video": False}
  image-only  : slots = {"text": "",   "image": True,  "video": False}
  text+image  : slots = {"text": "...", "image": True,  "video": False}
  video       : slots = {"text": "...", "image": False, "video": True}

Steps emitted:
  open_composer   → click "Start a post" / "Write a post" prompt
  type_text       → type text content into the modal textarea
  open_media      → click the camera / photo icon (image variant)
  upload_signal   → signal extension to open OS file picker (handled externally)
  open_video      → click the video icon (video variant)
  submit_post     → click the "Post" button
"""

from __future__ import annotations

from typing import Optional

from flows.base import Element, SocialFlow


class LinkedInFlow(SocialFlow):
    """Deterministic LinkedIn post flow with fuzzy element matching."""

    def get_steps(self) -> list[str]:
        steps: list[str] = ["open_composer"]

        has_text = bool(self.slots.get("text", "").strip())
        has_image = bool(self.slots.get("image", False))
        has_video = bool(self.slots.get("video", False))

        if has_text:
            steps.append("type_text")
        
        if has_image:
            steps.extend(["open_media", "upload_signal", "next_step"])
        elif has_video:
            steps.extend(["open_video", "upload_signal", "next_step"])

        steps.append("submit_post")
        return steps

    def find_target(
        self,
        elements: list[Element],
        step: str,
    ) -> Optional[tuple[float, float, float, float]]:
        el = None

        if step == "open_composer":
            el = self.fuzzy_find(
                elements,
                "start a post",
                min_width=20,
                min_height=10,
            )

        elif step == "type_text":
            el = self.role_find(elements, "textbox", min_width=50, min_height=10)
            if el is None:
                el = self.fuzzy_find(
                    elements, 
                    "start a post",
                    min_width=50,
                    min_height=10
                )

        elif step == "open_media":
            el = self.fuzzy_find(
                elements,
                "photo",
                "image",
                min_width=16,
                min_height=16,
            )

        elif step == "open_video":
            el = self.fuzzy_find(
                elements,
                "video",
                min_width=16,
                min_height=16,
            )

        elif step == "upload_signal":
            return None

        elif step == "next_step":
            el = self.fuzzy_find(
                elements,
                "next",
                min_width=20,
                min_height=10,
            )

        elif step == "submit_post":
            el = self.fuzzy_find(
                elements,
                "post",
                min_width=20,
                min_height=10,
            )
            # Avoid matching the "Start a post" area by preferring buttons
            if el and "start" in str(el.get("text", "")).lower():
                # Re-search skipping that hit
                filtered = [
                    e for e in elements
                    if "start" not in str(e.get("text", "")).lower()
                ]
                el = self.fuzzy_find(filtered, "post", min_width=20, min_height=10)

        if el is None:
            return None
        return self.bbox(el)
