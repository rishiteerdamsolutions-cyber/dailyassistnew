"""
Text burstiness destruction engine.

Validates text payloads against a 30-day rolling history
to ensure no two sentences share matching character counts
and word structures.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from bol.utils.logging import get_logger

logger = get_logger(__name__)


class VarianceEngine:
    """
    Validates and records text metrics against a 30-day rolling window
    to destroy statistical text burstiness signatures.
    """

    def __init__(self, history_db_path: Path | None = None) -> None:
        self._history_path = history_db_path
        self._history: list[dict] = []
        if history_db_path is not None:
            self._load_history()

    def validate_text(self, text: str) -> bool:
        """
        Validate text against the 30-day rolling history.

        Returns False if any sentence matches a previous entry
        with the same character count AND word count.
        """
        self._prune_old_entries()
        sentences = self._split_sentences(text)

        for sentence in sentences:
            char_count = len(sentence.strip())
            word_count = len(sentence.strip().split())
            if char_count == 0:
                continue

            for entry in self._history:
                if entry["char_count"] == char_count and entry["word_count"] == word_count:
                    logger.warning(
                        "Text burstiness detected: sentence matches history "
                        "(chars=%d, words=%d)", char_count, word_count,
                    )
                    return False
        return True

    def record_text(self, text: str) -> None:
        """Add sentence metrics to the rolling history and save."""
        sentences = self._split_sentences(text)
        today = date.today().isoformat()

        for sentence in sentences:
            stripped = sentence.strip()
            if not stripped:
                continue
            self._history.append({
                "date": today,
                "char_count": len(stripped),
                "word_count": len(stripped.split()),
            })

        self._prune_old_entries()
        self._save_history()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences on period, question mark, exclamation, or newline."""
        # Split on sentence-ending punctuation followed by space/end, or newlines
        parts = re.split(r'(?<=[.!?])\s+|\n+', text)
        return [p.strip() for p in parts if p.strip()]

    def _prune_old_entries(self) -> None:
        """Remove entries older than 30 days."""
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        self._history = [e for e in self._history if e.get("date", "") >= cutoff]

    def _save_history(self) -> None:
        """Persist history to JSON file."""
        if self._history_path is None:
            return
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._history_path, "w") as f:
            json.dump(self._history, f, indent=2)

    def _load_history(self) -> None:
        """Load history from JSON file if it exists."""
        if self._history_path is None or not self._history_path.exists():
            return
        try:
            with open(self._history_path) as f:
                self._history = json.load(f)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt history file, starting fresh")
            self._history = []
