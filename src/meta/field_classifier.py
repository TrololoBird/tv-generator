from __future__ import annotations

import re
from typing import Any, Dict

# TradingView numeric types
_NUMERIC_TYPES = {
    "number",
    "price",
    "fundamental_price",
    "percent",
    "integer",
    "float",
    "duration",
    "percentage",
}

_CUSTOM_PATTERNS = [r"^TV_Custom\.", r"_impact_score$", r"^BTC_", r"^custom_"]


def _is_custom(name: str) -> bool:
    for pat in _CUSTOM_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


def classify_fields(columns: Dict[str, Dict[str, Any]]) -> Dict[str, list[str]]:
    """Return field classification mapping."""

    result: Dict[str, list[str]] = {
        "numeric": [],
        "string": [],
        "custom": [],
        "supports_timeframes": [],
        "daily_only": [],
        "discovered": [],
    }

    supports_tf: set[str] = set()

    for name, info in columns.items():
        base = name.split("|", 1)[0]
        ftype = str(info.get("tv_type") or info.get("type") or "")
        if ftype in _NUMERIC_TYPES:
            result["numeric"].append(base)
        else:
            result["string"].append(base)

        if _is_custom(base):
            result["custom"].append(base)

        if "|" in name:
            supports_tf.add(base)

        if str(info.get("source")) == "scan":
            result["discovered"].append(base)

    # determine daily_only indicators
    for base in result["numeric"]:
        if base in supports_tf:
            continue
        if re.fullmatch(r"[A-Z]+[A-Z0-9\[\]]*", base):
            result["daily_only"].append(base)

    result["supports_timeframes"] = sorted(supports_tf)
    for key in result:
        result[key] = sorted(set(result[key]))
    return result


__all__ = ["classify_fields"]
