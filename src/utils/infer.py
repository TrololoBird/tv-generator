from __future__ import annotations

import pandas as pd
from datetime import datetime


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

    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "string"
        except ValueError:
            pass

    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return "integer"

    try:
        num = float(str(value))
    except (ValueError, TypeError):
        return "string"

    if num.is_integer():
        return "integer"
    return "number"
