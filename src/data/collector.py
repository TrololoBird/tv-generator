import logging
from pathlib import Path
from typing import Any, Dict, List

"""Utilities for fetching TradingView metadata and scan results."""

import pandas as pd

import requests

from src.api.data_fetcher import fetch_metainfo, choose_tickers, full_scan, save_json
from src.api.data_manager import build_field_status
from src.models import TVField, MetaInfoResponse
from src.exceptions import TVDataError

logger = logging.getLogger(__name__)


def refresh_market(market: str, outdir: Path | str = "results") -> None:
    """Download and store TradingView data for a market.

    Parameters
    ----------
    market : str
        Market identifier used by TradingView (e.g. ``"crypto"``).
    outdir : Path | str, optional
        Directory where the ``metainfo.json``, ``scan.json`` and
        ``field_status.tsv`` files will be written. Defaults to ``"results"``.

    Raises
    ------
    requests.exceptions.RequestException
        If any network request fails.
    ValueError
        If the received data is malformed.
    """

    outdir = Path(outdir)
    market_dir = outdir / market
    market_dir.mkdir(parents=True, exist_ok=True)
    meta_path = market_dir / "metainfo.json"
    scan_path = market_dir / "scan.json"
    status_path = market_dir / "field_status.tsv"

    try:
        meta: Dict[str, Any] = fetch_metainfo(market)
        fields: List[Dict[str, Any]] = meta.get("data", {}).get("fields") or meta.get(
            "fields", []
        )
        columns: List[str] = []
        tv_fields: List[TVField] = []
        for item in fields:
            name = item.get("name") or item.get("id")
            if name:
                columns.append(str(name))
                tv_fields.append(
                    TVField.model_validate(
                        {"name": name, "type": item.get("type", "string")}
                    )
                )

        try:
            tickers: List[str] = choose_tickers(meta)
        except ValueError as exc:
            logger.warning("No symbols found in metainfo for %s: %s", market, exc)
            tickers = []

        scan: Dict[str, Any] = (
            full_scan(market, tickers, columns)
            if tickers
            else {"data": [], "count": 0, "columns": columns}
        )

        save_json(meta, meta_path)
        logger.debug("Saved %s (%d bytes)", meta_path, meta_path.stat().st_size)
        save_json(scan, scan_path)
        logger.debug("Saved %s (%d bytes)", scan_path, scan_path.stat().st_size)

        meta_model = MetaInfoResponse(data=tv_fields)
        df: pd.DataFrame = build_field_status(meta_model, scan)
        status_path.write_text(df.to_csv(sep="\t", index=False).rstrip("\n"))
        logger.debug("Saved %s (%d bytes)", status_path, status_path.stat().st_size)
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("Failed to refresh %s: %s", market, exc)
        raise TVDataError(str(exc)) from exc
