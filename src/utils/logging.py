"""Logging utilities used across CLI commands."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Configure basic logging for the application.

    Args:
        verbose: If ``True`` enable debug level, otherwise info.
    """

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def log_exception(exc: Exception, log_path: Path) -> None:
    """Append exception information to ``log_path``.

    Args:
        exc: The exception instance to log.
        log_path: File path where the log should be appended.
    """

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        fh.write(f"{type(exc).__name__}: {exc}\n")
