import pandas as pd
from typing import Any
from src.models import MetaInfoResponse


def build_field_status(meta: MetaInfoResponse, scan: dict[str, Any]) -> pd.DataFrame:
    """Return DataFrame summarizing scan results for each field.

    The returned frame has exactly four columns in this order:
    ``["field", "tv_type", "status", "sample_value"]``. ``tv_type`` is taken
    from ``field.t`` in the supplied ``meta`` model.
    """
    rows = scan.get("data", []) if isinstance(scan, dict) else []
    if not isinstance(rows, list):
        rows = []

    # Mapping from field name to index in scan rows. Prefer explicit
    # ``columns`` mapping if present, otherwise fall back to the order of
    # ``meta.fields``.  This avoids relying solely on enumeration and
    # works even if the field order differs between ``meta`` and ``scan``.
    columns = scan.get("columns")
    if isinstance(columns, list) and all(isinstance(c, str) for c in columns):
        index_map = {name: i for i, name in enumerate(columns)}
    else:
        index_map = {f.n: i for i, f in enumerate(meta.fields)}

    result = []
    for field in meta.fields:
        idx = index_map.get(field.n)
        missing = False
        values: list[Any] = []
        for row in rows:
            dval = row.get("d") if isinstance(row, dict) else None
            if isinstance(dval, list) and idx is not None and idx < len(dval):
                values.append(dval[idx])
            else:
                missing = True
                break
        if missing:
            status = "error"
            sample = ""
        else:
            non_zero = [v for v in values if v not in (None, "", [])]
            if non_zero:
                status = "ok"
                sample = non_zero[0]
            elif all(v is None for v in values):
                status = "null"
                sample = ""
            else:
                status = "empty"
                sample = ""
        result.append(
            {
                "field": field.n,
                "tv_type": field.t,
                "status": status,
                "sample_value": sample,
            }
        )
    return pd.DataFrame(result, columns=["field", "tv_type", "status", "sample_value"])
