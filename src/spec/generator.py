from __future__ import annotations

from pathlib import Path
from typing import List

from src.generator.yaml_generator import generate_for_market


def detect_all_markets(indir: str | Path) -> List[str]:
    """Return list of markets found under ``indir`` directory."""
    base = Path(indir)
    markets = [p.parent.name for p in base.glob("*/metainfo.json")]
    markets.sort()
    return markets


def generate_spec_for_all_markets(
    indir: Path, outdir: Path, max_size: int = 1_048_576
) -> List[Path]:
    """Generate specs for all markets under ``indir``."""
    out_files: List[Path] = []
    for market in detect_all_markets(indir):
        out_files.append(generate_for_market(market, indir, outdir, max_size))
    return out_files
