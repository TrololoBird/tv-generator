"""
Общие фикстуры для тестов.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from tv_generator.config import Settings
from tv_generator.api import TradingViewAPI, APIResponse
from tv_generator.core import Pipeline, MarketData


@pytest.fixture
def temp_results_dir():
    """Временная директория для результатов тестов."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_specs_dir():
    """Временная директория для спецификаций тестов."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_settings():
    """Мока настроек для тестов."""
    return Settings(
        tradingview_base_url="https://test.example.com",
        request_timeout=5,
        max_retries=1,
        retry_delay=0.1,
        requests_per_second=100,  # Высокий rate limit для тестов
        results_dir="test_results",
        specs_dir="test_specs",
        log_level="DEBUG",
        test_tickers_per_market=1,
        batch_size=10
    )


@pytest.fixture
def mock_api_response():
    """Мока ответа API."""
    return {
        "data": [
            {
                "s": "AAPL",
                "d": [150.0, 1000000, "Apple Inc."]
            }
        ],
        "totalCount": 1
    }


@pytest.fixture
def mock_metainfo():
    """Мока metainfo."""
    return {
        "fields": [
            {
                "name": "close",
                "type": "number",
                "description": "Close price",
                "example": 150.0
            },
            {
                "name": "volume",
                "type": "number", 
                "description": "Volume",
                "example": 1000000
            },
            {
                "name": "name",
                "type": "string",
                "description": "Company name",
                "example": "Apple Inc."
            }
        ]
    }


@pytest.fixture
def mock_tickers():
    """Мока тикеров."""
    return {
        "data": [
            {"s": "AAPL", "d": [150.0, 1000000]},
            {"s": "GOOGL", "d": [2500.0, 500000]},
            {"s": "MSFT", "d": [300.0, 750000]}
        ],
        "totalCount": 3
    }


@pytest.fixture
def sample_market_data():
    """Образец данных рынка для тестов."""
    return MarketData(
        name="us_stocks",
        endpoint="america",
        label_product="screener-stock",
        description="US Stocks",
        metainfo={
            "fields": [
                {"name": "close", "type": "number"},
                {"name": "volume", "type": "number"},
                {"name": "name", "type": "string"}
            ]
        },
        tickers=[
            {"name": "AAPL", "close": 150.0},
            {"name": "GOOGL", "close": 2500.0}
        ],
        fields=["close", "volume", "name"],
        working_fields=["close", "name"],
        openapi_fields={
            "close": {"type": "number", "description": "Close price"},
            "name": {"type": "string", "description": "Company name"}
        }
    )


@pytest.fixture
def mock_tradingview_api():
    """Мока TradingView API."""
    api = AsyncMock(spec=TradingViewAPI)
    
    # Мокаем методы API
    api.get_metainfo.return_value = {
        "fields": [
            {"name": "close", "type": "number"},
            {"name": "volume", "type": "number"}
        ]
    }
    
    api.scan_tickers.return_value = [
        {"name": "AAPL", "close": 150.0},
        {"name": "GOOGL", "close": 2500.0}
    ]
    
    api.test_field.side_effect = [True, False]  # close работает, volume нет
    
    # Мокаем контекстный менеджер
    api.__aenter__ = AsyncMock(return_value=api)
    api.__aexit__ = AsyncMock(return_value=None)
    
    return api


@pytest.fixture
def mock_api_response_obj():
    """Мока объекта APIResponse."""
    return APIResponse(
        data={"test": "data"},
        status_code=200,
        headers={"content-type": "application/json"},
        url="https://test.example.com/api"
    )


@pytest.fixture
def mock_pipeline():
    """Мока пайплайна."""
    pipeline = MagicMock(spec=Pipeline)
    pipeline.results_dir = Path("test_results")
    pipeline.api = mock_tradingview_api()
    return pipeline


@pytest.fixture
def mock_httpx_client():
    """Мока httpx клиента."""
    with patch("httpx.AsyncClient") as mock_client:
        client = AsyncMock()
        mock_client.return_value = client
        yield client


@pytest.fixture
def mock_logger():
    """Мока логгера."""
    with patch("loguru.logger") as mock_logger:
        yield mock_logger


@pytest.fixture
def sample_markets_config():
    """Образец конфигурации рынков."""
    return {
        "us_stocks": {
            "endpoint": "america",
            "label_product": "screener-stock",
            "description": "US Stocks"
        },
        "crypto_coins": {
            "endpoint": "coin",
            "label_product": "screener-coin",
            "description": "Cryptocurrency Coins"
        }
    }


@pytest.fixture
def mock_health_status():
    """Мока статуса здоровья."""
    return {
        "status": "healthy",
        "timestamp": 1234567890.0,
        "endpoints": {
            "america": "healthy",
            "crypto": "healthy"
        },
        "pipeline": "healthy"
    }


@pytest.fixture
def spec_path():
    """Фикстура для пути к спецификациям."""
    return Path(__file__).parent.parent / "specs"


def pytest_configure(config) -> None:
    pass


def pytest_unconfigure(config) -> None:
    pass


def pytest_addoption(parser) -> None:
    pass


def pytest_generate_tests(metafunc) -> None:
    pass


def pytest_collection_modifyitems(session, config, items) -> None:
    pass


def pytest_runtest_setup(item) -> None:
    pass


def pytest_runtest_teardown(item, nextitem) -> None:
    pass


def pytest_runtest_makereport(item, call) -> None:
    pass


def pytest_sessionstart(session) -> None:
    pass


def pytest_sessionfinish(session, exitstatus) -> None:
    pass


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    pass 