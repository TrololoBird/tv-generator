from __future__ import annotations

"""Helpers for working with :class:`~pathlib.Path`."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Ensure *path* exists and is a directory."""
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    return path


def ensure_file(path: Path) -> Path:
    """Ensure *path* exists and is a file."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return path


def file_size(path: Path) -> int:
    """Return the size of *path* in bytes."""
    return ensure_file(path).stat().st_size


def market_paths(indir: Path, market: str) -> tuple[Path, Path, Path]:
    """Return metainfo, scan and status file paths for ``market`` under ``indir``."""
    market_dir = indir / market
    return (
        market_dir / "metainfo.json",
        market_dir / "scan.json",
        market_dir / "field_status.tsv",
    )
