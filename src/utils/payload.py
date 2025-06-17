from __future__ import annotations

from typing import Any, Dict, Iterable, List


def build_scan_payload(
    symbols: Iterable[str],
    columns: Iterable[str],
    filter_: Dict[str, Any] | None = None,
    filter2: Dict[str, Any] | None = None,
    sort: Dict[str, Any] | None = None,
    range_: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a scan payload for the given symbols and columns."""

    symbols_list: List[str] = list(symbols)

    def _normalize(col: str) -> str:
        """Strip multi-day/week timeframe suffixes from the column name."""
        if "|" in col:
            base, suffix = col.rsplit("|", 1)
            if suffix and suffix[-1] in {"D", "W"} and suffix[:-1].isdigit():
                return base
        return col

    columns_list: List[str] = [_normalize(c) for c in columns]

    if not symbols_list:
        raise ValueError("symbols list cannot be empty")
    if not columns_list:
        raise ValueError("columns list cannot be empty")
    if len(set(columns_list)) != len(columns_list):
        raise ValueError("columns list contains duplicates")

    payload: Dict[str, Any] = {
        "symbols": {"tickers": symbols_list, "query": {"types": []}},
        "columns": columns_list,
    }
    if filter_ is not None:
        if not isinstance(filter_, dict):
            raise TypeError("filter must be a dict")
        payload["filter"] = filter_
    if filter2 is not None:
        if not isinstance(filter2, dict):
            raise TypeError("filter2 must be a dict")
        payload["filter2"] = filter2
    if sort is not None:
        if not isinstance(sort, dict):
            raise TypeError("sort must be a dict")
        payload["sort"] = sort
    if range_ is not None:
        if not isinstance(range_, dict):
            raise TypeError("range must be a dict")
        payload["range"] = range_
    return payload
