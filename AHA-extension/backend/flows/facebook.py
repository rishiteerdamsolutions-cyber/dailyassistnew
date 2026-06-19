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
            steps.extend(["add_media", "click_dropzone", "upload_signal"])

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
                "what's on your mind",
                "write something",
                "create post",
                "post",
                "share",
                "status",
                min_width=20,
                min_height=10,
            )

        elif step == "type_text":
            el = self.role_find(elements, "textbox", min_width=100, min_height=30)
            if el is None:
                el = self.fuzzy_find(
                    elements, 
                    "what's on your mind",
                    "write something",
                    "create post"
                )

        elif step == "add_media":
            el = self.fuzzy_find(
                elements,
                "photo/video",
                "photo",
                "video",
                "add photos",
                "image",
                "media",
                min_width=16,
                min_height=16,
            )

        elif step == "click_dropzone":
            el = self.fuzzy_find(
                elements,
                "add photos/videos",
                "add photos",
                "add video",
                "drag and drop",
                "choose file",
                "browser",
                "upload",
                min_width=40,
                min_height=40,
            )

        elif step == "upload_signal":
            return None

        elif step == "submit_post":
            # For submit, exact matches are safer to avoid clicking "posts" in the feed
            for e in elements:
                text_val = str(e.get("text", "")).lower().strip()
                if text_val in ("post", "next", "publish", "share"):
                    w = float(e.get("width", 0))
                    h = float(e.get("height", 0))
                    if w >= 20 and h >= 10:
                        return self.bbox(e)
            
            # Absolute fallback if exact match fails
            el = self.fuzzy_find(elements, "post", "publish", "share", min_width=20, min_height=10)

        if el is None:
            return None
        return self.bbox(el)
