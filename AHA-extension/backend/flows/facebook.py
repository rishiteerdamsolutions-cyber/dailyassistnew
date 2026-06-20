"""
flows/facebook.py — Facebook posting flow.

Supports:
  text-only   : slots = {"text": "...", "image": False, "video": False}
  photo post  : slots = {"image": True, ...}
  video post  : slots = {"video": True, ...}

Desktop Facebook posting flow:
  1. Click "What's on your mind?" composer prompt
  2. Type text (if text slot filled)
  3. Click "Photo/video" button in composer (if media slot filled)
  4. Upload signal — OS file picker
  5. Click "Post" to publish
"""

from __future__ import annotations

from typing import Optional

from flows.base import Element, SocialFlow


class FacebookFlow(SocialFlow):

    def get_steps(self) -> list[str]:
        steps: list[str] = ["open_composer"]

        has_text = bool(self.slots.get("text", "").strip())
        has_image = bool(self.slots.get("image", False))
        has_video = bool(self.slots.get("video", False))

        if has_text:
            steps.append("type_text")
        if has_image or has_video:
            steps.extend(["add_media", "upload_signal"])

        steps.append("submit_post")
        steps.append("close_modal")
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
                "what's on your mind",
                min_width=20,
                min_height=10,
            )

        elif step == "type_text":
            el = self.role_find(elements, "textbox", min_width=50, min_height=10)
            if el is None:
                el = self.fuzzy_find(
                    elements, 
                    "what's on your mind",
                    min_width=50,
                    min_height=10
                )

        elif step == "add_media":
            el = self.fuzzy_find(
                elements,
                "photo/video",
                "add photos or videos",
                min_width=10,
                min_height=10,
            )

        elif step == "upload_signal":
            return None

        elif step == "submit_post":
            el = self.fuzzy_find(
                elements,
                "post",
                min_width=20,
                min_height=10,
            )

        elif step == "close_modal":
            el = self.fuzzy_find(
                elements,
                "close",
                "x",
                min_width=10,
                min_height=10,
            )
            if el is None:
                el = self.role_find(elements, "button", "close")

        if el is None:
            return None
        return self.bbox(el)
