import json
from pathlib import Path
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter, Retry


def _get_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.setdefault("User-Agent", "tv-generator")
    return session


def fetch_metainfo(
    scope: str, api_base: str = "https://scanner.tradingview.com"
) -> Dict:
    """Return metainfo for a given scope using GET request."""
    session = _get_session()
    url = f"{api_base.rstrip('/')}/{scope}/metainfo"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError as exc:  # pragma: no cover - should not happen in tests
        raise ValueError("Invalid JSON received from TradingView") from exc


def _chunks(seq: List[str], size: int) -> List[List[str]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]  # noqa: E203


def full_scan(
    scope: str,
    tickers: List[str],
    columns: List[str],
    api_base: str = "https://scanner.tradingview.com",
) -> Dict:
    """Perform a scan request splitting columns into batches."""
    session = _get_session()
    url = f"{api_base.rstrip('/')}/{scope}/scan"
    batches = _chunks(columns, 20)
    result: Dict | None = None
    for cols in batches:
        payload = {
            "symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": cols,
        }
        resp = session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError as exc:  # pragma: no cover - should not happen in tests
            raise ValueError("Invalid JSON received from TradingView") from exc
        if result is None:
            result = data
        else:
            res_rows = result.get("data", []) if isinstance(result, dict) else []
            new_rows = data.get("data", []) if isinstance(data, dict) else []
            for idx, row in enumerate(new_rows):
                if idx < len(res_rows):
                    dval = row.get("d") if isinstance(row, dict) else None
                    res_d = (
                        res_rows[idx].get("d")
                        if isinstance(res_rows[idx], dict)
                        else None
                    )
                    if isinstance(dval, list) and isinstance(res_d, list):
                        res_d.extend(dval)
    return result or {}


def save_json(data: Dict, path: Path) -> None:
    """Save dictionary as pretty JSON to given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
