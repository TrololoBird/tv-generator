"""
Sync module for tv-screener data.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import List

import requests

logger = logging.getLogger("tv_generator.sync")

__all__ = [
    "sync_markets",
    "sync_display_names",
    "sync_metainfo",
    "sync_scan",
]

DATA_DIR = Path("data")
METAINFO_DIR = DATA_DIR / "metainfo"
SCAN_DIR = DATA_DIR / "scan"

# List of markets to use (must be real TradingView markets)
MARKETS = ["stock", "forex", "crypto", "futures", "cfd", "bonds", "etf", "index", "economics"]

# Only use real endpoints: /metainfo and /scan
TV_BASE = "https://scanner.tradingview.com"


def sync_tv_screener_data(source_dir: Path, force: bool = False) -> None:
    """Sync data from tv-screener project."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Copy column display names
    src_file = source_dir / "src" / "tradingview_screener" / "column.py"
    dst_file = Path("data") / "column_display_names.json"

    if src_file.exists():
        dst_file.parent.mkdir(exist_ok=True)
        shutil.copy2(src_file, dst_file)
        logger.info(f"Copied {src_file}")
    else:
        logger.warning(f"Source file not found: {src_file}")

    # Copy market data
    src_dir = source_dir / "src" / "tradingview_screener"
    dst_dir = Path("data")

    for src_file in src_dir.glob("*.py"):
        if src_file.name in ["__init__.py", "column.py"]:
            continue

        dst_file = dst_dir / src_file.name
        if not dst_file.exists() or force:
            dst_dir.mkdir(exist_ok=True)
            shutil.copy2(src_file, dst_file)
            logger.info(f"Copied {src_file.name}")


def sync_markets() -> None:
    """Save the list of real TradingView markets to data/markets.json."""
    out_path = DATA_DIR / "markets.json"
    logger.info(f"Saving static TradingView markets list to {out_path}")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(MARKETS, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved markets to {out_path.resolve()}")


def sync_display_names() -> None:
    """Fetch and save TradingView field/column names for each market from /metainfo endpoint only."""
    out_path = DATA_DIR / "column_display_names.json"
    out = {}
    for market in MARKETS:
        url = f"{TV_BASE}/{market}/metainfo"
        logger.info(f"Fetching display names for {market} from {url}")
        try:
            resp = requests.get(url, timeout=20)
            logger.info(f"{url} -> {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"Failed to fetch metainfo for {market}: status {resp.status_code}")
                continue
            data = resp.json()
            # Extract all field/column/filter names from metainfo
            fields = list(data.get("fields", {}).keys())
            out[market] = fields
            logger.info(f"{market}: {len(fields)} fields")
        except Exception as e:
            logger.error(f"Exception fetching metainfo for {market}: {e}")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved column display names to {out_path.resolve()}")


def sync_metainfo(market: str) -> None:
    """Fetch and save metainfo for a specific market from TradingView /metainfo endpoint only."""
    url = f"{TV_BASE}/{market}/metainfo"
    out_path = METAINFO_DIR / f"{market}.json"
    logger.info(f"Fetching metainfo for {market} from {url}")
    try:
        resp = requests.get(url, timeout=20)
        logger.info(f"{url} -> {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"Failed to fetch metainfo for {market}: status {resp.status_code}")
            return
        data = resp.json()
        # Если data - список, оборачиваем в {'fields': ...}
        if isinstance(data, list):
            data = {"fields": data}
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved metainfo for {market} to {out_path.resolve()}")
    except Exception as e:
        logger.error(f"Exception fetching metainfo for {market}: {e}")


def sync_scan(market: str) -> None:
    """Fetch and save scan data for a specific market from TradingView /scan endpoint only."""
    url = f"{TV_BASE}/{market}/scan"
    out_path = SCAN_DIR / f"{market}.json"
    logger.info(f"Fetching scan data for {market} from {url}")
    payload = {
        "filter": [],
        "options": {"lang": "en"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "close", "volume"],
        "sort": {"sortBy": "close", "sortOrder": "desc"},
        "range": [0, 50],
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        logger.info(f"{url} -> {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"Failed to fetch scan data for {market}: status {resp.status_code}")
            return
        data = resp.json()
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved scan data for {market} to {out_path.resolve()}")
    except Exception as e:
        logger.error(f"Exception fetching scan data for {market}: {e}")
