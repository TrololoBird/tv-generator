"""File system helper utilities."""

from __future__ import annotations

import json
import logging
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)


def load_json(path: Path, max_size: int = 1_048_576) -> Any:
    """Load JSON file with a size limit.

    Args:
        path: Path to the JSON file.
        max_size: Maximum allowed file size in bytes.

    Returns:
        Parsed JSON object.

    Raises:
        FileNotFoundError: If the file does not exist.
        click.ClickException: If JSON is invalid or the file exceeds ``max_size``.
    """

    size = os.stat(path).st_size
    if size > max_size:
        logger.error("File too large: %s (%d bytes)", path, size)
        raise click.ClickException(f"File too large: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except JSONDecodeError as exc:
        logger.error("Failed to parse JSON from %s: %s", path, exc)
        raise click.ClickException(f"Invalid JSON in {path}") from exc
