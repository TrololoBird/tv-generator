"""
Общие фикстуры для тестов с реальными данными.
"""

import asyncio
import json
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
import sys

import pytest
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tv_generator.api import TradingViewAPI
from tv_generator.config import Settings
from tv_generator.core import OpenAPIPipeline


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
def real_settings():
    """Реальные настройки для тестов."""
    return Settings(
        tradingview_base_url="https://scanner.tradingview.com",
        request_timeout=30,
        max_retries=3,
        retry_delay=1.0,
        requests_per_second=10,  # Низкий rate limit для тестов
        results_dir="test_results",
        specs_dir="test_specs",
        log_level="INFO",
        test_tickers_per_market=5,
        batch_size=5,
    )


@pytest.fixture
def real_tradingview_api(real_settings):
    """Реальный экземпляр TradingView API."""
    return TradingViewAPI(settings=real_settings)


@pytest.fixture
def real_pipeline(real_settings, temp_results_dir, temp_specs_dir):
    """Реальный экземпляр пайплайна."""
    # Временно изменяем пути для тестов
    real_settings.results_dir = str(temp_results_dir)
    real_settings.specs_dir = str(temp_specs_dir)
    return OpenAPIPipeline(settings=real_settings)


@pytest.fixture
def sample_markets():
    """Реальные рынки для тестирования."""
    return {
        "us_stocks": {"endpoint": "america", "label_product": "screener-stock", "description": "US Stocks"},
        "crypto_coins": {"endpoint": "coin", "label_product": "screener-coin", "description": "Cryptocurrency Coins"},
        "forex": {"endpoint": "forex", "label_product": "screener-forex", "description": "Forex Pairs"},
        "commodities": {"endpoint": "commodity", "label_product": "screener-commodity", "description": "Commodities"},
        "indices": {"endpoint": "index", "label_product": "screener-index", "description": "Indices"},
    }


@pytest.fixture
def real_metainfo_files():
    """Пути к реальным файлам metainfo."""
    data_dir = Path(__file__).parent.parent / "data" / "metainfo"
    return [f for f in data_dir.glob("*.json") if f.is_file()]


@pytest.fixture
def real_scan_files():
    """Пути к реальным файлам scan."""
    data_dir = Path(__file__).parent.parent / "data" / "scan"
    return [f for f in data_dir.glob("*.json") if f.is_file()]


@pytest.fixture
def real_raw_responses():
    """Пути к реальным raw API responses."""
    raw_dir = Path(__file__).parent.parent / "raw_api_responses"
    return [f for f in raw_dir.glob("*_metainfo.json") if f.is_file()]


@pytest.fixture
def spec_path():
    """Фикстура для пути к спецификациям."""
    return Path(__file__).parent.parent / "specs"


@pytest.fixture
def openapi_validator():
    """Импорт валидатора OpenAPI."""
    try:
        from openapi_spec_validator import validate_spec

        return validate_spec
    except ImportError:
        pytest.skip("openapi-spec-validator not installed")


def pytest_configure(config) -> None:
    """Конфигурация pytest."""
    # Отключаем предупреждения о моках
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning:unittest.mock.*")
    config.addinivalue_line("filterwarnings", "ignore::UserWarning:pytest_mock.*")


def pytest_unconfigure(config) -> None:
    pass


def pytest_addoption(parser) -> None:
    """Добавляем опции командной строки."""
    parser.addoption("--real-api", action="store_true", default=False, help="Запускать тесты с реальными API вызовами")
    parser.addoption("--skip-slow", action="store_true", default=False, help="Пропускать медленные тесты")


def pytest_collection_modifyitems(config, items):
    """Модифицируем коллекцию тестов."""
    if not config.getoption("--real-api"):
        skip_real_api = pytest.mark.skip(reason="Требуется --real-api для запуска с реальными API")
        for item in items:
            if "real_api" in item.keywords:
                item.add_marker(skip_real_api)

    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="Медленные тесты пропущены")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
