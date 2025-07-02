"""
Тесты для core модуля.
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

from tv_generator.api import (
    APIResponse,
    NetworkError,
    RateLimitError,
    SecurityError,
    TradingViewAPI,
    ValidationError,
    load_cookies,
    validate_url,
)
from tv_generator.config import Config, Settings, settings
from tv_generator.core import MarketData, OpenAPIGeneratorResult, OpenAPIPipeline
from tv_generator.sync import sync_tv_screener_data
from tv_generator.validation import validate_all_specs, validate_spec_file


class TestOpenAPIPipeline:
    """Тесты для OpenAPIPipeline."""

    @pytest.fixture
    def pipeline(self) -> OpenAPIPipeline:
        """Фикстура для создания пайплайна."""
        return OpenAPIPipeline(setup_logging=False)

    @pytest.fixture
    def test_data_dir(self) -> Path:
        """Фикстура для директории с тестовыми данными."""
        data_dir = Path(__file__).parent / "test_data"
        data_dir.mkdir(exist_ok=True)
        return data_dir

    def test_pipeline_initialization(self, pipeline: OpenAPIPipeline) -> None:
        """Тест инициализации пайплайна."""
        assert pipeline.api_client is not None
        assert pipeline.results_dir == Path(settings.results_dir)
        assert pipeline.data_dir == Path("data")
        assert pipeline.specs_dir == Path("docs/specs")

    @pytest.mark.asyncio
    async def test_fetch_market_data_success(self, pipeline: OpenAPIPipeline) -> None:
        """Тест успешного получения данных рынка."""
        market_config = {"endpoint": "america", "label_product": "screener-stock", "description": "US Stocks"}
        market_data = await pipeline.fetch_market_data("us_stocks", market_config)

        # Проверяем базовые поля
        assert market_data.name == "us_stocks"
        assert market_data.endpoint == "america"
        assert market_data.label_product == "screener-stock"

        # Проверяем наличие полей
        assert len(market_data.fields) > 0
        assert len(market_data.working_fields) > 0
        assert all(isinstance(f, str) for f in market_data.fields)
        assert all(isinstance(f, str) for f in market_data.working_fields)

        # Проверяем наличие тикеров
        assert len(market_data.tickers) > 0
        assert all(isinstance(t, dict) for t in market_data.tickers)
        assert all("s" in t for t in market_data.tickers)

        # Проверяем OpenAPI поля
        assert market_data.openapi_fields
        assert all(isinstance(f, dict) for f in market_data.openapi_fields.values())
        assert all("type" in f for f in market_data.openapi_fields.values())

    @pytest.mark.asyncio
    async def test_fetch_market_data_validation(self, pipeline: OpenAPIPipeline) -> None:
        """Тест валидации данных рынка."""
        market_config = {"endpoint": "america", "label_product": "screener-stock", "description": "US Stocks"}
        market_data = await pipeline.fetch_market_data("us_stocks", market_config)

        # Проверяем типы полей
        for field_name, field_info in market_data.openapi_fields.items():
            assert isinstance(field_name, str)
            assert isinstance(field_info, dict)
            assert "type" in field_info
            assert field_info["type"] in ["string", "number", "integer", "boolean", "array"]

            if "enum" in field_info:
                assert isinstance(field_info["enum"], list)
            if "format" in field_info:
                assert isinstance(field_info["format"], str)
            if "description" in field_info:
                assert isinstance(field_info["description"], str)

    def test_save_market_data(self, pipeline: OpenAPIPipeline, test_data_dir: Path) -> None:
        """Тест сохранения данных рынка."""
        # Создаем тестовые данные
        market_data = MarketData(
            name="test_market",
            endpoint="test",
            label_product="test-product",
            description="Test Market",
            metainfo={"fields": [{"name": "field1", "type": "string"}]},
            tickers=[{"s": "TEST", "d": ["value"]}],
            fields=["field1"],
            working_fields=["field1"],
            openapi_fields={"field1": {"type": "string"}},
        )

        # Временно меняем директорию для результатов
        original_dir = pipeline.results_dir
        pipeline.results_dir = test_data_dir

        try:
            # Создаем директорию если её нет
            os.makedirs(str(test_data_dir), exist_ok=True)

            # Сохраняем данные
            pipeline.save_market_data(market_data)

            # Проверяем созданные файлы
            expected_files = [
                "test_market_fields.txt",
                "test_market_metainfo.json",
                "test_market_openapi_fields.json",
                "test_market_tickers.json",
                "test_market_working_fields.txt",
            ]

            for filename in expected_files:
                file_path = test_data_dir / filename
                assert file_path.exists(), f"File not found: {file_path}"

            # Проверяем содержимое файлов
            with open(test_data_dir / "test_market_openapi_fields.json") as f:
                openapi_fields = json.load(f)
                assert "field1" in openapi_fields
                assert openapi_fields["field1"]["type"] == "string"

        finally:
            # Восстанавливаем оригинальную директорию
            pipeline.results_dir = original_dir

    @pytest.mark.asyncio
    async def test_run_pipeline(self, pipeline: OpenAPIPipeline, test_data_dir: Path) -> None:
        """Тест запуска пайплайна."""
        # Запускаем пайплайн
        await pipeline.run()

        # Проверяем, что OpenAPI спецификации созданы для существующих рынков
        # Используем только те рынки, для которых есть metainfo файлы
        existing_markets = [
            "ireland",
            "bond",
            "bonds",
            "cfd",
            "coin",
            "crypto",
            "economics2",
            "forex",
            "futures",
            "options",
        ]

        specs_dir = Path("docs/specs")
        for market_name in existing_markets:
            # Проверяем, что OpenAPI спецификация создана
            spec_file = specs_dir / f"{market_name}_openapi.json"
            assert spec_file.exists(), f"OpenAPI spec not found: {spec_file}"

            # Проверяем валидность JSON файла
            with open(spec_file) as f:
                spec_data = json.load(f)
                assert isinstance(spec_data, dict)
                assert "openapi" in spec_data
                assert "info" in spec_data
                assert "paths" in spec_data

    def test_extract_fields_from_metainfo(self, pipeline: OpenAPIPipeline) -> None:
        """Тест извлечения полей из метаинформации."""
        metainfo = [
            {"n": "field1", "t": "string", "r": None},
            {"n": "field2", "t": "number", "r": None},
            {"n": "field3", "t": "integer", "r": [1, 2, 3]},
            {"n": "field4", "t": "boolean", "r": None},
        ]

        fields = pipeline._extract_fields_from_metainfo(metainfo)
        assert fields == ["field1", "field2", "field3", "field4"]

    def test_map_tradingview_type_to_openapi(self, pipeline: OpenAPIPipeline) -> None:
        """Тест маппинга типов TradingView в OpenAPI."""
        # Тестируем основные типы
        assert pipeline._map_tradingview_type_to_openapi("number") == "number"
        assert pipeline._map_tradingview_type_to_openapi("price") == "number"
        assert pipeline._map_tradingview_type_to_openapi("percent") == "number"
        assert pipeline._map_tradingview_type_to_openapi("integer") == "integer"
        assert pipeline._map_tradingview_type_to_openapi("string") == "string"
        assert pipeline._map_tradingview_type_to_openapi("text") == "string"
        assert pipeline._map_tradingview_type_to_openapi("boolean") == "boolean"
        assert pipeline._map_tradingview_type_to_openapi("bool") == "boolean"
        assert pipeline._map_tradingview_type_to_openapi("time") == "string"
        assert pipeline._map_tradingview_type_to_openapi("set") == "array"
        assert pipeline._map_tradingview_type_to_openapi("map") == "object"

        # Тестируем неизвестный тип
        assert pipeline._map_tradingview_type_to_openapi("unknown") == "string"

    def test_create_field_schema(self, pipeline: OpenAPIPipeline) -> None:
        """Тест создания схемы поля."""
        field = {"n": "test_field", "t": "number", "r": None}

        schema = pipeline._create_field_schema(field)
        assert schema["type"] == "number"
        assert "description" in schema
        assert "example" in schema
        assert schema["example"] == 123.45

    def test_create_field_schema_with_enum(self, pipeline: OpenAPIPipeline) -> None:
        """Тест создания схемы поля с enum значениями."""
        field = {
            "n": "test_field",
            "t": "string",
            "r": [{"id": "value1", "name": "Value 1"}, {"id": "value2", "name": "Value 2"}],
        }

        schema = pipeline._create_field_schema(field)
        assert schema["type"] == "string"
        assert "enum" in schema
        assert schema["enum"] == ["value1", "value2"]

    def test_generate_field_example(self, pipeline: OpenAPIPipeline) -> None:
        """Тест генерации примеров для полей."""
        # Тест для числового поля
        number_field = {"t": "number", "r": None}
        assert pipeline._generate_field_example(number_field) == 123.45

        # Тест для строкового поля
        string_field = {"t": "string", "r": None}
        assert pipeline._generate_field_example(string_field) == "example"

        # Тест для boolean поля
        bool_field = {"t": "boolean", "r": None}
        assert pipeline._generate_field_example(bool_field) is True

        # Тест для поля с enum
        enum_field = {"t": "string", "r": [{"id": "test_value", "name": "Test"}]}
        assert pipeline._generate_field_example(enum_field) == "test_value"

    @pytest.mark.asyncio
    async def test_health_check(self, pipeline: OpenAPIPipeline) -> None:
        """Тест проверки здоровья пайплайна."""
        health = await pipeline.health_check()

        assert health["status"] == "healthy"
        assert health["pipeline"] == "healthy"
        assert health["api_available"] is True
        assert "data_directories" in health
        assert "results" in health["data_directories"]
        assert "specs" in health["data_directories"]
        assert "data" in health["data_directories"]

    def test_load_markets(self, pipeline: OpenAPIPipeline) -> None:
        """Тест загрузки списка рынков."""
        markets = pipeline._load_markets()
        assert isinstance(markets, list)
        assert len(markets) > 0

        # Проверяем кэширование
        markets_cached = pipeline._load_markets()
        assert markets == markets_cached

    def test_load_display_names(self, pipeline: OpenAPIPipeline) -> None:
        """Тест загрузки отображаемых имен полей."""
        display_names = pipeline._load_display_names()
        assert isinstance(display_names, dict)
        assert len(display_names) > 0

        # Проверяем кэширование
        display_names_cached = pipeline._load_display_names()
        assert display_names == display_names_cached

    def test_generate_openapi_spec(self, pipeline: OpenAPIPipeline) -> None:
        """Тест генерации OpenAPI спецификации."""
        # Используем существующий рынок для теста
        spec = pipeline.generate_openapi_spec("stocks")

        assert spec["openapi"] == "3.1.0"
        assert "info" in spec
        assert "paths" in spec
        assert "components" in spec
        assert spec["info"]["title"] == "TradingView stocks API"
        assert "stocks" in spec["paths"]

    def test_generate_all_specs(self, pipeline: OpenAPIPipeline) -> None:
        """Тест генерации всех спецификаций."""
        result = pipeline.generate_all_specs()
        assert hasattr(result, "markets_processed")
        assert hasattr(result, "verification_summary")


class TestMarketData:
    """Тесты для MarketData."""

    def test_market_data_creation(self) -> None:
        """Тест создания объекта MarketData."""
        market_data = MarketData(
            name="test",
            endpoint="test_endpoint",
            label_product="test_product",
            description="Test description",
            metainfo={"fields": []},
            tickers=[],
            fields=[],
            working_fields=[],
            openapi_fields={},
        )

        assert market_data.name == "test"
        assert market_data.endpoint == "test_endpoint"
        assert market_data.label_product == "test_product"
        assert market_data.description == "Test description"


# Обратная совместимость - тесты для старых имен классов
class TestPipeline(TestOpenAPIPipeline):
    """Тесты для пайплайна (обратная совместимость)."""

    @pytest.fixture
    def pipeline(self) -> OpenAPIPipeline:
        """Фикстура для создания пайплайна (обратная совместимость)."""
        return OpenAPIPipeline()


def test_import_sync():
    """Тест импорта sync."""
    from tv_generator.sync import sync_tv_screener_data

    assert callable(sync_tv_screener_data)


def test_import_validation():
    """Тест импорта validation."""
    from tv_generator.validation import validate_all_specs, validate_spec_file

    assert callable(validate_all_specs)
    assert callable(validate_spec_file)


def test_sync_success(tmp_path):
    # Создаем структуру исходных данных
    source_dir = tmp_path / "tv-screener"
    source_data_dir = source_dir / "data"
    source_metainfo_dir = source_data_dir / "metainfo"

    source_data_dir.mkdir(parents=True)
    source_metainfo_dir.mkdir()

    # Создаем тестовые файлы
    (source_data_dir / "markets.json").write_text('{"countries": ["test"]}')
    (source_data_dir / "column_display_names.json").write_text('{"fields": {"test": "Test"}}')
    (source_metainfo_dir / "test.json").write_text('[{"n": "field1", "t": "string"}]')

    # Запускаем синхронизацию
    sync_tv_screener_data(source_dir)

    # Проверяем результат
    assert (Path("data") / "markets.json").exists()
    assert (Path("data") / "column_display_names.json").exists()
    assert (Path("data") / "metainfo" / "test.json").exists()


def test_sync_force_overwrite(tmp_path):
    # Создаем структуру исходных данных
    source_dir = tmp_path / "tv-screener"
    source_data_dir = source_dir / "data"
    source_metainfo_dir = source_data_dir / "metainfo"

    source_data_dir.mkdir(parents=True)
    source_metainfo_dir.mkdir()

    # Создаем тестовые файлы
    (source_data_dir / "markets.json").write_text('{"countries": ["test"]}')
    (source_data_dir / "column_display_names.json").write_text('{"fields": {"test": "Test"}}')
    (source_metainfo_dir / "test.json").write_text('[{"n": "field1", "t": "string"}]')

    # Создаем существующие файлы
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    (data_dir / "markets.json").write_text('{"countries": ["old"]}')

    # Запускаем синхронизацию с force
    sync_tv_screener_data(source_dir, force=True)

    # Проверяем, что файлы обновлены
    with open(data_dir / "markets.json") as f:
        content = f.read()
        assert "test" in content


def test_sync_skip_existing(tmp_path):
    # Создаем структуру исходных данных
    source_dir = tmp_path / "tv-screener"
    source_data_dir = source_dir / "data"
    source_metainfo_dir = source_data_dir / "metainfo"

    source_data_dir.mkdir(parents=True)
    source_metainfo_dir.mkdir()

    # Создаем тестовые файлы
    (source_data_dir / "markets.json").write_text('{"countries": ["test"]}')
    (source_data_dir / "column_display_names.json").write_text('{"fields": {"test": "Test"}}')
    (source_metainfo_dir / "test.json").write_text('[{"n": "field1", "t": "string"}]')

    # Создаем существующие файлы
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    (data_dir / "markets.json").write_text('{"countries": ["old"]}')

    # Запускаем синхронизацию без force
    sync_tv_screener_data(source_dir, force=False)

    # Проверяем, что файлы не обновлены
    with open(data_dir / "markets.json") as f:
        content = f.read()
        assert "old" in content


def test_sync_missing_source(tmp_path):
    # Тестируем отсутствие исходной директории
    with pytest.raises(FileNotFoundError):
        sync_tv_screener_data(tmp_path / "nonexistent")


def test_sync_missing_files(tmp_path):
    # Создаем пустую структуру
    source_dir = tmp_path / "tv-screener"
    source_dir.mkdir()

    # Синхронизация должна пройти без ошибок
    sync_tv_screener_data(source_dir)


def test_validate_spec_file_valid(tmp_path):
    # Корректная OpenAPI спецификация (минимальная)
    spec_file = tmp_path / "valid_spec.json"
    spec_content = {"openapi": "3.1.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
    spec_file.write_text(json.dumps(spec_content))

    is_valid, errors = validate_spec_file(spec_file)
    assert is_valid
    assert len(errors) == 0


def test_validate_spec_file_invalid_json(tmp_path):
    # Некорректный JSON
    spec_file = tmp_path / "invalid_spec.json"
    spec_file.write_text('{"invalid": json}')

    is_valid, errors = validate_spec_file(spec_file)
    assert not is_valid
    assert len(errors) > 0


def test_validate_spec_file_invalid_openapi(tmp_path):
    # Некорректная спецификация (нет info)
    spec_file = tmp_path / "invalid_openapi.json"
    spec_content = {"openapi": "3.1.0", "paths": {}}
    spec_file.write_text(json.dumps(spec_content))

    is_valid, errors = validate_spec_file(spec_file)
    assert not is_valid
    assert len(errors) > 0


def test_validate_all_specs(tmp_path):
    # Создаем тестовые спецификации
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()

    # Валидная спецификация
    valid_spec = specs_dir / "valid_openapi.json"
    valid_content = {"openapi": "3.1.0", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
    valid_spec.write_text(json.dumps(valid_content))

    # Некорректная спецификация
    invalid_spec = specs_dir / "invalid_openapi.json"
    invalid_content = {"openapi": "3.1.0", "paths": {}}
    invalid_spec.write_text(json.dumps(invalid_content))

    # Тестируем валидацию
    result = validate_all_specs(specs_dir)
    assert not result  # Должна быть ошибка в invalid_spec


def test_validate_all_specs_no_dir(tmp_path):
    # Тестируем отсутствие директории
    result = validate_all_specs(tmp_path / "nonexistent")
    assert not result


def test_validate_all_specs_no_files(tmp_path):
    # Тестируем пустую директорию
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = validate_all_specs(empty_dir)
    assert result  # Должна пройти успешно


def test_config_default(tmp_path):
    """Тест конфигурации по умолчанию."""
    config = Config(tmp_path / "config.json")
    assert config.get("generator.version") == "2.0.0"
    assert config.get("data.source") == "tv-screener"


def test_config_set_and_get(tmp_path):
    """Тест установки и получения значений конфигурации."""
    config = Config(tmp_path / "config.json")
    config.set("test.key", "test_value")
    assert config.get("test.key") == "test_value"


def test_config_save_and_load(tmp_path):
    """Тест сохранения и загрузки конфигурации."""
    config = Config(tmp_path / "config.json")
    config.set("test.key", "test_value")
    config.save()

    # Создаем новый объект конфигурации
    new_config = Config(tmp_path / "config.json")
    assert new_config.get("test.key") == "test_value"


def test_settings_structure():
    """Тест структуры настроек."""
    assert hasattr(settings, "version")
    assert hasattr(settings, "tradingview_base_url")
    assert hasattr(settings, "request_timeout")
    assert hasattr(settings, "markets")


def test_validate_url():
    """Тест валидации URL."""
    from tv_generator.api import validate_url

    # Валидные URL
    assert validate_url("https://scanner.tradingview.com")
    assert validate_url("https://scanner.tradingview.com/api")

    # Невалидные URL
    assert not validate_url("http://malicious.com")
    assert not validate_url("https://scanner.tradingview.com.evil.com")
    assert not validate_url("ftp://scanner.tradingview.com")


def test_load_cookies_nonexistent(tmp_path):
    """Тест загрузки cookies из несуществующего файла."""
    from tv_generator.api import load_cookies

    cookies = load_cookies(str(tmp_path / "nonexistent"))
    assert cookies is None


def test_load_cookies_too_large(tmp_path):
    """Тест загрузки слишком большого файла cookies."""
    from tv_generator.api import SecurityError, load_cookies

    # Создаем большой файл
    large_file = tmp_path / "large_cookies.txt"
    large_file.write_text("x" * (1024 * 1024 + 1))  # Больше 1MB

    with pytest.raises(SecurityError):
        load_cookies(str(large_file))


def test_tradingviewapi_invalid_url(monkeypatch):
    """Тест инициализации API с невалидным URL."""
    from tv_generator.api import SecurityError, TradingViewAPI

    # Мокаем settings
    monkeypatch.setattr("tv_generator.config.settings.tradingview_base_url", "http://invalid.com")

    with pytest.raises(SecurityError):
        TradingViewAPI()


def test_tradingviewapierror_inheritance():
    """Тест иерархии исключений."""
    from tv_generator.api import NetworkError, RateLimitError, SecurityError, TradingViewAPIError, ValidationError

    assert issubclass(SecurityError, TradingViewAPIError)
    assert issubclass(NetworkError, TradingViewAPIError)
    assert issubclass(RateLimitError, TradingViewAPIError)
    assert issubclass(ValidationError, TradingViewAPIError)


def test_load_metainfo_empty(tmp_path):
    import asyncio

    from src.tv_generator.core.file_manager import AsyncFileManager

    # Создаём пустой файл
    metainfo_path = tmp_path / "metainfo.json"
    metainfo_path.write_text("")
    fm = AsyncFileManager(data_dir=tmp_path, specs_dir=tmp_path)
    result = asyncio.run(fm.load_metainfo("metainfo"))
    assert result == {}, "Пустой файл должен возвращать пустой dict"


def test_load_metainfo_invalid_json(tmp_path):
    import asyncio

    from src.tv_generator.core.file_manager import AsyncFileManager

    # Создаём битый JSON
    metainfo_path = tmp_path / "metainfo.json"
    metainfo_path.write_text("{invalid json}")
    fm = AsyncFileManager(data_dir=tmp_path, specs_dir=tmp_path)
    result = asyncio.run(fm.load_metainfo("metainfo"))
    assert result == {}, "Битый JSON должен возвращать пустой dict"


def test_load_scan_empty(tmp_path):
    import asyncio

    from src.tv_generator.core.file_manager import AsyncFileManager

    scan_path = tmp_path / "scan.json"
    scan_path.write_text("")
    fm = AsyncFileManager(data_dir=tmp_path, specs_dir=tmp_path)
    result = asyncio.run(fm.load_scan_data("scan"))
    assert result == [], "Пустой файл scan должен возвращать пустой список"


def test_load_scan_invalid_json(tmp_path):
    import asyncio

    from src.tv_generator.core.file_manager import AsyncFileManager

    scan_path = tmp_path / "scan.json"
    scan_path.write_text("{invalid json}")
    fm = AsyncFileManager(data_dir=tmp_path, specs_dir=tmp_path)
    result = asyncio.run(fm.load_scan_data("scan"))
    assert result == [], "Битый JSON scan должен возвращать пустой список"
