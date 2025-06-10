from __future__ import annotations

from typing import Any, Dict, Iterable


def build_scan_payload(
    symbols: Iterable[str], columns: Iterable[str]
) -> Dict[str, Any]:
    """Return a scan payload for the given symbols and columns."""
    return {
        "symbols": {"tickers": list(symbols), "query": {"types": []}},
        "columns": list(columns),
    }
