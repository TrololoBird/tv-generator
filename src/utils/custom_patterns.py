from __future__ import annotations

import re
from typing import List

_CUSTOM_PATTERNS: List[str] = [
    r"^TV_Custom\.",
    r"_impact_score$",
    r"^BTC_",
    r"^custom_",
]


def _is_custom(name: str) -> bool:
    for pat in _CUSTOM_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


__all__ = ["_CUSTOM_PATTERNS", "_is_custom"]
