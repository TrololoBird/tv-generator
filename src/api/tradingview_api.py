import logging
import os
from typing import Any, Dict, Optional, cast

import requests
from requests.adapters import HTTPAdapter, Retry
import requests_cache

from src.constants import SCOPES
from pydantic import ValidationError
from src.models import (
    MetaInfoResponse,
    ScanResponse,
    SearchResponse,
    HistoryResponse,
    SummaryResponse,
)

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

    def _request(
        self, scope: str, endpoint: str, method: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Internal helper to send a request and parse JSON."""
        url = self._url(scope, endpoint)
        logger.debug("%s %s", method.upper(), url)
        try:
            r = self.session.request(method, url, json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("Request error: %s", exc)
            raise
        self._log_response(r)
        try:
            r.raise_for_status()
        except requests.HTTPError as exc:
            logger.error("HTTP error: %s - %s", r.status_code, r.text)
            raise ValueError(f"TradingView HTTP {r.status_code}: {r.text}") from exc
        try:
            return cast(Dict[str, Any], r.json())
        except ValueError as exc:
            logger.error("Invalid JSON: %s", r.text)
            raise ValueError("Invalid JSON received from TradingView") from exc

    def _log_response(self, response: requests.Response) -> None:
        """Log basic details about the HTTP response."""
        logger.debug(
            "Response: %s %s",
            response.status_code,
            response.headers.get("content-type", ""),
        )

    def _url(self, scope: str, endpoint: str) -> str:
        if scope not in SCOPES:
            raise ValueError(
                f"Invalid scope '{scope}', must be one of {sorted(SCOPES)}"
            )
        return f"{self.base_url}/{scope}/{endpoint}"

    def scan(self, scope: str, payload: Dict[str, Any]) -> ScanResponse:
        """Send POST /{scope}/scan with fallback to GET if needed."""
        url = self._url(scope, "scan")

        def _scan_get() -> ScanResponse:
            resp = self.session.get(url, timeout=self.timeout)
            self._log_response(resp)
            resp.raise_for_status()
            data_g = cast(Dict[str, Any], resp.json())
            return cast(ScanResponse, ScanResponse.parse_obj(data_g))

        response: requests.Response | None = None
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            self._log_response(response)
            response.raise_for_status()
            data = cast(Dict[str, Any], response.json())
        except requests.HTTPError as exc:
            status = response.status_code if response is not None else None
            if status in (400, 404):
                return _scan_get()
            logger.error(
                "HTTP error: %s - %s",
                status,
                exc.response.text if exc.response else "",
            )
            raise ValueError(
                f"TradingView HTTP {status}: "
                f"{exc.response.text if exc.response else ''}"
            ) from exc
        except requests.ConnectionError:
            return _scan_get()
        except ValueError:
            return _scan_get()

        return cast(ScanResponse, ScanResponse.parse_obj(data))

    def metainfo(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch metainfo for scope validated by ``MetaInfoResponse``."""
        data = self._request(scope, "metainfo", "POST", payload)
        MetaInfoResponse.parse_obj(data)
        return data

    def search(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/search validated by ``SearchResponse``."""
        data = self._request(scope, "search", "POST", payload)
        try:
            SearchResponse.parse_obj(data)
        except ValidationError as exc:
            raise ValueError("Invalid search response") from exc
        return data

    def history(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/history validated by ``HistoryResponse``."""
        data = self._request(scope, "history", "POST", payload)
        try:
            HistoryResponse.parse_obj(data)
        except ValidationError as exc:
            raise ValueError("Invalid history response") from exc
        return data

    def summary(self, scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /{scope}/summary validated by ``SummaryResponse``."""
        data = self._request(scope, "summary", "POST", payload)
        try:
            SummaryResponse.parse_obj(data)
        except ValidationError as exc:
            raise ValueError("Invalid summary response") from exc
        return data
