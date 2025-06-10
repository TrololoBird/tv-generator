from __future__ import annotations

from typing import Any, Dict, Iterable


def build_scan_payload(
    symbols: Iterable[str],
    columns: Iterable[str],
    filters: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a scan payload for the given symbols and columns."""
    payload = {
        "symbols": {"tickers": list(symbols), "query": {"types": []}},
        "columns": list(columns),
    }
    if filters:
        payload["filter"] = filters
    return payload
