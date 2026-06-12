"""
QWERTY proximity matrix and typo injection engine.

Maps physical key adjacency on a standard QWERTY keyboard
and generates plausible proximity typos.
"""

from __future__ import annotations

import secrets

from bol.schemas.linguistic import FatigueProfile, TypoSpec


class TypoEngine:
    """
    Generates proximity-based keyboard typos using a QWERTY adjacency matrix.

    Preserves case and handles unknown characters gracefully.
    """

    QWERTY_ADJACENCY: dict[str, list[str]] = {
        # Number row
        "1": ["2", "q"],
        "2": ["1", "3", "q", "w"],
        "3": ["2", "4", "w", "e"],
        "4": ["3", "5", "e", "r"],
        "5": ["4", "6", "r", "t"],
        "6": ["5", "7", "t", "y"],
        "7": ["6", "8", "y", "u"],
        "8": ["7", "9", "u", "i"],
        "9": ["8", "0", "i", "o"],
        "0": ["9", "o", "p"],
        # Top row
        "q": ["1", "2", "w", "a"],
        "w": ["q", "2", "3", "e", "a", "s"],
        "e": ["w", "3", "4", "r", "s", "d"],
        "r": ["e", "4", "5", "t", "d", "f"],
        "t": ["r", "5", "6", "y", "f", "g"],
        "y": ["t", "6", "7", "u", "g", "h"],
        "u": ["y", "7", "8", "i", "h", "j"],
        "i": ["u", "8", "9", "o", "j", "k"],
        "o": ["i", "9", "0", "p", "k", "l"],
        "p": ["o", "0", "l"],
        # Home row
        "a": ["q", "w", "s", "z"],
        "s": ["a", "w", "e", "d", "z", "x"],
        "d": ["s", "e", "r", "f", "x", "c"],
        "f": ["d", "r", "t", "g", "c", "v"],
        "g": ["f", "t", "y", "h", "v", "b"],
        "h": ["g", "y", "u", "j", "b", "n"],
        "j": ["h", "u", "i", "k", "n", "m"],
        "k": ["j", "i", "o", "l", "m"],
        "l": ["k", "o", "p"],
        # Bottom row
        "z": ["a", "s", "x"],
        "x": ["z", "s", "d", "c"],
        "c": ["x", "d", "f", "v"],
        "v": ["c", "f", "g", "b"],
        "b": ["v", "g", "h", "n"],
        "n": ["b", "h", "j", "m"],
        "m": ["n", "j", "k"],
    }

    def get_proximity_typo(self, char: str) -> str:
        """
        Return a plausible neighboring key for the given character.

        Preserves case: uppercase input produces uppercase output.
        Unknown characters are returned unchanged.

        Parameters
        ----------
        char : str
            The original character.

        Returns
        -------
        str
            A QWERTY-adjacent character, or the original if no mapping exists.
        """
        lower = char.lower()
        if lower not in self.QWERTY_ADJACENCY:
            return char

        neighbors = self.QWERTY_ADJACENCY[lower]
        idx = secrets.randbelow(len(neighbors))
        typo = neighbors[idx]

        # Preserve case
        if char.isupper():
            typo = typo.upper()

        return typo

    def should_inject_typo(self, current_typo_rate: float) -> bool:
        """
        Determine whether to inject a typo at the current position.

        Uses 10,000 granularity for fine-grained probability.
        """
        return secrets.randbelow(10000) / 10000.0 < current_typo_rate

    def generate_typo_spec(
        self, position: int, original_char: str, fatigue: FatigueProfile
    ) -> TypoSpec:
        """
        Generate a complete typo specification with correction timing.

        Parameters
        ----------
        position : int
            Character index where the typo occurs.
        original_char : str
            The correct character.
        fatigue : FatigueProfile
            Current fatigue state (influences realization delay).

        Returns
        -------
        TypoSpec
            Full typo specification including correction details.
        """
        replacement = self.get_proximity_typo(original_char)

        # Realization delay: 300-1500ms, shorter when less fatigued
        base_realization = 300 + secrets.randbelow(1201)  # 300 to 1500
        fatigue_factor = 1.0 + (fatigue.characters_typed / 1000.0) * 0.3
        realization_ms = base_realization * min(fatigue_factor, 2.0)

        return TypoSpec(
            position=position,
            original_char=original_char,
            replacement_char=replacement,
            realization_delay_ms=realization_ms,
            correction_backspaces=1,
        )
