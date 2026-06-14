"""
agents/linguistic.py — Keystroke engine for AHA Chrome Extension backend.

Ported from:
  bol/modules/m5_linguistic/engine.py
  bol/modules/m5_linguistic/fatigue.py
  bol/modules/m5_linguistic/typo.py

Fully self-contained — no bol.* imports.

Public API
----------
generate_keystrokes(text: str, personality: PersonalityVector) -> list[KeystrokeEvent]

Each KeystrokeEvent maps directly to a chrome.debugger Input.dispatchKeyEvent call:
  {
    "key":             str   — the character (or "Backspace")
    "text":            str   — printable character (empty for Backspace)
    "delay_before_ms": float — milliseconds to wait before dispatching
    "shift":           bool  — whether Shift is held (for uppercase)
  }
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Optional

from agents.policy import PersonalityVector


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class KeystrokeEvent:
    """
    A single dispatchable keystroke event.

    Maps to chrome.debugger Input.dispatchKeyEvent parameters.
    """
    key: str                  # DOM key name, e.g. "a", "A", "Backspace", " ", "Enter"
    text: str                 # Printable text (empty string for control keys)
    delay_before_ms: float    # Wait this long before firing the event
    shift: bool = False       # Whether the Shift modifier is active
    is_typo: bool = False     # Informational — was this keystroke a typo?
    is_correction: bool = False  # Informational — is this a backspace correction?


# ── QWERTY Adjacency Matrix ───────────────────────────────────────────────────

_QWERTY_ADJACENCY: dict[str, list[str]] = {
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

_PUNCTUATION = set('.,;:!?"\'()-—')


# ── Fatigue Profile ───────────────────────────────────────────────────────────

@dataclass
class _FatigueProfile:
    base_wpm: float
    decay_rate: float
    base_typo_rate: float
    typo_growth_rate: float = 0.005
    characters_typed: int = 0

    @property
    def current_wpm(self) -> float:
        degradation = 1.0 - (self.decay_rate * (self.characters_typed / 100.0))
        return max(self.base_wpm * max(degradation, 0.4), 15.0)

    @property
    def current_typo_rate(self) -> float:
        return min(
            self.base_typo_rate + (self.typo_growth_rate * (self.characters_typed / 100.0)),
            0.08,
        )

    @property
    def current_char_delay_ms(self) -> float:
        chars_per_minute = self.current_wpm * 5.0
        return (60.0 / chars_per_minute) * 1000.0


# ── Internal helpers ──────────────────────────────────────────────────────────

def _create_fatigue_profile(personality: PersonalityVector) -> _FatigueProfile:
    wpm_range = personality.base_wpm_max - personality.base_wpm_min
    base_wpm = float(personality.base_wpm_min + secrets.randbelow(max(wpm_range + 1, 1)))

    decay_jitter = (secrets.randbelow(41) - 20) / 1000.0   # ±0.02
    decay_rate = max(0.05, min(0.12, personality.fatigue_rate + decay_jitter))
    base_typo_rate = 0.015 * personality.typo_rate_modifier

    return _FatigueProfile(
        base_wpm=base_wpm,
        decay_rate=decay_rate,
        base_typo_rate=base_typo_rate,
    )


def _calculate_delay_ms(profile: _FatigueProfile, char: str) -> float:
    """Character delay with entropy jitter and character-type multipliers."""
    base = profile.current_char_delay_ms
    jitter = 1.0 + (secrets.randbelow(41) - 20) / 100.0   # ±20%
    delay = base * jitter

    if char == " ":
        delay *= 1.5 + secrets.randbelow(11) / 10.0        # 1.5–2.5×
    elif char in _PUNCTUATION:
        delay *= 1.2 + secrets.randbelow(7) / 10.0         # 1.2–1.8×
    elif char == "\n":
        delay *= 2.0 + secrets.randbelow(11) / 10.0        # 2.0–3.0×

    return max(delay, 10.0)


def _get_proximity_typo(char: str) -> str:
    """Return a plausible QWERTY-adjacent neighbour, preserving case."""
    lower = char.lower()
    if lower not in _QWERTY_ADJACENCY:
        return char
    neighbors = _QWERTY_ADJACENCY[lower]
    idx = secrets.randbelow(len(neighbors))
    typo = neighbors[idx]
    if char.isupper():
        typo = typo.upper()
    return typo


def _should_inject_typo(rate: float) -> bool:
    return secrets.randbelow(10_000) / 10_000.0 < rate


def _realization_delay_ms(profile: _FatigueProfile) -> float:
    """300–1500ms, scaled slightly by fatigue level."""
    base = 300 + secrets.randbelow(1201)
    fatigue_factor = 1.0 + (profile.characters_typed / 1000.0) * 0.3
    return base * min(fatigue_factor, 2.0)


def _char_to_key_event(char: str) -> tuple[str, str, bool]:
    """
    Return (key_name, text, shift_held) for a single character.

    key_name → the DOM key string used in dispatchKeyEvent.
    text     → the actual printed character.
    shift    → True when Shift must be held.
    """
    if char == "\n":
        return ("Enter", "", False)
    if char == "\t":
        return ("Tab", "", False)
    if char == "\b":
        return ("Backspace", "", False)
    if char == " ":
        return ("Space", " ", False)
    if char.isupper():
        return (char, char, True)
    # Punctuation that requires Shift on US keyboards
    _shift_map = {
        "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
        "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
        "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
        ":": ";", '"': "'", "<": ",", ">": ".", "?": "/",
        "~": "`",
    }
    if char in _shift_map:
        return (char, char, True)
    return (char, char, False)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_keystrokes(
    text: str,
    personality: PersonalityVector,
) -> list[KeystrokeEvent]:
    """
    Generate a complete keystroke sequence with progressive fatigue,
    QWERTY proximity typos, and correction events.

    Each event is ready to be dispatched via chrome.debugger
    Input.dispatchKeyEvent after waiting delay_before_ms.

    Parameters
    ----------
    text          The exact string to type.
    personality   Personality vector controlling WPM, typo rate, fatigue.

    Returns
    -------
    list[KeystrokeEvent]
        Ordered list including typos, backspace corrections, and real chars.
    """
    profile = _create_fatigue_profile(personality)
    events: list[KeystrokeEvent] = []
    chars_typed = 0

    for i, char in enumerate(text):
        delay = _calculate_delay_ms(profile, char)

        if char.isalpha() and _should_inject_typo(profile.current_typo_rate):
            # ── 1. Type the wrong character
            typo_char = _get_proximity_typo(char)
            key, txt, shift = _char_to_key_event(typo_char)
            events.append(KeystrokeEvent(
                key=key, text=txt, delay_before_ms=delay, shift=shift, is_typo=True,
            ))
            chars_typed += 1

            # ── 2. Realization pause + Backspace
            realization = _realization_delay_ms(profile)
            events.append(KeystrokeEvent(
                key="Backspace", text="", delay_before_ms=realization, is_correction=True,
            ))

            # ── 3. Re-type the correct character (slightly faster — muscle memory)
            corrected_delay = _calculate_delay_ms(profile, char) * 0.8
            key, txt, shift = _char_to_key_event(char)
            events.append(KeystrokeEvent(
                key=key, text=txt, delay_before_ms=corrected_delay, shift=shift,
            ))
            chars_typed += 1

        else:
            # ── Normal keystroke
            key, txt, shift = _char_to_key_event(char)
            events.append(KeystrokeEvent(
                key=key, text=txt, delay_before_ms=delay, shift=shift,
            ))
            chars_typed += 1

        # Update fatigue profile (immutable replacement)
        profile = _FatigueProfile(
            base_wpm=profile.base_wpm,
            decay_rate=profile.decay_rate,
            base_typo_rate=profile.base_typo_rate,
            typo_growth_rate=profile.typo_growth_rate,
            characters_typed=chars_typed,
        )

    return events
