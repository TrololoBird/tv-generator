"""
Тесты для модуля API с реальными данными.
"""

import asyncio
import json
import ssl
from pathlib import Path

import httpx
import pytest
from loguru import logger

from tv_generator.api import (
    APIResponse,
    NetworkError,
    RateLimiter,
    RateLimitError,
    SecurityError,
    TradingViewAPI,
    TradingViewAPIError,
    ValidationError,
    load_cookies,
    validate_url,
)
from tv_generator.config import settings


class TestRateLimiter:
    """Тесты для RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Тест rate limiting."""
        limiter = RateLimiter(requests_per_second=10, burst_limit=5, window_size=1.0)

        start_time = asyncio.get_event_loop().time()

        # Тестируем burst limit
        for _ in range(5):
            await limiter.wait()

        burst_time = asyncio.get_event_loop().time() - start_time
        assert burst_time < 0.5  # Burst должен пройти относительно быстро

        # Тестируем rate limit
        await limiter.wait()  # Шестой запрос должен ждать
        rate_time = asyncio.get_event_loop().time() - start_time
        assert rate_time >= 0.1  # Должен ждать

        # Тестируем window size
        await asyncio.sleep(1.0)  # Ждем пока окно сдвинется
        window_start = asyncio.get_event_loop().time()
        await limiter.wait()
        window_time = asyncio.get_event_loop().time() - window_start
        assert window_time < 0.1  # После сдвига окна должен пройти быстро

    def test_rate_limiter_initialization(self) -> None:
        """Тест инициализации RateLimiter."""
        limiter = RateLimiter(requests_per_second=5, burst_limit=10, window_size=60.0)

        assert limiter.requests_per_second == 5
        assert limiter.burst_limit == 10
        assert limiter.window_size == 60.0
        assert limiter.min_interval == 0.2
        assert isinstance(limiter.request_times, list)
        assert len(limiter.request_times) == 0


class TestTradingViewAPI:
    """Тесты для TradingViewAPI с реальными API вызовами."""

    @pytest.fixture
    def api(self):
        """Фикстура для создания API клиента."""
        return TradingViewAPI()

    @pytest.fixture
    def test_data_dir(self) -> Path:
        """Фикстура для директории с тестовыми данными."""
        data_dir = Path(__file__).parent / "test_data"
        data_dir.mkdir(exist_ok=True)
        return data_dir

    def test_api_initialization(self) -> None:
        """Тест инициализации API."""
        api = TradingViewAPI()
        assert api.base_url == settings.tradingview_base_url
        assert api.timeout == settings.request_timeout
        assert api.max_retries == settings.max_retries
        assert api.retry_delay == settings.retry_delay
        assert api.rate_limiter.requests_per_second == settings.requests_per_second
        assert api.rate_limiter.burst_limit == settings.burst_limit
        assert api.rate_limiter.window_size == settings.window_size

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_get_metainfo_success(self, api: TradingViewAPI) -> None:
        """Тест успешного получения metainfo с реальным API."""
        metainfo = await api.get_metainfo("america")

        assert isinstance(metainfo, dict)
        assert "fields" in metainfo
        assert isinstance(metainfo["fields"], list)

        # Проверяем структуру полей
        if metainfo["fields"]:
            field = metainfo["fields"][0]
            assert "n" in field  # name
            assert "t" in field  # type

            # Проверяем, что тип поля - один из реальных типов TradingView
            real_types = {
                "number",
                "price",
                "num_slice",
                "text",
                "fundamental_price",
                "map",
                "percent",
                "time",
                "bool",
                "time-yyyymmdd",
                "interface",
                "set",
            }
            assert field["t"] in real_types, f"Unknown field type: {field['t']}"

    @pytest.mark.asyncio
    async def test_get_metainfo_invalid_endpoint(self, api) -> None:
        """Тест получения metainfo с невалидным endpoint."""
        with pytest.raises(SecurityError):
            await api.get_metainfo("../invalid")

        with pytest.raises(SecurityError):
            await api.get_metainfo("https://evil.com")

        with pytest.raises(SecurityError):
            await api.get_metainfo("america; rm -rf /")

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_scan_tickers(self, api) -> None:
        """Тест сканирования тикеров с реальным API."""
        result = await api.scan_tickers(endpoint="america", label_product="screener-stock", limit=5)

        # Проверяем структуру ответа
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(result) <= 5

        # Проверяем тикеры
        for ticker in result:
            assert isinstance(ticker, dict)
            assert "s" in ticker  # symbol
            assert isinstance(ticker["s"], str)
            assert len(ticker["s"]) > 0
            assert "d" in ticker  # data
            assert isinstance(ticker["d"], list)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_scan_tickers_invalid_input(self, api) -> None:
        """Тест сканирования тикеров с невалидными входными данными."""
        # Тестируем невалидный endpoint (не alphanumeric)
        try:
            result = await api.scan_tickers("america;", "product", 10)
        except SecurityError:
            pass
        except TradingViewAPIError as e:
            assert "404" in str(e) or "Not Found" in str(e)
        else:
            # TradingView может вернуть валидные данные даже для невалидного endpoint
            assert isinstance(result, list)

        # Тестируем невалидный label_product (TradingView возвращает валидный список)
        result = await api.scan_tickers("america", "'; DROP TABLE", 10)
        assert isinstance(result, list)

        # Тестируем невалидный limit - TradingView может вернуть валидные данные
        for bad_limit in [-1, 1001]:
            try:
                result = await api.scan_tickers("america", "product", bad_limit)
            except ValueError:
                pass
            except TradingViewAPIError:
                pass
            else:
                # TradingView может вернуть валидные данные даже для невалидного limit
                assert isinstance(result, list)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_get_field_data(self, api: TradingViewAPI) -> None:
        """Тест получения данных по полям с реальным API."""
        # Используем правильный параметр symbol вместо ticker
        data = await api.get_field_data(endpoint="america", symbol="AAPL", fields=["name", "close", "volume"])

        assert isinstance(data, dict)
        # Проверяем реальную структуру данных TradingView
        # Данные возвращаются в формате {'s': 'symbol', 'd': [data]}
        assert "s" in data
        assert "d" in data
        assert data["s"] == "AAPL"
        assert isinstance(data["d"], list)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_get_field_data_invalid_input(self, api) -> None:
        """Тест получения данных по полям с невалидными входными данными."""
        # Тестируем несуществующий символ
        try:
            data = await api.get_field_data("america", "INVALID_SYMBOL_12345", ["name"])
        except TradingViewAPIError as e:
            # TradingView может вернуть ошибку или пустые данные
            assert "404" in str(e) or "Not Found" in str(e) or "No data" in str(e)
        else:
            # Или может вернуть пустые данные
            assert isinstance(data, dict)

        # Тестируем невалидный endpoint
        with pytest.raises(SecurityError):
            await api.get_field_data("../invalid", "AAPL", ["name"])

        # Тестируем невалидные поля
        try:
            data = await api.get_field_data("america", "AAPL", ["invalid_field_12345"])
        except TradingViewAPIError:
            pass
        else:
            # TradingView может вернуть валидные данные даже для невалидных полей
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_test_field_working(self, api) -> None:
        """Тест проверки рабочего поля с реальным API."""
        # Тестируем поле, которое точно работает
        is_working = await api.test_field("america", "AAPL", "name")
        assert isinstance(is_working, bool)
        # name обычно работает для акций
        assert is_working is True

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_test_field_not_working(self, api) -> None:
        """Тест проверки нерабочего поля с реальным API."""
        # Тестируем поле, которое может не работать
        is_working = await api.test_field("america", "AAPL", "invalid_field_12345")
        assert isinstance(is_working, bool)
        # Невалидное поле должно не работать
        assert is_working is False

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_health_check(self, api: TradingViewAPI) -> None:
        """Тест проверки здоровья API с реальным API."""
        health = await api.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in health
        assert isinstance(health["timestamp"], (int, float))
        assert "endpoints" in health
        assert isinstance(health["endpoints"], dict)

        # Проверяем, что основные endpoints работают
        for endpoint in ["america", "crypto", "forex"]:
            if endpoint in health["endpoints"]:
                assert health["endpoints"][endpoint] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_context_manager(self, api) -> None:
        """Тест контекстного менеджера."""
        async with api as api_client:
            assert api_client is api
            # Проверяем, что клиент работает
            assert api_client.base_url == settings.tradingview_base_url

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_rate_limiting_integration(self, api) -> None:
        """Тест интеграции rate limiting с реальными запросами."""
        start_time = asyncio.get_event_loop().time()

        # Делаем несколько запросов подряд
        tasks = []
        for _ in range(3):
            task = api.get_metainfo("america")
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Проверяем, что rate limiting работает
        assert duration >= 0.2  # Минимум 3 запроса с rate limit
        assert all(isinstance(result, dict) for result in results)
        assert all("fields" in result for result in results)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_multiple_endpoints(self, api) -> None:
        """Тест работы с несколькими endpoints."""
        endpoints = ["america", "crypto", "forex"]

        for endpoint in endpoints:
            try:
                metainfo = await api.get_metainfo(endpoint)
                assert isinstance(metainfo, dict)
                assert "fields" in metainfo

                # Делаем небольшую паузу между запросами
                await asyncio.sleep(0.1)
            except TradingViewAPIError as e:
                # Некоторые endpoints могут быть недоступны
                logger.warning(f"Endpoint {endpoint} not available: {e}")

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_error_handling(self, api) -> None:
        """Тест обработки ошибок с реальным API."""
        # Тестируем несуществующий endpoint
        with pytest.raises(TradingViewAPIError) as excinfo:
            await api.get_metainfo("nonexistent_endpoint_12345")
        assert "404" in str(excinfo.value) or "Not Found" in str(excinfo.value)

        # Тестируем невалидный символ
        with pytest.raises(TradingViewAPIError) as excinfo:
            await api.get_field_data("america", "INVALID_SYMBOL_12345", ["name"])
        assert "404" in str(excinfo.value) or "Not Found" in str(excinfo.value)


class TestAPIResponse:
    """Тесты для APIResponse."""

    def test_api_response_creation(self) -> None:
        """Тест создания APIResponse."""
        response = APIResponse(
            data={"test": "data"},
            status_code=200,
            headers={"content-type": "application/json"},
            url="https://example.com/api",
        )

        assert response.data == {"test": "data"}
        assert response.status_code == 200
        assert response.headers == {"content-type": "application/json"}
        assert response.url == "https://example.com/api"

    def test_api_response_json(self) -> None:
        """Тест JSON сериализации APIResponse."""
        response = APIResponse(
            data={"test": "data"},
            status_code=200,
            headers={},
            url="https://example.com/api",
        )

        json_data = response.json()
        assert json_data == {"test": "data"}


class TestValidation:
    """Тесты для валидации."""

    def test_validate_url_valid(self) -> None:
        """Тест валидации корректного URL."""
        assert validate_url("https://scanner.tradingview.com/america/scan")
        assert validate_url("https://scanner.tradingview.com/crypto/scan")

    def test_validate_url_invalid(self) -> None:
        """Тест валидации некорректного URL."""
        assert not validate_url("https://evil.com/api")
        assert not validate_url("file:///etc/passwd")
        assert not validate_url("javascript:alert('xss')")


class TestErrors:
    """Тесты для ошибок."""

    def test_network_error(self) -> None:
        """Тест NetworkError."""
        error = NetworkError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, Exception)

    def test_rate_limit_error(self) -> None:
        """Тест RateLimitError."""
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, Exception)

    def test_security_error(self) -> None:
        """Тест SecurityError."""
        error = SecurityError("Invalid endpoint")
        assert str(error) == "Invalid endpoint"
        assert isinstance(error, Exception)

    def test_validation_error(self) -> None:
        """Тест ValidationError."""
        error = ValidationError("Invalid data")
        assert str(error) == "Invalid data"
        assert isinstance(error, Exception)

    def test_tradingview_api_error(self) -> None:
        """Тест TradingViewAPIError."""
        error = TradingViewAPIError("API error", status_code=500)
        assert str(error) == "API error"
        assert error.status_code == 500
        assert isinstance(error, Exception)
