import json
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor

from src.models import MetaInfoResponse, ScanResponse
from src.api.tradingview_api import TradingViewAPI

# TradingView's ``/scan`` endpoint returns at most 20 columns per request.
# To obtain data for more fields we issue multiple requests in parallel,
# splitting the columns list into batches of this size.
MAX_COLUMNS_PER_SCAN = 20


def fetch_metainfo(
    scope: str, api_base: str = "https://scanner.tradingview.com"
) -> Dict[str, Any]:
    """Return metainfo for a given scope using the TradingViewAPI."""

    # ``TradingViewAPI.metainfo`` sends the POST request and validates
    # the response via ``MetaInfoResponse``.
    api = TradingViewAPI(base_url=api_base)
    data = api.metainfo(scope, {"query": ""})
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
        )
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

    body = meta_dict.get("body") or meta_dict.get("data", {})
    if symbol_idx is None and isinstance(body, dict):
        symbols_list = body.get("symbols") or []
        if symbols_list:
            return [s if isinstance(s, str) else s[0] for s in symbols_list][:limit]

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

    if not tickers:
        raise ValueError("Cannot determine tickers: missing symbol field in metadata")

    return tickers[:limit]


def full_scan(
    scope: str,
    tickers: List[str],
    columns: List[str],
    api_base: str = "https://scanner.tradingview.com",
) -> Dict[str, Any]:
    """Perform a scan request splitting columns into batches."""
    if tickers == ["AUTO"]:
        meta_json = fetch_metainfo(scope, api_base)
        tickers = choose_tickers(meta_json, limit=10)

    api = TradingViewAPI(base_url=api_base)
    url = f"{api_base.rstrip('/')}/{scope}/scan"
    batches = _chunks(columns, MAX_COLUMNS_PER_SCAN)

    def _scan(cols: List[str]) -> Dict[str, Any]:
        payload = {
            "symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": cols,
        }
        resp = api.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError as exc:  # pragma: no cover - should not happen in tests
            raise ValueError("Invalid JSON received from TradingView") from exc
        ScanResponse.parse_obj(data)
        return data

    result_map: dict[str, list[Any]] = {sym: [] for sym in tickers}
    with ThreadPoolExecutor(max_workers=min(8, len(batches))) as executor:
        responses = list(executor.map(_scan, batches))

    for data in responses:
        rows = data.get("data", []) if isinstance(data, dict) else []
        for row in rows:
            sym = row.get("s") if isinstance(row, dict) else None
            dval = row.get("d") if isinstance(row, dict) else None
            if isinstance(sym, str) and isinstance(dval, list):
                result_map.setdefault(sym, []).extend(dval)

    final_rows = [{"s": sym, "d": result_map.get(sym, [])} for sym in tickers]
    final = {"data": final_rows, "count": len(final_rows)}
    ScanResponse.parse_obj(final)
    return final


def save_json(data: Dict[str, Any], path: Path) -> None:
    """Save dictionary as pretty JSON to given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
