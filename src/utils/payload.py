from __future__ import annotations

from typing import Any, Dict, Iterable


def build_scan_payload(
    symbols: Iterable[str],
    columns: Iterable[str],
    filter_: Dict[str, Any] | None = None,
    filter2: Dict[str, Any] | None = None,
    sort: Dict[str, Any] | None = None,
    range_: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a scan payload for the given symbols and columns."""

    payload = {
        "symbols": {"tickers": list(symbols), "query": {"types": []}},
        "columns": list(columns),
    }
    if filter_:
        payload["filter"] = filter_
    if filter2:
        payload["filter2"] = filter2
    if sort:
        payload["sort"] = sort
    if range_:
        payload["range"] = range_
    return payload
