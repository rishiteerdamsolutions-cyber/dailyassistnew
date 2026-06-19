"""
flows/base.py — Abstract base class for all social media posting flows.

Every platform flow (LinkedIn, Instagram, Facebook, X, WhatsApp) inherits
from SocialFlow and implements:
  - get_steps()    → ordered list of step names for the chosen post variant
  - find_target()  → locate the element for a given step in the element list

Element dicts supplied by the Chrome Extension have the shape:
  {
    "text":   str,   # Visible text of the element (may be empty for icons)
    "x":      float, # Left edge of bounding box (viewport pixels)
    "y":      float, # Top edge of bounding box (viewport pixels)
    "width":  float, # Element width in pixels
    "height": float, # Element height in pixels
    "tag":    str,   # Optional — HTML tag hint ("button", "input", etc.)
    "role":   str,   # Optional — ARIA role hint
  }
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


# Type alias for the element dict supplied by the extension
Element = dict


class SocialFlow(ABC):
    """
    Abstract base for all platform posting flows.

    Concrete subclasses define the ordered steps and how to locate each
    step's target element in the current page element list.
    """

    def __init__(self, slots: dict) -> None:
        """
        Parameters
        ----------
        slots
            Post content slots from the extension, e.g.:
              {"text": "Hello world!", "image": True, "video": False}
        """
        self.slots = slots

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def get_steps(self) -> list[str]:
        """
        Return the ordered list of step names for the active post variant.

        Step names are arbitrary strings understood by find_target().
        The WebSocket handler iterates through them sequentially.

        Example return:
            ["open_composer", "type_text", "add_image", "submit_post"]
        """

    @abstractmethod
    def find_target(
        self,
        elements: list[Element],
        step: str,
    ) -> Optional[tuple[float, float, float, float]]:
        """
        Find the element for a given step and return its bounding box.

        Parameters
        ----------
        elements
            Current page element snapshot from the Chrome Extension.
        step
            Step name from get_steps().

        Returns
        -------
        (x, y, width, height)  — bounding box of the target element, or
        None                   — if the element cannot be found.
        """

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def fuzzy_find(
        elements: list[Element],
        *queries: str,
        min_width: float = 0.0,
        min_height: float = 0.0,
    ) -> Optional[Element]:
        """
        Case-insensitive search across element text.
        Finds the absolute BEST match across all elements, penalizing extra text.
        """
        import re
        from difflib import SequenceMatcher

        best_element = None
        best_score = 0.0

        for query in queries:
            q = re.sub(r'[^a-z0-9]', '', query.lower())
            if not q: continue

            for el in elements:
                w = float(el.get("width", 0))
                h = float(el.get("height", 0))
                if w < min_width or h < min_height:
                    continue

                el_text = re.sub(r'[^a-z0-9]', '', str(el.get("text", "")).lower())
                if not el_text: continue
                
                score = 0.0
                if q == el_text:
                    score = 1.0
                elif q in el_text:
                    # It's a substring. Score based on how much of the string it occupies
                    # e.g. "post" in "post" = 1.0, "post" in "createpost" = 0.4
                    score = 0.8 * (len(q) / len(el_text))
                else:
                    ratio = SequenceMatcher(None, q, el_text).ratio()
                    if ratio >= 0.8:
                        score = ratio * 0.7 # Penalize fuzzy matching

                if score > best_score:
                    best_score = score
                    best_element = el

            # If we found an excellent match (>0.85) for this query, stop searching
            if best_score > 0.85:
                break

        if best_score > 0.5: # Require at least a 50% confidence match
            return best_element
        return None

    @staticmethod
    @staticmethod
    def role_find(
        elements: list[Element],
        role: str,
        text_hint: str = "",
        min_width: float = 0.0,
        min_height: float = 0.0,
    ) -> Optional[Element]:
        role_lower = role.lower()
        hint_lower = text_hint.lower()
        
        best_el = None
        max_area = -1.0

        for el in elements:
            if str(el.get("role", "")).lower() == role_lower:
                w = float(el.get("width", 0))
                h = float(el.get("height", 0))
                
                if w < min_width or h < min_height:
                    continue
                    
                if not hint_lower or hint_lower in str(el.get("text", "")).lower():
                    area = w * h
                    if area > max_area:
                        max_area = area
                        best_el = el

        return best_el

    @staticmethod
    def bbox(el: Element) -> tuple[float, float, float, float]:
        """Extract (x, y, width, height) from an element dict."""
        return (
            float(el.get("x", 0)),
            float(el.get("y", 0)),
            float(el.get("width", 1)),
            float(el.get("height", 1)),
        )
