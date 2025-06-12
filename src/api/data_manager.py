import pandas as pd
from typing import Any
from src.models import MetaInfoResponse


def build_field_status(meta: MetaInfoResponse, scan: dict) -> pd.DataFrame:
    """Return status for each field from meta based on scan results."""
    rows = scan.get("data", []) if isinstance(scan, dict) else []
    if not isinstance(rows, list):
        rows = []

    result = []
    for idx, field in enumerate(meta.fields):
        missing = False
        values: list[Any] = []
        for row in rows:
            dval = row.get("d") if isinstance(row, dict) else None
            if isinstance(dval, list) and idx < len(dval):
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
