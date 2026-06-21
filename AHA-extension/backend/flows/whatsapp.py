"""
flows/whatsapp.py — WhatsApp Status posting flow.

Supports WhatsApp Web status posting:
  1. Click Status icon
  2. Click "+" (New Status) icon
  3. Click "Photos & videos"
  4. Upload signal — OS file picker
  5. Type caption
  6. Click Send
"""

from __future__ import annotations

from typing import Optional

from flows.base import Element, SocialFlow


class WhatsAppFlow(SocialFlow):

    def get_steps(self) -> list[str]:
        steps: list[str] = ["open_status"]
        
        has_text = bool(self.slots.get("text", "").strip())
        has_media = bool(self.slots.get("image", False)) or bool(self.slots.get("video", False))

        if has_media:
            steps.extend(["click_add_status", "select_photos_videos", "upload_signal"])
            
        if has_text:
            steps.append("type_caption")

        steps.append("submit_status")
        return steps

    def find_target(
        self,
        elements: list[Element],
        step: str,
    ) -> Optional[tuple[float, float, float, float]]:
        el = None

        if step == "open_status":
            el = self.fuzzy_find(
                elements,
                "status",
                min_width=20,
                min_height=10,
            )

        elif step == "click_add_status":
            el = self.fuzzy_find(
                elements,
                "new status",
                min_width=16,
                min_height=16,
            )
            if el is None:
                el = self.role_find(elements, "button", "status")

        elif step == "select_photos_videos":
            el = self.fuzzy_find(
                elements,
                "photos & videos",
                min_width=20,
                min_height=10,
            )

        elif step == "upload_signal":
            return None

        elif step == "type_caption":
            el = self.fuzzy_find(
                elements,
                "type a caption",
                min_width=50,
                min_height=10,
                boost_clickable=False
            )

        elif step == "submit_status":
            el = self.fuzzy_find(
                elements,
                "send",
                min_width=20,
                min_height=10,
            )
            if el is None:
                el = self.role_find(elements, "button", "send")

        if el is None:
            return None
        return self.bbox(el)
