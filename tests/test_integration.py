"""
Интеграционные тесты с реальными данными.
"""

import asyncio
import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Dict, List

import pytest
from loguru import logger
from openapi_spec_validator import validate_spec

from tv_generator.api import TradingViewAPI
from tv_generator.config import settings
from tv_generator.core import MarketData, OpenAPIGeneratorResult, OpenAPIPipeline, generate_all_specifications


class TestIntegration:
    """Интеграционные тесты с реальными API вызовами."""

    @pytest.fixture
    def temp_results_dir(self) -> Generator[Path, None, None]:
        """Фикстура для временной директории результатов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_full_pipeline_integration(self, temp_results_dir):
        """Тест полной интеграции пайплайна с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            settings.specs_dir = str(temp_results_dir / "specs")

            # Создаем директории
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            # Запускаем пайплайн
            pipeline = OpenAPIPipeline()
            await pipeline.run()

            # Проверяем, что OpenAPI спецификации созданы для существующих рынков
            specs_dir = Path(settings.specs_dir)
            existing_markets = [
                "america",
                "crypto",
                "forex",
                "commodity",
                "index",
                "coin",
                "bond",
                "bonds",
                "cfd",
                "futures",
            ]

            created_specs = []
            for market_name in existing_markets:
                spec_file = specs_dir / f"{market_name}_openapi.json"
                if spec_file.exists():
                    created_specs.append(market_name)
                    # Проверяем валидность спецификации
                    with open(spec_file) as f:
                        spec = json.load(f)
                    validate_spec(spec)

            # Проверяем, что создано минимум 10 спецификаций
            assert len(created_specs) >= 10, f"Создано только {len(created_specs)} спецификаций из ожидаемых 10+"

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_single_market_processing(self, temp_results_dir):
        """Тест обработки одного рынка с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Проверяем результат
            assert market_data.name == "america"
            assert len(market_data.tickers) > 0
            assert len(market_data.fields) > 0
            assert len(market_data.working_fields) > 0

            # Проверяем, что файлы сохранены
            results_dir = Path(settings.results_dir)
            metainfo_file = results_dir / "america_metainfo.json"
            scan_file = results_dir / "america_scan.json"

            assert metainfo_file.exists()
            assert scan_file.exists()

            # Проверяем содержимое файлов
            with open(metainfo_file) as f:
                metainfo = json.load(f)
            assert "fields" in metainfo
            assert isinstance(metainfo["fields"], list)

            with open(scan_file) as f:
                scan = json.load(f)
            assert isinstance(scan, list)
            if scan:
                assert "s" in scan[0]  # symbol
                assert "d" in scan[0]  # data

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_api_error_handling(self, temp_results_dir):
        """Тест обработки ошибок API с реальными запросами."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Тестируем несуществующий рынок
            try:
                await pipeline.fetch_market_data("nonexistent_market_12345", {"endpoint": "invalid"})
                assert False, "Ожидалась ошибка для несуществующего рынка"
            except Exception as e:
                # Ожидаем ошибку
                assert "not found" in str(e).lower() or "invalid" in str(e).lower()

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_health_check_integration(self, temp_results_dir):
        """Тест интеграции проверки здоровья с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()
            health_status = await pipeline.health_check()

            assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
            assert "pipeline" in health_status
            assert "timestamp" in health_status
            assert "endpoints" in health_status

            # Проверяем, что основные endpoints работают
            for endpoint in ["america", "crypto", "forex"]:
                if endpoint in health_status["endpoints"]:
                    assert health_status["endpoints"][endpoint] in ["healthy", "degraded", "unhealthy"]

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    def test_config_validation(self):
        """Тест валидации конфигурации."""
        # Проверяем, что все необходимые поля присутствуют
        assert hasattr(settings, "tradingview_base_url")
        assert hasattr(settings, "request_timeout")
        assert hasattr(settings, "max_retries")
        assert hasattr(settings, "requests_per_second")
        assert hasattr(settings, "markets")

        # Проверяем структуру рынков
        for market_name, config in settings.markets.items():
            assert "endpoint" in config
            assert "label_product" in config
            assert "description" in config

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_batch_processing(self, temp_results_dir):
        """Тест пакетной обработки полей с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Проверяем, что поля обработаны
            assert len(market_data.fields) > 0
            assert len(market_data.working_fields) > 0
            assert len(market_data.openapi_fields) > 0

            # Проверяем, что working_fields является подмножеством fields
            assert all(field in market_data.fields for field in market_data.working_fields)

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_multiple_markets_processing(self, temp_results_dir):
        """Тест обработки нескольких рынков с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            settings.specs_dir = str(temp_results_dir / "specs")

            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Обрабатываем несколько рынков
            markets_to_test = ["america", "crypto", "forex"]
            processed_markets = []

            for market_name in markets_to_test:
                try:
                    market_config = settings.markets[market_name]
                    market_data = await pipeline.fetch_market_data(market_name, market_config)

                    # Генерируем OpenAPI спецификацию
                    result = await pipeline.generate_openapi_spec(market_data)

                    processed_markets.append(market_name)

                    # Проверяем результат
                    assert result.spec is not None
                    assert result.market_name == market_name

                    # Валидируем спецификацию
                    validate_spec(result.spec)

                    # Делаем паузу между рынками
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Ошибка при обработке рынка {market_name}: {e}")

            # Проверяем, что обработано минимум 2 рынка
            assert len(processed_markets) >= 2, f"Обработано только {len(processed_markets)} рынков из ожидаемых 2+"

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.asyncio
    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_data_persistence(self, temp_results_dir):
        """Тест персистентности данных с реальным API."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Сохраняем данные
            await pipeline.save_market_data(market_data)

            # Проверяем, что файлы созданы
            results_dir = Path(settings.results_dir)
            metainfo_file = results_dir / f"{market_data.name}_metainfo.json"
            scan_file = results_dir / f"{market_data.name}_scan.json"

            assert metainfo_file.exists()
            assert scan_file.exists()

            # Загружаем данные обратно
            loaded_metainfo = await pipeline._load_metainfo(market_data.name)
            loaded_scan = await pipeline._load_scan(market_data.name)

            # Проверяем, что данные совпадают
            assert loaded_metainfo == market_data.metainfo
            assert loaded_scan == market_data.tickers

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    def test_config_loading(self):
        """Тест загрузки конфигурации."""
        assert settings.tradingview_base_url == "https://scanner.tradingview.com"
        assert settings.request_timeout == 30
        assert settings.max_retries == 3
        assert settings.requests_per_second == 10

    def test_markets_config(self):
        """Тест конфигурации рынков."""
        assert "america" in settings.markets
        assert "crypto" in settings.markets
        assert "forex" in settings.markets
        assert settings.markets["america"]["endpoint"] == "america"

    def test_specs_directory_structure(self):
        """Тест структуры директории спецификаций."""
        specs_dir = Path(settings.specs_dir)
        assert specs_dir.name == "specs"
        assert specs_dir.parent.name == "docs"

    def test_results_directory_structure(self):
        """Тест структуры директории результатов."""
        results_dir = Path(settings.results_dir)
        assert results_dir.name == "results"


class TestDataPersistence:
    """Тесты персистентности данных."""

    @pytest.fixture
    def temp_results_dir(self):
        """Фикстура для временной директории результатов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_market_data_serialization(self, temp_results_dir):
        """Тест сериализации данных рынка."""
        # Создаем тестовые данные
        market_data = MarketData(
            name="test_market",
            endpoint="test",
            label_product="test-product",
            description="Test Market",
            metainfo={
                "fields": [
                    {"n": "close", "t": "number", "description": "Close price"},
                    {"n": "volume", "t": "number", "description": "Volume"},
                ]
            },
            tickers=[{"s": "AAPL", "d": [150.0, 1000000]}, {"s": "GOOGL", "d": [2500.0, 500000]}],
            fields=["close", "volume"],
            working_fields=["close", "volume"],
            openapi_fields={
                "close": {"type": "number", "description": "Close price"},
                "volume": {"type": "number", "description": "Volume"},
            },
        )

        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir)
            Path(temp_results_dir).mkdir(parents=True, exist_ok=True)

            # Сохраняем данные
            pipeline = OpenAPIPipeline()
            asyncio.run(pipeline.save_market_data(market_data))

            # Проверяем, что файлы созданы
            metainfo_file = temp_results_dir / "test_market_metainfo.json"
            scan_file = temp_results_dir / "test_market_scan.json"

            assert metainfo_file.exists()
            assert scan_file.exists()

            # Проверяем содержимое файлов
            with open(metainfo_file) as f:
                metainfo = json.load(f)
            assert metainfo == market_data.metainfo

            with open(scan_file) as f:
                scan = json.load(f)
            assert scan == market_data.tickers

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    def test_data_file_contents(self, temp_results_dir):
        """Тест содержимого файлов данных."""
        # Создаем тестовые данные
        test_metainfo = {
            "fields": [
                {"n": "close", "t": "number", "description": "Close price", "example": 150.0},
                {"n": "volume", "t": "number", "description": "Volume", "example": 1000000},
                {"n": "name", "t": "text", "description": "Company name", "example": "Apple Inc."},
            ]
        }

        test_scan = [
            {"s": "AAPL", "d": [150.0, 1000000, "Apple Inc."]},
            {"s": "GOOGL", "d": [2500.0, 500000, "Alphabet Inc."]},
            {"s": "MSFT", "d": [300.0, 750000, "Microsoft Corporation"]},
        ]

        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_results_dir)
            Path(temp_results_dir).mkdir(parents=True, exist_ok=True)

            # Сохраняем тестовые данные
            metainfo_file = temp_results_dir / "test_metainfo.json"
            scan_file = temp_results_dir / "test_scan.json"

            with open(metainfo_file, "w") as f:
                json.dump(test_metainfo, f, indent=2)

            with open(scan_file, "w") as f:
                json.dump(test_scan, f, indent=2)

            # Проверяем, что файлы созданы и содержат правильные данные
            assert metainfo_file.exists()
            assert scan_file.exists()

            with open(metainfo_file) as f:
                loaded_metainfo = json.load(f)
            assert loaded_metainfo == test_metainfo

            with open(scan_file) as f:
                loaded_scan = json.load(f)
            assert loaded_scan == test_scan

            # Проверяем структуру данных
            assert "fields" in loaded_metainfo
            assert isinstance(loaded_metainfo["fields"], list)
            assert len(loaded_metainfo["fields"]) == 3

            assert isinstance(loaded_scan, list)
            assert len(loaded_scan) == 3

            for field in loaded_metainfo["fields"]:
                assert "n" in field  # name
                assert "t" in field  # type
                assert "description" in field
                assert "example" in field

            for ticker in loaded_scan:
                assert "s" in ticker  # symbol
                assert "d" in ticker  # data
                assert isinstance(ticker["s"], str)
                assert isinstance(ticker["d"], list)

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results


# Тесты валидации OpenAPI спецификаций
def load_spec(filename):
    """Загружает OpenAPI спецификацию из файла."""
    spec_path = Path("docs/specs") / filename
    with open(spec_path) as f:
        return json.load(f)


# Ожидаемые спецификации
EXPECTED_SPECS = [
    "america_openapi.json",
    "crypto_openapi.json",
    "forex_openapi.json",
    "commodity_openapi.json",
    "index_openapi.json",
    "coin_openapi.json",
    "bond_openapi.json",
    "bonds_openapi.json",
    "cfd_openapi.json",
    "futures_openapi.json",
]


@pytest.mark.parametrize("spec_file", EXPECTED_SPECS)
def test_openapi_spec_valid(spec_file):
    """Тест валидности OpenAPI спецификаций."""
    spec_path = Path("docs/specs") / spec_file
    if spec_path.exists():
        with open(spec_path) as f:
            spec = json.load(f)
        validate_spec(spec)
    else:
        pytest.skip(f"Файл {spec_file} не найден")


@pytest.mark.parametrize("spec_file", EXPECTED_SPECS)
def test_openapi_spec_has_examples(spec_file):
    """Тест наличия примеров в OpenAPI спецификациях."""
    spec_path = Path("docs/specs") / spec_file
    if spec_path.exists():
        with open(spec_path) as f:
            spec = json.load(f)

        # Проверяем, что спецификация содержит примеры
        has_examples = False

        if "paths" in spec:
            for path in spec["paths"].values():
                for method in path.values():
                    if "requestBody" in method:
                        content = method["requestBody"].get("content", {})
                        for media_type in content.values():
                            if "schema" in media_type:
                                schema = media_type["schema"]
                                if "properties" in schema:
                                    for prop in schema["properties"].values():
                                        if "example" in prop:
                                            has_examples = True
                                            break

        assert has_examples, f"Спецификация {spec_file} не содержит примеров"


def test_openapi_spec_valid_global_stocks():
    """Тест валидности спецификации для глобальных акций."""
    spec_path = Path("docs/specs/america_openapi.json")
    if spec_path.exists():
        with open(spec_path) as f:
            spec = json.load(f)

        # Проверяем структуру спецификации
        assert spec["openapi"].startswith("3.")
        assert "info" in spec
        assert "paths" in spec
        assert "/america/scan" in spec["paths"]

        # Проверяем, что спецификация валидна
        validate_spec(spec)

        # Проверяем наличие основных компонентов
        scan_path = spec["paths"]["/america/scan"]
        assert "post" in scan_path

        post_method = scan_path["post"]
        assert "requestBody" in post_method
        assert "responses" in post_method

        # Проверяем структуру request body
        request_body = post_method["requestBody"]
        assert "content" in request_body
        assert "application/json" in request_body["content"]

        # Проверяем структуру response
        responses = post_method["responses"]
        assert "200" in responses

        response_200 = responses["200"]
        assert "content" in response_200
        assert "application/json" in response_200["content"]
    else:
        pytest.skip("Спецификация america_openapi.json не найдена")
