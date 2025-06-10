import logging
import os
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry
import requests_cache

logger = logging.getLogger(__name__)


class TradingViewAPI:
    """Minimal wrapper around TradingView Scanner API."""

    BASE_URL = "https://scanner.tradingview.com"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        base_url: str | None = None,
        timeout: int = 10,
        cache: bool | None = None,
    ) -> None:
        """Create API wrapper.

        Parameters
        ----------
        session : requests.Session | None
            Custom session instance. If provided, caching settings are ignored.
        base_url : str | None
            Override default base URL.
        timeout : int
            Request timeout in seconds.
        cache : bool | None
            Enable requests caching if True or if ``TV_CACHE`` env var is set.
        """

        use_cache = bool(os.environ.get("TV_CACHE")) if cache is None else cache
        if session:
            self.session = session
        elif use_cache:
            expire = int(os.environ.get("TV_CACHE_EXPIRE", 86400))
            self.session = requests_cache.CachedSession(
                "tv_api_cache", expire_after=expire
            )
        else:
            self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.setdefault("User-Agent", "tv-generator")
        self.base_url = base_url or os.environ.get("TV_BASE_URL", self.BASE_URL)
        self.timeout = int(os.environ.get("TV_TIMEOUT", timeout))
        self._valid_scopes = {
            "crypto",
            "forex",
            "futures",
            "america",
            "bond",
            "cfd",
            "coin",
            "stocks",
        }

    def _request(
        self, method: str, url: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Internal helper to send a request and parse JSON."""
        logger.debug("%s %s", method.upper(), url)
        try:
            r = self.session.request(method, url, json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("Request error: %s", exc)
            raise
        logger.debug("Response status %s", r.status_code)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            logger.error("HTTP error: %s - %s", r.status_code, r.text)
            raise
        try:
            return r.json()
        except ValueError as exc:
            logger.error("Invalid JSON: %s", r.text)
            raise ValueError("Invalid JSON received from TradingView") from exc

    def _url(self, scope: str, endpoint: str) -> str:
        if scope not in self._valid_scopes:
            raise ValueError(
                f"Invalid scope '{scope}', must be one of {sorted(self._valid_scopes)}"
            )
        return f"{self.base_url}/{scope}/{endpoint}"

    def scan(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send GET /{scope}/scan and return JSON."""
        url = self._url(scope, "scan")
        return self._request("GET", url, payload)

    def metainfo(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch metainfo for scope."""
        url = self._url(scope, "metainfo")
        return self._request("POST", url, payload)

    def search(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/search."""
        url = self._url(scope, "search")
        return self._request("POST", url, payload)

    def history(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/history."""
        url = self._url(scope, "history")
        return self._request("POST", url, payload)

    def summary(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/summary."""
        url = self._url(scope, "summary")
        return self._request("POST", url, payload)
