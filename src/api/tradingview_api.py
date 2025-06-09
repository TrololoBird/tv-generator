import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class TradingViewAPI:
    """Minimal wrapper around TradingView Scanner API."""

    BASE_URL = "https://scanner.tradingview.com"

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    def scan(self, market: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send POST /{market}/scan and return JSON."""
        url = f"{self.BASE_URL}/{market}/scan"
        logger.debug("POST %s", url)
        r = self.session.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()

    def metainfo(self, market: str) -> Dict[str, Any]:
        """Fetch metainfo for market."""
        url = f"{self.BASE_URL}/{market}/metainfo"
        logger.debug("POST %s", url)
        r = self.session.post(url, json={}, timeout=10)
        r.raise_for_status()
        return r.json()
