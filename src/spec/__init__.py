"""Helpers for OpenAPI spec generation."""

from .generator import (
    generate_spec_for_all_markets,
    generate_spec_for_market,
    detect_all_markets,
)

__all__ = [
    "generate_spec_for_all_markets",
    "generate_spec_for_market",
    "detect_all_markets",
]
