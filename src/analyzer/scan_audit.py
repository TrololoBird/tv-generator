from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

__all__ = ["find_missing_fields"]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _extract_strings(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for val in obj.values():
            yield from _extract_strings(val)
    elif isinstance(obj, list):
        for item in obj:
            yield from _extract_strings(item)
    elif isinstance(obj, str):
        yield obj


def _collect_scan_fields(scan: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    columns = scan.get("columns")
    if isinstance(columns, list):
        fields.update(str(c) for c in columns if isinstance(c, str))
    for key in ("filter", "filter2", "sort"):
        obj = scan.get(key)
        if isinstance(obj, (dict, list)):
            for token in _extract_strings(obj):
                if token and " " not in token and "/" not in token:
                    fields.add(token)
    return fields


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "numeric"
    return "string"


def _infer_field_type(field: str, scan: dict[str, Any]) -> str:
    columns = scan.get("columns")
    if isinstance(columns, list) and field in columns:
        idx = columns.index(field)
        rows = scan.get("data", [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            dval = row.get("d")
            if isinstance(dval, list) and idx < len(dval):
                val = dval[idx]
                if val not in (None, ""):
                    return _infer_type(val)
    return "string"


def find_missing_fields(
    meta: dict[str, Any] | Path,
    scan: dict[str, Any] | Path,
    status: pd.DataFrame | Path | None = None,
) -> list[dict[str, str]]:
    """Return list of fields used in scan but absent from metainfo."""

    if isinstance(meta, Path):
        meta = _load_json(meta)
    if isinstance(scan, Path):
        scan = _load_json(scan)

    meta_fields: set[str] = set()
    for item in meta.get("fields", []) + meta.get("data", {}).get("fields", []):
        name = None
        if isinstance(item, dict):
            name = item.get("name") or item.get("id")
        elif hasattr(item, "get"):
            name = item.get("name") or item.get("id")
        if isinstance(name, str):
            meta_fields.add(name)

    status_fields: set[str] = set()
    if isinstance(status, pd.DataFrame):
        status_fields = set(status.get("field", []))
    elif isinstance(status, Path) and status.exists():
        try:
            df = pd.read_csv(status, sep="\t")
        except Exception:
            df = pd.DataFrame()
        status_fields = {str(v).strip() for v in df.get("field", [])}

    known = meta_fields | status_fields
    used = _collect_scan_fields(scan)
    missing = sorted(used - known)

    result: list[dict[str, str]] = []
    for name in missing:
        ftype = _infer_field_type(name, scan)
        result.append({"name": name, "source": "scan", "type": ftype})
    return result
