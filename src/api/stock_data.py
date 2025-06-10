import logging
from typing import Any

from .tradingview_api import TradingViewAPI
from src.utils.payload import build_scan_payload

logger = logging.getLogger(__name__)


def fetch_recommendation(symbol: str, market: str = "stocks") -> Any:
    """Return trading recommendation for a symbol."""
    api = TradingViewAPI()
    payload = build_scan_payload([symbol], ["Recommend.All"])
    data = api.scan(market, payload)
    try:
        return data["data"][0]["d"][0]
    except (KeyError, IndexError) as exc:
        logger.error("Recommendation unavailable: %s", exc)
        raise ValueError("Recommendation unavailable") from exc


def fetch_stock_value(symbol: str, market: str = "stocks") -> Any:
    """Return current close price for a symbol."""
    api = TradingViewAPI()
    payload = build_scan_payload([symbol], ["close"])
    data = api.scan(market, payload)
    try:
        return data["data"][0]["d"][0]
    except (KeyError, IndexError) as exc:
        logger.error("Price unavailable: %s", exc)
        raise ValueError("Price unavailable") from exc
