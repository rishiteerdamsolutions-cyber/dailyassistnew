"""Load .env into os.environ for local server startup (no extra dependency)."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    """Set env vars from .env if not already defined in the process."""
    root = Path(__file__).resolve().parent.parent
    env_path = path or (root / ".env")
    if not env_path.is_file():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[key] = value
