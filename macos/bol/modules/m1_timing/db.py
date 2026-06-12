"""
SQLite persistence layer for timing pools.

Manages the 1,000-value depletion pools per platform,
ensuring extraction-without-replacement across sessions.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from bol.utils.logging import get_logger

logger = get_logger(__name__)


class TimingDatabase:
    """SQLite-backed storage for timing pool depletion tracking."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS timing_pools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        value_ms REAL NOT NULL,
        consumed INTEGER DEFAULT 0,
        consumed_at TEXT,
        cycle_id INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_platform_consumed
        ON timing_pools (platform, consumed);
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize database, creating file and tables if needed."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(self._DDL)
        self._conn.commit()
        logger.info("Timing database initialized at %s", db_path)

    def initialize_pool(
        self, platform: str, values: list[float], cycle_id: int = 0
    ) -> None:
        """Bulk-insert a new set of timing values for a platform."""
        rows = [(platform, v, 0, None, cycle_id) for v in values]
        self._conn.executemany(
            "INSERT INTO timing_pools (platform, value_ms, consumed, consumed_at, cycle_id) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()
        logger.info(
            "Initialized timing pool for '%s': %d values, cycle %d",
            platform, len(values), cycle_id,
        )

    def draw_value(self, platform: str) -> float:
        """
        Draw one unconsumed value randomly and mark it consumed.

        Raises
        ------
        ValueError
            If no unconsumed values remain.
        """
        cursor = self._conn.execute(
            "SELECT id, value_ms FROM timing_pools "
            "WHERE platform = ? AND consumed = 0 "
            "ORDER BY RANDOM() LIMIT 1",
            (platform,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"No unconsumed values in pool for platform '{platform}'")

        record_id, value_ms = row
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE timing_pools SET consumed = 1, consumed_at = ? WHERE id = ?",
            (now, record_id),
        )
        self._conn.commit()
        return float(value_ms)

    def get_available_count(self, platform: str) -> int:
        """Count unconsumed values for a platform."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM timing_pools WHERE platform = ? AND consumed = 0",
            (platform,),
        )
        return cursor.fetchone()[0]

    def get_consumed_count(self, platform: str) -> int:
        """Count consumed values for a platform."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM timing_pools WHERE platform = ? AND consumed = 1",
            (platform,),
        )
        return cursor.fetchone()[0]

    def get_current_cycle(self, platform: str) -> int:
        """Get the current cycle ID for a platform."""
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(cycle_id), 0) FROM timing_pools WHERE platform = ?",
            (platform,),
        )
        return cursor.fetchone()[0]

    def reset_cycle(self, platform: str, new_cycle_id: int) -> None:
        """Mark all values as unconsumed and update the cycle ID."""
        self._conn.execute(
            "UPDATE timing_pools SET consumed = 0, consumed_at = NULL, cycle_id = ? "
            "WHERE platform = ?",
            (new_cycle_id, platform),
        )
        self._conn.commit()
        logger.info("Reset timing pool for '%s' to cycle %d", platform, new_cycle_id)

    def pool_exists(self, platform: str) -> bool:
        """Check if a timing pool exists for the given platform."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM timing_pools WHERE platform = ?",
            (platform,),
        )
        return cursor.fetchone()[0] > 0

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
