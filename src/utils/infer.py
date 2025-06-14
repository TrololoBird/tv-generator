from __future__ import annotations

import pandas as pd
from datetime import datetime


def infer_type(value: pd.Series | str | int | float | bool | None) -> str:
    """Infer OpenAPI type from a sample value.

    Strings equal to ``"true"`` or ``"false"`` (case-insensitive) are
    interpreted as boolean values.
    """
    if isinstance(value, pd.Series):
        series = value.dropna()
        if series.empty:
            return "string"
        types = {infer_type(v) for v in series}
        if "number" in types and "integer" in types:
            types.discard("integer")
            types.add("number")
        return types.pop() if len(types) == 1 else "string"

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

    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            pass
        else:
            if "." in value or "e" in value.lower():
                return "number"

    try:
        num = float(str(value))
    except (ValueError, TypeError):
        return "string"

    if num.is_integer():
        return "integer"
    return "number"
