import json
import logging
from pathlib import Path
from typing import Any

import requests

from src.api.data_fetcher import fetch_metainfo, choose_tickers, full_scan, save_json
from src.api.data_manager import build_field_status
from src.models import TVField, MetaInfoResponse

logger = logging.getLogger(__name__)


def refresh_market(market: str, outdir: Path | str = "results") -> None:
    """Refresh TradingView data for ``market`` into ``outdir`` directory."""

    outdir = Path(outdir)
    market_dir = outdir / market
    market_dir.mkdir(parents=True, exist_ok=True)
    meta_path = market_dir / "metainfo.json"
    scan_path = market_dir / "scan.json"
    status_path = market_dir / "field_status.tsv"

    try:
        meta = fetch_metainfo(market)
        fields = meta.get("data", {}).get("fields") or meta.get("fields", [])
        columns: list[str] = []
        tv_fields: list[TVField] = []
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
            tickers = choose_tickers(meta)
        except ValueError as exc:
            logger.warning("No symbols found in metainfo for %s: %s", market, exc)
            tickers = []

        scan = (
            full_scan(market, tickers, columns)
            if tickers
            else {"data": [], "count": 0, "columns": columns}
        )

        save_json(meta, meta_path)
        save_json(scan, scan_path)

        meta_model = MetaInfoResponse(data=tv_fields)
        df = build_field_status(meta_model, scan)
        status_path.write_text(df.to_csv(sep="\t", index=False).rstrip("\n"))
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("Failed to refresh %s: %s", market, exc)
