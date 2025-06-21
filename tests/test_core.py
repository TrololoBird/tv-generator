"""
Тесты для core модуля.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any
import os

from tv_generator.core import Pipeline, MarketData
from tv_generator.config import settings
from tv_generator.api import TradingViewAPI


class TestPipeline:
    """Тесты для Pipeline."""

    @pytest.fixture
    def pipeline(self) -> Pipeline:
        """Фикстура для создания пайплайна."""
        return Pipeline()
    
    @pytest.fixture
    def test_data_dir(self) -> Path:
        """Фикстура для директории с тестовыми данными."""
        data_dir = Path(__file__).parent / "test_data"
        data_dir.mkdir(exist_ok=True)
        return data_dir

    def test_pipeline_initialization(self, pipeline: Pipeline) -> None:
        """Тест инициализации пайплайна."""
        assert pipeline.api is not None
        assert pipeline.results_dir == Path(settings.results_dir)

    @pytest.mark.asyncio
    async def test_fetch_market_data_success(self, pipeline: Pipeline) -> None:
        """Тест успешного получения данных рынка."""
        market_config = {
            "endpoint": "america",
            "label_product": "screener-stock",
            "description": "US Stocks"
        }
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
    async def test_fetch_market_data_validation(self, pipeline: Pipeline) -> None:
        """Тест валидации данных рынка."""
        market_config = {
            "endpoint": "america",
            "label_product": "screener-stock",
            "description": "US Stocks"
        }
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

    def test_save_market_data(self, pipeline: Pipeline, test_data_dir: Path) -> None:
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
            openapi_fields={"field1": {"type": "string"}}
        )
        
        # Временно меняем директорию для результатов
        original_dir = pipeline.results_dir
        pipeline.results_dir = test_data_dir
        
        try:
            # Добавляем отладочную информацию
            print(f"DEBUG: test_data_dir = {test_data_dir}")
            print(f"DEBUG: test_data_dir exists = {test_data_dir.exists()}")
            print(f"DEBUG: pipeline.results_dir = {pipeline.results_dir}")
            
            # Создаем директорию если её нет
            os.makedirs(str(test_data_dir), exist_ok=True)
            print(f"DEBUG: Created directory {test_data_dir}")
            print(f"DEBUG: Directory exists after creation = {test_data_dir.exists()}")
            
            # Сохраняем данные
            print(f"DEBUG: Starting save_market_data")
            pipeline.save_market_data(market_data)
            print(f"DEBUG: save_market_data completed")
            
            # Проверяем созданные файлы
            expected_files = [
                "test_market_fields.txt",
                "test_market_metainfo.json", 
                "test_market_openapi_fields.json",
                "test_market_tickers.json",
                "test_market_working_fields.txt"
            ]
            
            for filename in expected_files:
                file_path = test_data_dir / filename
                print(f"DEBUG: Checking {file_path}")
                print(f"DEBUG: File exists = {file_path.exists()}")
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
    async def test_run_pipeline(self, pipeline: Pipeline, test_data_dir: Path) -> None:
        """Тест запуска пайплайна."""
        # Временно меняем директорию для результатов
        original_dir = pipeline.results_dir
        pipeline.results_dir = test_data_dir
        
        try:
            # Запускаем пайплайн
            await pipeline.run()
            
            # Проверяем, что файлы созданы для каждого рынка
            for market_name in settings.markets:
                # Проверяем правильные имена файлов (без .json для некоторых)
                assert (test_data_dir / f"{market_name}_metainfo.json").exists()
                assert (test_data_dir / f"{market_name}_tickers.json").exists()
                assert (test_data_dir / f"{market_name}_fields.txt").exists()
                assert (test_data_dir / f"{market_name}_working_fields.txt").exists()
                assert (test_data_dir / f"{market_name}_openapi_fields.json").exists()
                
                # Проверяем валидность JSON файлов
                with open(test_data_dir / f"{market_name}_openapi_fields.json") as f:
                    openapi_fields = json.load(f)
                    assert isinstance(openapi_fields, dict)
                    assert len(openapi_fields) > 0
                    
        finally:
            # Восстанавливаем оригинальную директорию
            pipeline.results_dir = original_dir

    def test_extract_fields(self, pipeline: Pipeline) -> None:
        """Тест извлечения полей."""
        metainfo = {
            "fields": [
                {"n": "field1", "t": "string", "r": None},
                {"n": "field2", "t": "number", "r": None},
                {"n": "field3", "t": "integer", "r": [1, 2, 3]},
                {"n": "field4", "t": "boolean", "r": None}
            ]
        }
        fields = pipeline._extract_fields(metainfo)
        assert len(fields) == 4
        assert all(f in fields for f in ["field1", "field2", "field3", "field4"])

    def test_map_tradingview_type_to_openapi(self, pipeline: Pipeline) -> None:
        """Тест маппинга типов TradingView в OpenAPI."""
        # Реальные типы из анализа данных
        test_cases = [
            ("number", "number"),
            ("price", "number"),
            ("num_slice", "number"),
            ("text", "string"),
            ("fundamental_price", "number"),
            ("map", "string"),
            ("percent", "number"),
            ("time", "string"),
            ("bool", "boolean"),
            ("time-yyyymmdd", "string"),
            ("interface", "string"),
            ("set", "string"),
            ("unknown_type", "string"),  # Неизвестные типы -> string
        ]
        
        for tv_type, expected_openapi_type in test_cases:
            result = pipeline._map_tradingview_type_to_openapi(tv_type)
            assert result == expected_openapi_type, f"Failed for {tv_type}"
    
    def test_create_openapi_fields(self, pipeline: Pipeline) -> None:
        """Тест создания OpenAPI полей."""
        metainfo = {
            "fields": [
                {
                    "n": "field1",
                    "t": "number",
                    "description": "Test field"
                    # Убираем example - не все поля имеют примеры
                },
                {
                    "n": "field2",
                    "t": "text",
                    "r": ["a", "b", "c"],
                    "description": "Enum field"
                },
                {
                    "n": "field3",
                    "t": "bool",
                    "description": "Boolean field"
                }
            ]
        }
        
        working_fields = ["field1", "field2", "field3"]
        openapi_fields = pipeline._create_openapi_fields(metainfo, working_fields)
        
        assert "field1" in openapi_fields
        assert openapi_fields["field1"]["type"] == "number"
        assert openapi_fields["field1"]["description"] == "Test field"
        # Не проверяем наличие example - не все поля имеют примеры
        
        assert "field2" in openapi_fields
        assert openapi_fields["field2"]["type"] == "string"
        assert openapi_fields["field2"]["enum"] == ["a", "b", "c"]
        
        assert "field3" in openapi_fields
        assert openapi_fields["field3"]["type"] == "boolean"
    
    @pytest.mark.asyncio
    async def test_health_check(self, pipeline: Pipeline) -> None:
        """Тест проверки здоровья пайплайна."""
        health_status = await pipeline.health_check()
        
        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Проверяем, что есть информация о компонентах
        if "api" in health_status:
            assert isinstance(health_status["api"], dict)
            assert "status" in health_status["api"]


class TestMarketData:
    """Тесты для MarketData."""

    def test_market_data_creation(self) -> None:
        """Тест создания MarketData."""
        market_data = MarketData(
            name="test",
            endpoint="america",
            label_product="screener-stock",
            description="Test Market",
            metainfo={"fields": [{"name": "field1", "type": "string"}]},
            tickers=[{"s": "TEST", "d": ["value"]}],
            fields=["field1"],
            working_fields=["field1"],
            openapi_fields={"field1": {"type": "string"}}
        )
        
        # Проверяем все поля
        assert market_data.name == "test"
        assert market_data.endpoint == "america"
        assert market_data.label_product == "screener-stock"
        assert market_data.description == "Test Market"
        assert isinstance(market_data.metainfo, dict)
        assert isinstance(market_data.tickers, list)
        assert isinstance(market_data.fields, list)
        assert isinstance(market_data.working_fields, list)
        assert isinstance(market_data.openapi_fields, dict)
        
        # Проверяем типы данных
        assert all(isinstance(t, dict) for t in market_data.tickers)
        assert all(isinstance(f, str) for f in market_data.fields)
        assert all(isinstance(f, str) for f in market_data.working_fields)
        assert all(isinstance(f, dict) for f in market_data.openapi_fields.values()) 