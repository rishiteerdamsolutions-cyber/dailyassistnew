"""
flows/x.py — X (formerly Twitter) posting flow.

Supports:
  text-only   : slots = {"text": "...", "image": False, "video": False}
  image tweet : slots = {"image": True, ...}
  video tweet : slots = {"video": True, ...}

X desktop posting flow:
  1. Click the "Post" compose button in the sidebar (or "What's happening?" area)
  2. Type text into the compose box
  3. Click the media (image/GIF/video) icon if media slot is filled
  4. Upload signal — OS file picker
  5. Click "Post" button to publish
"""

from __future__ import annotations

from typing import Optional

from flows.base import Element, SocialFlow


class XFlow(SocialFlow):

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
                "what is happening",
                "what's happening",
                min_width=20,
                min_height=10,
            )

        elif step == "type_text":
            el = self.role_find(elements, "textbox", min_width=100, min_height=30)
            if el is None:
                el = self.fuzzy_find(
                    elements, 
                    "what is happening",
                    "what's happening"
                )

        elif step == "add_media":
            el = self.fuzzy_find(
                elements,
                "media",
                min_width=16,
                min_height=16,
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
            # Prefer the button role to avoid matching the textarea placeholder
            if el and el.get("role", "").lower() != "button":
                fallback = self.role_find(elements, "button", "post")
                if fallback:
                    el = fallback

        if el is None:
            return None
        return self.bbox(el)
