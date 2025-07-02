"""
API клиент для работы с TradingView Scanner API.
"""

import asyncio
import json as _json
import os
import ssl
import time
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import certifi
import httpx
from loguru import logger

from .config import settings


@dataclass
class APIResponse:
    """Ответ от API."""

    data: Any
    status_code: int
    headers: dict[str, str]
    url: str


class RateLimiter:
    """Rate limiter для API запросов с поддержкой burst и sliding window."""

    def __init__(self, requests_per_second: int, burst_limit: int = 10, window_size: float = 60.0) -> None:
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit
        self.window_size = window_size
        self.request_times: list[float] = []
        self.min_interval = 1.0 / requests_per_second

    def _cleanup_old_requests(self, current_time: float) -> None:
        """Очистка старых запросов из окна."""
        cutoff = current_time - self.window_size
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.pop(0)

    async def wait(self) -> None:
        """Ожидание для соблюдения rate limit с учетом burst."""
        current_time = time.time()
        self._cleanup_old_requests(current_time)

        # Проверка burst limit
        if len(self.request_times) >= self.burst_limit:
            wait_time = self.request_times[0] + self.window_size - current_time
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                current_time = time.time()
                self._cleanup_old_requests(current_time)

        # Проверка rate limit
        if self.request_times:
            time_since_last = current_time - self.request_times[-1]
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)
                current_time = time.time()

        self.request_times.append(current_time)


class TradingViewAPIError(Exception):
    """Базовый класс для ошибок TradingView API."""

    pass


class SecurityError(TradingViewAPIError):
    """Ошибки, связанные с безопасностью."""

    pass


class NetworkError(TradingViewAPIError):
    """Ошибки, связанные с сетевыми проблемами."""

    pass


class RateLimitError(TradingViewAPIError):
    """Ошибки, связанные с превышением лимита запросов."""

    pass


class ValidationError(TradingViewAPIError):
    """Ошибки валидации данных."""

    pass


def validate_url(url: str) -> bool:
    """Проверка безопасности URL."""
    try:
        parsed = urlparse(url)
        return all(
            [
                parsed.scheme in ("http", "https"),
                parsed.netloc.endswith(".tradingview.com"),
                not parsed.netloc.startswith("."),
                "//" not in parsed.path,
                ".." not in parsed.path,
            ]
        )
    except Exception:
        return False


def load_cookies(path: str) -> dict[str, str] | None:
    """Загрузка cookies из файла (Netscape, JSON, rookiepy)."""
    if not path or not os.path.exists(path):
        return None

    if not os.path.isfile(path):
        raise SecurityError("Cookie path must be a file")

    # Проверка размера файла
    if os.path.getsize(path) > 1024 * 1024:  # 1MB
        raise SecurityError("Cookie file too large")

    # Попытка загрузить как Netscape
    try:
        cj = MozillaCookieJar()
        cj.load(path, ignore_discard=True, ignore_expires=True)
        cookies = {c.name: c.value for c in cj}
        if cookies:
            return cookies
    except Exception:
        pass

    # Попытка загрузить как JSON
    try:
        with open(path, encoding="utf-8") as f:
            data = _json.load(f)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            # Chrome/rookiepy формат
            cookies = {c["name"]: c["value"] for c in data if isinstance(c, dict) and "name" in c and "value" in c}
            if cookies:
                return cookies
    except Exception:
        pass

    # Попытка rookiepy (если установлен)
    try:
        import rookiepy

        cookies = rookiepy.to_cookiejar(rookiepy.chrome([".tradingview.com"]))
        return {c.name: c.value for c in cookies}
    except Exception:
        pass

    return None


class TradingViewAPI:
    """Клиент для работы с TradingView Scanner API."""

    def __init__(self):
        if not validate_url(settings.tradingview_base_url):
            raise SecurityError("Invalid base URL")

        self.base_url = settings.tradingview_base_url
        self.timeout = settings.request_timeout
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay
        self.rate_limiter = RateLimiter(
            settings.requests_per_second, burst_limit=settings.burst_limit, window_size=settings.window_size
        )

        # SSL контекст с проверкой сертификатов
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        # Загрузка cookies
        cookies = None
        if settings.cookies_path:
            try:
                cookies = load_cookies(settings.cookies_path)
                if cookies:
                    logger.info(f"Loaded {len(cookies)} cookies from {settings.cookies_path}")
                else:
                    logger.warning(f"No cookies loaded from {settings.cookies_path}")
            except SecurityError as e:
                logger.error(f"Security error loading cookies: {e}")
                raise

        # HTTP клиент с улучшенной безопасностью
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": f"TradingView-OpenAPI-Generator/{settings.version}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
            cookies=cookies,
            verify=ssl_context,
            follow_redirects=False,  # Запрещаем автоматические редиректы
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _validate_endpoint(self, endpoint: str) -> None:
        """Проверка безопасности endpoint."""
        if not isinstance(endpoint, str):
            raise SecurityError("Endpoint must be a string")

        # Проверка на опасные символы
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "{", "}", "[", "]", '"', "'", "<", ">", "\\", "/", ".."]
        for char in dangerous_chars:
            if char in endpoint:
                raise SecurityError(f"Endpoint contains dangerous character: {char}")

        # Проверка на инъекции
        if ".." in endpoint or "//" in endpoint:
            raise SecurityError("Endpoint contains path traversal attempt")

        # Проверка на SQL инъекции
        sql_patterns = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "UNION"]
        for pattern in sql_patterns:
            if pattern.upper() in endpoint.upper():
                raise SecurityError(f"Endpoint contains SQL injection attempt: {pattern}")

        # Проверка на допустимые символы (только буквы, цифры, дефисы, подчеркивания)
        if not all(c.isalnum() or c in "-_" for c in endpoint):
            raise SecurityError("Endpoint contains invalid characters")

    def _validate_request_data(self, data: dict | None) -> None:
        """Проверка безопасности данных запроса."""
        if data is not None:
            if not isinstance(data, dict):
                raise SecurityError("Request data must be a dictionary")
            # Проверка на максимальный размер
            if len(_json.dumps(data)) > 1024 * 1024:  # 1MB
                raise SecurityError("Request data too large")

    async def _make_request(self, method: str, url: str, data: dict | None = None, **kwargs) -> APIResponse:
        """Выполнение HTTP запроса с обработкой ошибок и rate limiting."""
        if not validate_url(url):
            raise SecurityError(f"Invalid URL: {url}")

        self._validate_request_data(data)

        for attempt in range(self.max_retries + 1):
            try:
                await self.rate_limiter.wait()

                response = await self.client.request(method, url, json=data, **kwargs)

                # Проверка Content-Type
                content_type = response.headers.get("content-type", "")
                if not any(ct in content_type.lower() for ct in settings.allowed_content_types):
                    raise SecurityError(f"Invalid content type: {content_type}")

                # Проверка размера ответа
                if len(response.content) > settings.max_request_size:
                    raise SecurityError("Response too large")

                if response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")

                response.raise_for_status()

                return APIResponse(
                    data=response.json(),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    url=str(response.url),
                )

            except httpx.TimeoutException:
                if attempt == self.max_retries:
                    raise NetworkError("Request timed out after all retries")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.NetworkError as e:
                if attempt == self.max_retries:
                    raise NetworkError(f"Network error: {str(e)}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    if attempt == self.max_retries:
                        raise NetworkError(f"Server error: {e.response.status_code}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise TradingViewAPIError(f"HTTP {e.response.status_code}: {str(e)}")

            except Exception as e:
                raise TradingViewAPIError(f"Unexpected error: {str(e)}")

        raise TradingViewAPIError("All retry attempts failed")

    async def get_metainfo(self, endpoint: str) -> dict[str, Any]:
        """Получение metainfo для указанного эндпоинта."""
        self._validate_endpoint(endpoint)
        url = f"{self.base_url}/{endpoint}/metainfo"
        response = await self._make_request("GET", url)
        return response.data

    async def scan_tickers(
        self, endpoint: str, label_product: str, limit: int = 100, filters: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Сканирование тикеров для указанного рынка."""
        self._validate_endpoint(endpoint)
        url = f"{self.base_url}/{endpoint}/scan"

        # Базовые фильтры - убираем проблемный market_cap_basic
        base_filters = []

        if filters:
            base_filters.extend(filters)

        data = {
            "filter": base_filters,
            "options": {"lang": "en"},
            "range": [0, limit],
            "markets": [label_product],
            "symbols": {"query": {"types": []}},
            "columns": ["name", "close", "change", "change_abs", "volume"],
            "sort": {"sortBy": "name", "sortOrder": "asc"},
        }

        response = await self._make_request("POST", url, data=data)
        return response.data.get("data", [])

    async def get_field_data(
        self, endpoint: str, symbol: str, fields: list[str], label_product: str | None = None
    ) -> dict[str, Any]:
        """Получение данных по полям для указанного символа."""
        url = f"{self.base_url}/{endpoint}/scan"

        # Определяем label_product если не передан
        if not label_product:
            for market_config in settings.markets.values():
                if market_config["endpoint"] == endpoint:
                    label_product = market_config["label_product"]
                    break

        if not label_product:
            label_product = "america"  # Fallback

        data = {
            "filter": [{"left": "name", "operation": "equal", "right": symbol}],
            "options": {"lang": "en"},
            "range": [0, 1],
            "markets": [label_product],
            "symbols": {"query": {"types": []}},
            "columns": fields,
            "sort": {"sortBy": "name", "sortOrder": "asc"},
        }

        response = await self._make_request("POST", url, data=data)
        data_list = response.data.get("data", [])
        return data_list[0] if data_list else {}

    async def test_field(self, endpoint: str, symbol: str, field: str, label_product: str | None = None) -> bool:
        """Тестирование работоспособности поля."""
        try:
            data = await self.get_field_data(endpoint, symbol, [field], label_product)
            value = data.get(field)
            return value is not None and value != ""
        except Exception as e:
            logger.debug(f"Field {field} test failed: {e}")
            return False

    async def get_market_info(self, endpoint: str) -> dict[str, Any]:
        """Получение информации о рынке."""
        try:
            metainfo = await self.get_metainfo(endpoint)
            return {
                "endpoint": endpoint,
                "metainfo": metainfo,
                "fields_count": len(metainfo.get("fields", [])),
                "available": True,
            }
        except Exception as e:
            logger.error(f"Failed to get market info for {endpoint}: {e}")
            return {"endpoint": endpoint, "metainfo": {}, "fields_count": 0, "available": False, "error": str(e)}

    async def health_check(self) -> dict[str, Any]:
        """Проверка здоровья API."""
        health_status = {"status": "healthy", "timestamp": time.time(), "endpoints": {}}

        # Проверяем каждый эндпоинт
        unique_endpoints = set()
        for market_config in settings.markets.values():
            unique_endpoints.add(market_config["endpoint"])

        healthy_count = 0
        total_endpoints = len(unique_endpoints)

        for endpoint in unique_endpoints:
            try:
                await self.get_metainfo(endpoint)
                health_status["endpoints"][endpoint] = "healthy"
                healthy_count += 1
            except Exception as e:
                health_status["endpoints"][endpoint] = f"unhealthy: {e}"

        # Определяем общий статус
        if healthy_count == total_endpoints:
            health_status["status"] = "healthy"
        elif healthy_count >= total_endpoints * 0.7:  # 70% эндпоинтов работают
            health_status["status"] = "healthy"
        elif healthy_count >= total_endpoints * 0.5:  # 50% эндпоинтов работают
            health_status["status"] = "degraded"
        else:
            health_status["status"] = "unhealthy"

        return health_status
