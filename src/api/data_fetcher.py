import json
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List

from src.models import MetaInfoResponse, ScanResponse

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
        data = resp.json()
    except ValueError as exc:  # pragma: no cover - should not happen in tests
        raise ValueError("Invalid JSON received from TradingView") from exc
    MetaInfoResponse.parse_obj(data)
    return data


def _chunks(seq: List[str], size: int) -> List[List[str]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]  # noqa: E203


def choose_tickers(
    meta: MetaInfoResponse | Dict[str, Any], limit: int = 10
) -> List[str]:
    """Return up to ``limit`` tickers based on metainfo and optional scan.

    The function first looks for a field named ``symbol`` or ``s`` to determine
    the index of the ticker column. If ``scan`` data is present inside the
    supplied ``meta`` mapping, the most frequent tickers are returned.  When no
    scan data is available, the symbols list is taken from
    ``meta['body']['symbols']`` or ``meta['data']['index']['names']``.
    """

    if not isinstance(meta, dict):
        meta_dict: Dict[str, Any] = (
            meta.model_dump(exclude_none=False) if hasattr(meta, "model_dump") else {}
        )  # type: ignore[arg-type]
    else:
        meta_dict = meta

    fields = meta_dict.get("fields") or meta_dict.get("data", {}).get("fields") or []
    symbol_idx = None
    for idx, field in enumerate(fields):
        name = None
        if isinstance(field, dict):
            name = field.get("name") or field.get("id")
        elif hasattr(field, "n"):
            name = getattr(field, "n")
        if isinstance(name, str) and name.lower() in {"symbol", "s"}:
            symbol_idx = idx
            break

    tickers: list[str] = []

    scan = meta_dict.get("scan")
    if symbol_idx is not None and isinstance(scan, dict):
        rows = scan.get("data")
        if isinstance(rows, list):
            counter: Counter[str] = Counter()
            for row in rows:
                dval = row.get("d") if isinstance(row, dict) else None
                if (
                    isinstance(dval, list)
                    and symbol_idx < len(dval)
                    and isinstance(dval[symbol_idx], str)
                ):
                    counter[str(dval[symbol_idx])] += 1
            for sym, _ in counter.most_common(limit):
                if sym not in tickers:
                    tickers.append(sym)

    if not tickers:
        body = meta_dict.get("body") or meta_dict.get("data", {})
        symbols = None
        if isinstance(body, dict):
            symbols = body.get("symbols")
            if symbols is None:
                index = body.get("index") or meta_dict.get("index")
                if isinstance(index, dict):
                    symbols = index.get("names")
        if isinstance(symbols, list):
            for item in symbols:
                if len(tickers) >= limit:
                    break
                symbol: str | None = None
                if isinstance(item, str):
                    symbol = item
                elif isinstance(item, list) and item:
                    if isinstance(item[0], str):
                        symbol = item[0]
                elif isinstance(item, dict):
                    val = item.get("symbol") or item.get("s")
                    if isinstance(val, str):
                        symbol = val
                if symbol and symbol not in tickers:
                    tickers.append(symbol)

    return tickers[:limit]


def full_scan(
    scope: str,
    tickers: List[str],
    columns: List[str],
    api_base: str = "https://scanner.tradingview.com",
) -> Dict:
    """Perform a scan request splitting columns into batches."""
    if tickers == ["AUTO"]:
        meta_json = fetch_metainfo(scope, api_base)
        tickers = choose_tickers(meta_json, limit=10)

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
        ScanResponse.parse_obj(data)
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
    final = result or {}
    ScanResponse.parse_obj(final)
    return final


def save_json(data: Dict, path: Path) -> None:
    """Save dictionary as pretty JSON to given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
