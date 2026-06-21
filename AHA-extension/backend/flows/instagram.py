"""
flows/instagram.py — Instagram posting flow.

Supports:
  text caption    : slots = {"text": "...", "image": False, "video": False}
  image post      : slots = {"image": True, ...}
  video/reel      : slots = {"video": True, ...}

Typical Instagram desktop posting flow:
  1. Click the "New post" / "+" / "Create" button in the nav
  2. Upload signal — OS file picker for image/video
  3. Click "Next" to advance through crop/filter steps (up to 2× for filters)
  4. Type caption in the caption textarea
  5. Click "Share" to publish

Note: Instagram uses aria-label extensively instead of visible text;
      both text and aria-label searches are attempted.
"""

from __future__ import annotations

from typing import Optional

from flows.base import Element, SocialFlow


class InstagramFlow(SocialFlow):

    def get_steps(self) -> list[str]:
        steps: list[str] = ["open_new_post"]

        has_image = bool(self.slots.get("image", False))
        has_video = bool(self.slots.get("video", False))
        has_text = bool(self.slots.get("text", "").strip())

        if has_image or has_video:
            steps.append("select_from_computer")
            steps.append("upload_signal")
            steps.append("next_step")    # crop panel → filter panel
            steps.append("next_step")    # filter panel → caption panel

        if has_text:
            steps.append("type_caption")

        steps.append("share_post")
        return steps

    def find_target(
        self,
        elements: list[Element],
        step: str,
    ) -> Optional[tuple[float, float, float, float]]:
        el = None

        if step == "open_new_post":
            el = self.fuzzy_find(
                elements,
                "create",
                "new post",
                min_width=10,
                min_height=10,
            )
            if el is None:
                el = self.role_find(elements, "button", "new post")
            if el is None:
                el = self.role_find(elements, "link", "new post")
            if el is None:
                el = self.role_find(elements, "menuitem", "new post")

        elif step == "select_from_computer":
            el = self.fuzzy_find(
                elements,
                "select from computer",
                min_width=20,
                min_height=10,
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

        elif step == "type_caption":
            el = self.role_find(elements, "textbox", min_width=50, min_height=20)
            if el is None:
                el = self.fuzzy_find(
                    elements,
                    "write a caption",
                )

        elif step == "share_post":
            el = self.fuzzy_find(
                elements,
                "share",
                min_width=20,
                min_height=10,
            )

        if el is None:
            return None
        return self.bbox(el)
