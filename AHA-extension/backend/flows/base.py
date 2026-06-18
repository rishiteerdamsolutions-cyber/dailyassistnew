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
        Case-insensitive partial-match search across element text.

        Tries each query in order and returns the first match.
        Optionally filters by minimum bounding box size (useful for
        distinguishing icon-only buttons from text labels).

        Parameters
        ----------
        elements   Page element list.
        *queries   One or more text substrings to search for.
        min_width  Minimum element width to accept.
        min_height Minimum element height to accept.

        Returns
        -------
        The first matching element dict, or None.
        """
        import re
        from difflib import SequenceMatcher
        for query in queries:
            q = re.sub(r'[^a-z0-9]', '', query.lower())
            for el in elements:
                el_text = re.sub(r'[^a-z0-9]', '', str(el.get("text", "")).lower())
                
                # Check for exact substring first
                if q in el_text:
                    match_ratio = 1.0
                elif len(el_text) > 0 and len(q) > 0:
                    # True fuzzy match (allows typos)
                    match_ratio = SequenceMatcher(None, q, el_text).ratio()
                    # Also check if q is a fuzzy substring of el_text
                    if match_ratio < 0.8 and len(el_text) > len(q):
                        # Find the best matching substring of length len(q)
                        best_sub = 0
                        for i in range(len(el_text) - len(q) + 1):
                            sub = el_text[i:i+len(q)]
                            r = SequenceMatcher(None, q, sub).ratio()
                            if r > best_sub:
                                best_sub = r
                        match_ratio = max(match_ratio, best_sub)
                else:
                    match_ratio = 0.0

                if match_ratio >= 0.8:  # 80% similarity threshold
                    w = float(el.get("width", 0))
                    h = float(el.get("height", 0))
                    if w >= min_width and h >= min_height:
                        return el
        return None

    @staticmethod
    def role_find(
        elements: list[Element],
        role: str,
        text_hint: str = "",
    ) -> Optional[Element]:
        """
        Find an element by ARIA role, optionally filtered by text hint.

        Parameters
        ----------
        elements   Page element list.
        role       ARIA role string (e.g. "textbox", "button").
        text_hint  Optional substring to further narrow the match.
        """
        role_lower = role.lower()
        hint_lower = text_hint.lower()
        for el in elements:
            if str(el.get("role", "")).lower() == role_lower:
                if not hint_lower or hint_lower in str(el.get("text", "")).lower():
                    return el
        return None

    @staticmethod
    def bbox(el: Element) -> tuple[float, float, float, float]:
        """Extract (x, y, width, height) from an element dict."""
        return (
            float(el.get("x", 0)),
            float(el.get("y", 0)),
            float(el.get("width", 1)),
            float(el.get("height", 1)),
        )
