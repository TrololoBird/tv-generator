from __future__ import annotations

import pandas as pd


def infer_type(value: pd.Series | str | int | float | bool | None) -> str:
    """Infer OpenAPI type from a sample value."""
    if isinstance(value, pd.Series):
        value = value.iloc[0]

    if pd.isna(value):
        return "string"

    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return "boolean"

    try:
        float(str(value))
        return "number"
    except (ValueError, TypeError):
        return "string"
