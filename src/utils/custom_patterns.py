from __future__ import annotations

import re
from typing import List

"""Helper utilities for detecting TradingView custom field names."""

_CUSTOM_PATTERNS: List[str] = [
    r"^TV_Custom\.",
    r"_impact_score$",
    r"^BTC_",
    r"^custom_",
]


def _is_custom(name: str) -> bool:
    """Return ``True`` if ``name`` looks like a custom TradingView field.

    Parameters
    ----------
    name : str
        Field name from TradingView metainfo or scan results.

    Returns
    -------
    bool
        ``True`` if the name matches any of the known custom patterns,
        otherwise ``False``.
    """

    for pat in _CUSTOM_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


__all__ = ["_CUSTOM_PATTERNS", "_is_custom"]
