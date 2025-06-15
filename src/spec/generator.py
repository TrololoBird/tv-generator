from __future__ import annotations

from pathlib import Path
from typing import List
import logging

from src.generator.yaml_generator import generate_for_market

logger = logging.getLogger(__name__)


def detect_all_markets(indir: str | Path) -> List[str]:
    """Return list of markets found under ``indir`` directory."""
    base = Path(indir)
    markets = [p.parent.name for p in base.glob("*/metainfo.json")]
    markets.sort()
    return markets


def generate_spec_for_all_markets(
    indir: Path,
    outdir: Path,
    max_size: int = 1_048_576,
    *,
    include_missing: bool = False,
    include_types: tuple[str, ...] = (),
    exclude_types: tuple[str, ...] = (),
    only_timeframe_supported: bool = False,
    only_daily: bool = False,
) -> List[Path]:
    """Generate specs for all markets under ``indir``."""
    out_files: List[Path] = []
    for market in detect_all_markets(indir):
        out_files.append(
            generate_spec_for_market(
                market,
                indir,
                outdir,
                max_size,
                include_missing=include_missing,
                include_types=include_types,
                exclude_types=exclude_types,
                only_timeframe_supported=only_timeframe_supported,
                only_daily=only_daily,
            )
        )
    return out_files


def generate_spec_for_market(
    market: str,
    indir: Path,
    outdir: Path,
    max_size: int = 1_048_576,
    *,
    include_missing: bool = False,
    include_types: tuple[str, ...] = (),
    exclude_types: tuple[str, ...] = (),
    only_timeframe_supported: bool = False,
    only_daily: bool = False,
) -> Path:
    """Generate spec for a single market."""

    return generate_for_market(
        market,
        indir,
        outdir,
        max_size,
        include_missing=include_missing,
        include_types=include_types,
        exclude_types=exclude_types,
        only_timeframe_supported=only_timeframe_supported,
        only_daily=only_daily,
    )
