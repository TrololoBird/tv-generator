from __future__ import annotations

import pandas as pd


def infer_type(value: pd.Series | str | int | float | None) -> str:
    """Infer OpenAPI type from a sample value."""
    if pd.isna(value):
        return "string"
    try:
        float(str(value))
        return "number"
    except (ValueError, TypeError):
        return "string"
