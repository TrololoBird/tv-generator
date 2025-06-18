"""Project-wide constants and shared type hints."""

from typing import Literal

#: List of supported TradingView API scopes.
SCOPES = [
    "crypto",
    "forex",
    "futures",
    "america",
    "bond",
    "cfd",
    "coin",
    "stocks",
]

#: Literal type representing supported TradingView markets.
Market = Literal[
    "crypto",
    "forex",
    "futures",
    "america",
    "bond",
    "cfd",
    "coin",
    "stocks",
]

#: Generation mode for specification creation.
GenerationMode = Literal["default", "include_missing"]
