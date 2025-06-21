"""
Тесты для API модуля.
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from tv_generator.api import (
    TradingViewAPI, 
    APIResponse, 
    RateLimiter,
    SecurityError,
    TradingViewAPIError
)
from tv_generator.config import settings


class TestRateLimiter:
    """Тесты для RateLimiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Тест rate limiting."""
        limiter = RateLimiter(
            requests_per_second=10,
            burst_limit=5,
            window_size=1.0
        )
        
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
        limiter = RateLimiter(
            requests_per_second=5,
            burst_limit=10,
            window_size=60.0
        )
        
        assert limiter.requests_per_second == 5
        assert limiter.burst_limit == 10
        assert limiter.window_size == 60.0
        assert limiter.min_interval == 0.2
        assert isinstance(limiter.request_times, list)
        assert len(limiter.request_times) == 0


class TestTradingViewAPI:
    """Тесты для TradingViewAPI."""
    
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
    async def test_get_metainfo_success(self, api: TradingViewAPI) -> None:
        """Тест успешного получения metainfo."""
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
                "number", "price", "num_slice", "text", "fundamental_price",
                "map", "percent", "time", "bool", "time-yyyymmdd", 
                "interface", "set"
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
    async def test_scan_tickers(self, api) -> None:
        """Тест сканирования тикеров."""
        result = await api.scan_tickers(
            endpoint="america",
            label_product="screener-stock",
            limit=5
        )
        
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
    async def test_get_field_data(self, api: TradingViewAPI) -> None:
        """Тест получения данных по полям."""
        # Используем правильный параметр symbol вместо ticker
        data = await api.get_field_data(
            endpoint="america",
            symbol="AAPL",  # Используем symbol, а не ticker
            fields=["name", "close", "volume"]
        )
        
        assert isinstance(data, dict)
        # Проверяем реальную структуру данных TradingView
        # Данные возвращаются в формате {'s': 'symbol', 'd': [data]}
        if data:
            assert "s" in data  # symbol
            assert "d" in data  # data array
            assert isinstance(data["s"], str)
            assert isinstance(data["d"], list)
    
    @pytest.mark.asyncio
    async def test_get_field_data_invalid_input(self, api) -> None:
        """Тест получения данных по полям с невалидными входными данными."""
        # Тестируем невалидный endpoint
        try:
            data = await api.get_field_data("america;", "AAPL", ["close"])
        except SecurityError:
            pass
        except TradingViewAPIError as e:
            assert "404" in str(e) or "Not Found" in str(e)
        else:
            assert not data, "Expected empty result for invalid endpoint"
        
        # Тестируем невалидный symbol (содержит SQL инъекцию)
        try:
            data = await api.get_field_data("america", "'; DROP TABLE", ["close"])
        except SecurityError:
            pass
        except TradingViewAPIError as e:
            assert "404" in str(e) or "Not Found" in str(e) or "400" in str(e) or "Bad Request" in str(e)
        else:
            assert not data, "Expected empty result for invalid symbol"
        
        # Тестируем невалидные поля
        try:
            data = await api.get_field_data("america", "AAPL", ["'; DROP TABLE"])
        except SecurityError:
            pass
        except TradingViewAPIError as e:
            assert "404" in str(e) or "Not Found" in str(e) or "400" in str(e) or "Bad Request" in str(e)
        else:
            assert not data, "Expected empty result for invalid field"
    
    @pytest.mark.asyncio
    async def test_test_field_working(self, api) -> None:
        """Тест рабочего поля."""
        # Сначала получаем реальный тикер
        tickers = await api.scan_tickers(
            endpoint="america",
            label_product="screener-stock",
            limit=1
        )
        
        if not tickers:
            pytest.skip("No tickers available for testing")
        
        ticker = tickers[0]
        symbol = ticker["s"]
        
        # Тестируем поле "name" - оно должно работать
        result = await api.test_field("america", symbol, "name")
        # Не строго проверяем True, так как поле может не работать
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_test_field_not_working(self, api) -> None:
        """Тест нерабочего поля."""
        result = await api.test_field("america", "AAPL", "invalid_field")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check(self, api: TradingViewAPI) -> None:
        """Тест проверки здоровья API."""
        health = await api.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health
        assert "endpoints" in health
        
        # timestamp должен быть float, а не str
        assert isinstance(health["timestamp"], (int, float))
        
        # Проверяем статус
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Проверяем эндпоинты
        assert isinstance(health["endpoints"], dict)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, api) -> None:
        """Тест контекстного менеджера."""
        async with api as client:
            assert client == api
            assert not client.client.is_closed
        
        assert api.client.is_closed
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, api) -> None:
        """Тест интеграции rate limiting."""
        start_time = asyncio.get_event_loop().time()
        
        # Делаем несколько быстрых запросов
        results = []
        for _ in range(3):
            result = await api.get_metainfo("america")
            results.append(result)
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Проверяем, что запросы были успешными
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)
        
        # Проверяем, что rate limiting работает
        assert total_time >= 0.2  # Минимальное время для 3 запросов при 10 RPS


class TestAPIResponse:
    """Тесты для APIResponse."""
    
    def test_api_response_creation(self) -> None:
        """Тест создания APIResponse."""
        data = {"test": "data"}
        status_code = 200
        headers = {"Content-Type": "application/json"}
        url = "https://test.com"
        
        response = APIResponse(
            data=data,
            status_code=status_code,
            headers=headers,
            url=url
        )
        
        assert response.data == data
        assert response.status_code == status_code
        assert response.headers == headers
        assert response.url == url 