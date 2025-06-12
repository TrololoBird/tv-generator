import logging
from typing import Any

from .tradingview_api import TradingViewAPI
from pydantic import ValidationError
from src.utils.payload import build_scan_payload

logger = logging.getLogger(__name__)


def _fetch_field(symbol: str, scope: str, column: str, error_msg: str) -> Any:
    api = TradingViewAPI()
    payload = build_scan_payload([symbol], [column])
    try:
        data = api.scan(scope, payload)
    except ValidationError as exc:
        logger.error("Invalid scan response for %s in %s: %s", symbol, scope, exc)
        raise ValueError(f"{error_msg} for {symbol} in market {scope}") from exc
    try:
        return data["data"][0]["d"][0]
    except (KeyError, IndexError) as exc:
        logger.error("%s for %s in %s: %s", error_msg, symbol, scope, exc)
        raise ValueError(f"{error_msg} for {symbol} in market {scope}") from exc


def fetch_recommendation(symbol: str, market: str = "stocks") -> Any:
    """Return trading recommendation for a symbol."""
    return _fetch_field(symbol, market, "Recommend.All", "Recommendation unavailable")


def fetch_stock_value(symbol: str, market: str = "stocks") -> Any:
    """Return current close price for a symbol."""
    return _fetch_field(symbol, market, "close", "Price unavailable")
