import logging
import os
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


class TradingViewAPI:
    """Minimal wrapper around TradingView Scanner API."""

    BASE_URL = "https://scanner.tradingview.com"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        base_url: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.session = session or requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.setdefault("User-Agent", "tv-generator")
        self.base_url = base_url or os.environ.get("TV_BASE_URL", self.BASE_URL)
        self.timeout = int(os.environ.get("TV_TIMEOUT", timeout))

    def scan(self, market: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send POST /{market}/scan and return JSON."""
        url = f"{self.base_url}/{market}/scan"
        logger.debug("POST %s", url)
        r = self.session.post(url, json=payload, timeout=self.timeout)
        logger.debug("Response status %s", r.status_code)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as exc:
            logger.error("Invalid JSON: %s", r.text)
            raise ValueError("Invalid JSON received from TradingView") from exc

    def metainfo(self, market: str) -> Dict[str, Any]:
        """Fetch metainfo for market."""
        url = f"{self.base_url}/{market}/metainfo"
        logger.debug("POST %s", url)
        r = self.session.post(url, json={}, timeout=self.timeout)
        logger.debug("Response status %s", r.status_code)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as exc:
            logger.error("Invalid JSON: %s", r.text)
            raise ValueError("Invalid JSON received from TradingView") from exc
