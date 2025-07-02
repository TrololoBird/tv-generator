"""
Регрессионные тесты с реальными данными.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest
from loguru import logger

from tv_generator.config import settings
from tv_generator.core import OpenAPIPipeline


class TestRegression:
    """Регрессионные тесты для проверки изменений в данных и спецификациях."""

    @pytest.fixture
    def temp_test_dir(self):
        """Фикстура для временной директории тестов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_metainfo_changes_reflect_in_spec(self, temp_test_dir):
        """Тест: изменения в метаинформации отражаются в спецификации."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Получаем данные рынка
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Сохраняем исходную метаинформацию
            original_metainfo = market_data.metainfo.copy()
            original_fields_count = len(market_data.fields)

            # Генерируем первую спецификацию
            result1 = await pipeline.generate_openapi_spec(market_data)
            spec1 = result1.spec

            # Проверяем, что количество полей в спецификации соответствует метаинформации
            if "paths" in spec1 and "/america/scan" in spec1["paths"]:
                scan_path = spec1["paths"]["/america/scan"]
                if "post" in scan_path:
                    post_method = scan_path["post"]
                    if "requestBody" in post_method:
                        content = post_method["requestBody"].get("content", {})
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "properties" in schema:
                                properties_count = len(schema["properties"])
                                # Проверяем, что количество свойств соответствует полям
                                assert properties_count >= original_fields_count

            # Симулируем изменение метаинформации (добавляем новое поле)
            new_field = {"n": "test_field", "t": "number", "description": "Test field"}
            market_data.metainfo["fields"].append(new_field)
            market_data.fields.append("test_field")
            market_data.working_fields.append("test_field")
            market_data.openapi_fields["test_field"] = {"type": "number", "description": "Test field"}

            # Генерируем вторую спецификацию
            result2 = await pipeline.generate_openapi_spec(market_data)
            spec2 = result2.spec

            # Проверяем, что новая спецификация отличается от старой
            assert spec1 != spec2

            # Проверяем, что новое поле появилось в спецификации
            if "paths" in spec2 and "/america/scan" in spec2["paths"]:
                scan_path = spec2["paths"]["/america/scan"]
                if "post" in scan_path:
                    post_method = scan_path["post"]
                    if "requestBody" in post_method:
                        content = post_method["requestBody"].get("content", {})
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "properties" in schema:
                                properties = schema["properties"]
                                assert "test_field" in properties
                                assert properties["test_field"]["type"] == "number"

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_ticker_changes_affect_field_selection(self, temp_test_dir):
        """Тест: изменения в тикерах влияют на выборку рабочих полей."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Получаем данные рынка
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Сохраняем исходные данные
            original_tickers = market_data.tickers.copy()
            original_working_fields = market_data.working_fields.copy()

            # Проверяем, что есть рабочие поля
            assert len(original_working_fields) > 0

            # Симулируем изменение тикеров (используем только первый тикер)
            market_data.tickers = [original_tickers[0]] if original_tickers else []

            # Пересчитываем рабочие поля
            market_data.working_fields = []
            market_data.openapi_fields = {}

            # Тестируем поля с новым набором тикеров
            for field in market_data.fields:
                try:
                    # Используем реальный API для тестирования поля
                    is_working = await pipeline.api.test_field(
                        market_data.endpoint, market_data.tickers[0]["s"] if market_data.tickers else "AAPL", field
                    )
                    if is_working:
                        market_data.working_fields.append(field)
                        # Получаем данные поля для OpenAPI схемы
                        field_data = await pipeline.api.get_field_data(
                            market_data.endpoint,
                            market_data.tickers[0]["s"] if market_data.tickers else "AAPL",
                            [field],
                        )
                        if field_data and "d" in field_data and field_data["d"]:
                            # Определяем тип поля на основе данных
                            field_type = type(field_data["d"][0]).__name__
                            if field_type == "int" or field_type == "float":
                                openapi_type = "number"
                            elif field_type == "str":
                                openapi_type = "string"
                            elif field_type == "bool":
                                openapi_type = "boolean"
                            else:
                                openapi_type = "string"

                            market_data.openapi_fields[field] = {"type": openapi_type, "description": f"Field {field}"}
                except Exception as e:
                    logger.warning(f"Ошибка при тестировании поля {field}: {e}")

            # Проверяем, что набор рабочих полей изменился
            # (может быть меньше, так как используем меньше тикеров)
            assert len(market_data.working_fields) <= len(original_working_fields)

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_missing_field_removed_from_schema(self, temp_test_dir):
        """Тест: отсутствующее поле удаляется из схемы."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Получаем данные рынка
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Генерируем первую спецификацию
            result1 = await pipeline.generate_openapi_spec(market_data)
            spec1 = result1.spec

            # Сохраняем исходные рабочие поля
            original_working_fields = market_data.working_fields.copy()
            original_openapi_fields = market_data.openapi_fields.copy()

            # Симулируем удаление поля из рабочих полей
            if len(market_data.working_fields) > 1:
                removed_field = market_data.working_fields.pop()
                if removed_field in market_data.openapi_fields:
                    del market_data.openapi_fields[removed_field]

                # Генерируем вторую спецификацию
                result2 = await pipeline.generate_openapi_spec(market_data)
                spec2 = result2.spec

                # Проверяем, что спецификации отличаются
                assert spec1 != spec2

                # Проверяем, что удаленное поле отсутствует во второй спецификации
                if "paths" in spec2 and "/america/scan" in spec2["paths"]:
                    scan_path = spec2["paths"]["/america/scan"]
                    if "post" in scan_path:
                        post_method = scan_path["post"]
                        if "requestBody" in post_method:
                            content = post_method["requestBody"].get("content", {})
                            if "application/json" in content:
                                schema = content["application/json"].get("schema", {})
                                if "properties" in schema:
                                    properties = schema["properties"]
                                    assert removed_field not in properties

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_field_type_changes_reflect_in_schema(self, temp_test_dir):
        """Тест: изменения типа поля отражаются в схеме."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Получаем данные рынка
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Генерируем первую спецификацию
            result1 = await pipeline.generate_openapi_spec(market_data)
            spec1 = result1.spec

            # Сохраняем исходные OpenAPI поля
            original_openapi_fields = market_data.openapi_fields.copy()

            # Симулируем изменение типа поля
            if market_data.openapi_fields:
                field_name = list(market_data.openapi_fields.keys())[0]
                original_type = market_data.openapi_fields[field_name]["type"]

                # Изменяем тип поля
                new_type = "string" if original_type == "number" else "number"
                market_data.openapi_fields[field_name]["type"] = new_type

                # Генерируем вторую спецификацию
                result2 = await pipeline.generate_openapi_spec(market_data)
                spec2 = result2.spec

                # Проверяем, что спецификации отличаются
                assert spec1 != spec2

                # Проверяем, что тип поля изменился в спецификации
                if "paths" in spec2 and "/america/scan" in spec2["paths"]:
                    scan_path = spec2["paths"]["/america/scan"]
                    if "post" in scan_path:
                        post_method = scan_path["post"]
                        if "requestBody" in post_method:
                            content = post_method["requestBody"].get("content", {})
                            if "application/json" in content:
                                schema = content["application/json"].get("schema", {})
                                if "properties" in schema and field_name in schema["properties"]:
                                    field_schema = schema["properties"][field_name]
                                    assert field_schema["type"] == new_type

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_multiple_markets_consistency(self, temp_test_dir):
        """Тест: консистентность между несколькими рынками."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Тестируем несколько рынков
            markets_to_test = ["america", "crypto", "forex"]
            market_specs = {}

            for market_name in markets_to_test:
                try:
                    market_config = settings.markets[market_name]
                    market_data = await pipeline.fetch_market_data(market_name, market_config)

                    # Генерируем спецификацию
                    result = await pipeline.generate_openapi_spec(market_data)
                    market_specs[market_name] = result.spec

                    # Делаем паузу между рынками
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Ошибка при обработке рынка {market_name}: {e}")

            # Проверяем консистентность спецификаций
            for market_name, spec in market_specs.items():
                # Проверяем базовую структуру
                assert spec["openapi"].startswith("3.")
                assert "info" in spec
                assert "paths" in spec

                # Проверяем, что есть соответствующий путь
                expected_path = f"/{market_name}/scan"
                assert expected_path in spec["paths"]

                # Проверяем структуру метода POST
                scan_path = spec["paths"][expected_path]
                assert "post" in scan_path

                post_method = scan_path["post"]
                assert "requestBody" in post_method
                assert "responses" in post_method

                # Проверяем, что есть ответ 200
                assert "200" in post_method["responses"]

                # Проверяем, что спецификация валидна
                from openapi_spec_validator import validate_spec

                validate_spec(spec)

            # Проверяем, что спецификации разных рынков отличаются
            spec_names = list(market_specs.keys())
            for i in range(len(spec_names)):
                for j in range(i + 1, len(spec_names)):
                    market1, market2 = spec_names[i], spec_names[j]
                    spec1, spec2 = market_specs[market1], market_specs[market2]

                    # Спецификации должны отличаться (разные рынки)
                    assert spec1 != spec2

                    # Но должны иметь одинаковую базовую структуру
                    assert spec1["openapi"] == spec2["openapi"]
                    assert "info" in spec1 and "info" in spec2
                    assert "paths" in spec1 and "paths" in spec2

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    async def test_data_persistence_consistency(self, temp_test_dir):
        """Тест: консистентность сохранения и загрузки данных."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            pipeline = OpenAPIPipeline()

            # Получаем данные рынка
            market_config = settings.markets["america"]
            market_data = await pipeline.fetch_market_data("america", market_config)

            # Сохраняем данные
            await pipeline.save_market_data(market_data)

            # Загружаем данные обратно
            loaded_metainfo = await pipeline._load_metainfo(market_data.name)
            loaded_scan = await pipeline._load_scan(market_data.name)

            # Проверяем консистентность
            assert loaded_metainfo == market_data.metainfo
            assert loaded_scan == market_data.tickers

            # Создаем новый объект MarketData из загруженных данных
            restored_market_data = await pipeline._create_market_data_from_files(market_data.name, market_config)

            # Проверяем, что восстановленные данные совпадают с оригинальными
            assert restored_market_data.name == market_data.name
            assert restored_market_data.endpoint == market_data.endpoint
            assert restored_market_data.label_product == market_data.label_product
            assert restored_market_data.description == market_data.description
            assert restored_market_data.metainfo == market_data.metainfo
            assert restored_market_data.tickers == market_data.tickers

            # Проверяем, что поля обработаны одинаково
            assert set(restored_market_data.fields) == set(market_data.fields)
            assert set(restored_market_data.working_fields) == set(market_data.working_fields)

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
