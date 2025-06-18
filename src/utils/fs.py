"""File system helper utilities."""

from __future__ import annotations

import json
import logging
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any
import yaml

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


def save_json(data: Any, path: Path) -> None:
    """Save *data* as pretty JSON to ``path``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_yaml(path: Path, max_size: int = 5_242_880) -> Any:
    """Load YAML file with a size limit (default 5 MB)."""

    size = os.stat(path).st_size
    if size > max_size:
        logger.error("YAML too large: %s (%d bytes)", path, size)
        raise click.ClickException(f"File too large: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        logger.error("Failed to parse YAML from %s: %s", path, exc)
        raise click.ClickException(f"Invalid YAML in {path}") from exc


def cleanup_cache_file(path: Path, max_size: int = 50 * 1024 * 1024) -> None:
    """Remove cache *path* if it exceeds ``max_size`` bytes."""

    if not path.exists():
        return
    size = path.stat().st_size
    if size <= max_size:
        return
    logger.info("Clearing cache %s (%d bytes > %d)", path, size, max_size)
    try:
        path.unlink()
    except OSError as exc:
        logger.warning("Failed to delete cache %s: %s", path, exc)
