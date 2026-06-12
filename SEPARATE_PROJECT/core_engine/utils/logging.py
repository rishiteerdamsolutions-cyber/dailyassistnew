"""
Structured logging for the BOL system.

Provides a configured logger with consistent formatting
across all modules.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


_CONFIGURED = False


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger instance for a BOL module.

    Parameters
    ----------
    name : str
        Logger name (typically ``__name__`` of the calling module).
    level : int
        Logging level (default: INFO).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    global _CONFIGURED

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not _CONFIGURED:
        _configure_root_logger(level)
        _CONFIGURED = True

    return logger


def _configure_root_logger(level: int) -> None:
    """Configure the root BOL logger with console output."""
    root = logging.getLogger("bol")
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)


def setup_file_logging(log_dir: Path, level: int = logging.DEBUG) -> None:
    """
    Add a file handler to the root BOL logger.

    Parameters
    ----------
    log_dir : Path
        Directory where log files will be written.
    level : int
        Logging level for file output (default: DEBUG).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bol.log"

    root = logging.getLogger("bol")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S.%f",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
