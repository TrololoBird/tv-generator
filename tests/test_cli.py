"""
Тесты для CLI модуля.
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tv_generator.config import settings
from src.tv_generator.simple_cli import fetch_data, generate, health, info, test_specs, validate


@pytest.fixture(autouse=True)
def patch_rich_progress():
    """Мокаем Rich ProgressBar для избежания конфликтов в тестах."""
    with patch("rich.progress.Progress") as mock_progress:
        mock_progress.return_value.__enter__.return_value = mock_progress.return_value
        mock_progress.return_value.__exit__.return_value = None
        yield mock_progress


@pytest.mark.usefixtures("patch_rich_progress")
class TestSimpleCLI:
    """Тесты для простого CLI интерфейса."""

    @pytest.fixture
    def test_data_dir(self) -> Path:
        """Создает временную директорию для тестовых данных."""
        test_dir = Path("tests/test_data")
        test_dir.mkdir(exist_ok=True)
        yield test_dir
        # Очистка после тестов
        for file in test_dir.glob("*"):
            if file.is_file():
                file.unlink()

    @pytest.fixture
    def capture_output(self):
        """Захватывает stdout для проверки вывода."""
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        try:
            yield new_stdout
        finally:
            sys.stdout = old_stdout

    def test_info(self, capsys) -> None:
        """Тест команды info."""
        info()
        captured = capsys.readouterr()
        output = captured.out

        # Проверяем основную информацию
        assert "TradingView OpenAPI Generator" in output
        assert "Python:" in output
        assert "API URL:" in output
        assert "Доступные рынки:" in output

    def test_validate(self, capsys) -> None:
        """Тест команды validate."""
        validate()
        captured = capsys.readouterr()
        output = captured.out

        # Проверяем основные секции валидации
        assert "Валидация конфигурации" in output
        assert "Проверка директорий:" in output
        assert "Проверка конфигурации:" in output

    @pytest.mark.asyncio
    async def test_health(self, capsys) -> None:
        """Тест команды health."""
        await health()
        captured = capsys.readouterr()
        output = captured.out

        # Проверяем основные секции
        assert "Статус здоровья системы:" in output
        assert "API:" in output
        assert "Pipeline:" in output

    @pytest.mark.asyncio
    async def test_fetch_data(self, test_data_dir) -> None:
        """Тест команды fetch_data."""
        # Временно меняем директорию для результатов
        original_dir = settings.results_dir
        settings.results_dir = str(test_data_dir)

        try:
            # Тестируем с одним рынком для скорости
            await fetch_data(verbose=True)

            # Проверяем созданные файлы
            assert (test_data_dir / "us_stocks_metainfo.json").exists()
            assert (test_data_dir / "us_stocks_tickers.json").exists()
            assert (test_data_dir / "us_stocks_fields.txt").exists()
            assert (test_data_dir / "us_stocks_working_fields.txt").exists()

        finally:
            # Восстанавливаем оригинальную директорию
            settings.results_dir = original_dir

    @pytest.mark.asyncio
    async def test_generate(self, test_data_dir) -> None:
        """Тест команды generate."""
        # Временно меняем директории
        original_results = settings.results_dir
        original_specs = settings.specs_dir
        settings.results_dir = str(test_data_dir)
        settings.specs_dir = str(test_data_dir / "specs")

        try:
            # Создаем тестовые данные
            (test_data_dir / "specs").mkdir(exist_ok=True)
            test_market = "us_stocks"

            # Добавляем отладочную информацию
            print(f"DEBUG: test_data_dir = {test_data_dir}")
            print(f"DEBUG: settings.results_dir = {settings.results_dir}")
            print(f"DEBUG: settings.specs_dir = {settings.specs_dir}")
            print(f"DEBUG: specs dir exists = {(test_data_dir / 'specs').exists()}")

            # Создаем минимальный набор файлов
            openapi_fields_path = test_data_dir / f"{test_market}_openapi_fields.json"
            metainfo_path = test_data_dir / f"{test_market}_metainfo.json"

            print(f"DEBUG: Creating {openapi_fields_path}")
            with open(openapi_fields_path, "w") as f:
                json.dump(
                    {
                        "close": {"type": "number", "description": "Close price"},
                        "volume": {"type": "number", "description": "Volume"},
                    },
                    f,
                )

            print(f"DEBUG: Creating {metainfo_path}")
            with open(metainfo_path, "w") as f:
                json.dump({"fields": [{"n": "close", "t": "number"}, {"n": "volume", "t": "number"}]}, f)

            print(f"DEBUG: Files created successfully")
            print(f"DEBUG: openapi_fields_path exists = {openapi_fields_path.exists()}")
            print(f"DEBUG: metainfo_path exists = {metainfo_path.exists()}")

            # Запускаем генерацию
            print(f"DEBUG: Starting generate()")
            await generate(verbose=True)
            print(f"DEBUG: generate() completed")

            # Проверяем созданные файлы
            expected_spec_path = test_data_dir / "specs" / f"{test_market}_openapi.json"

            print(f"DEBUG: Expected spec path = {expected_spec_path}")
            print(f"DEBUG: spec file exists = {expected_spec_path.exists()}")

            # Проверяем содержимое директории specs
            specs_dir = test_data_dir / "specs"
            if specs_dir.exists():
                print(f"DEBUG: Contents of {specs_dir}:")
                for file in specs_dir.iterdir():
                    print(f"DEBUG:   - {file.name}")

            assert expected_spec_path.exists(), f"Spec file not found at {expected_spec_path}"

        finally:
            # Восстанавливаем оригинальные директории
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.asyncio
    async def test_test_specs(self, test_data_dir) -> None:
        """Тест команды test_specs."""
        # Временно меняем директории
        original_results = settings.results_dir
        original_specs = settings.specs_dir
        settings.results_dir = str(test_data_dir)
        settings.specs_dir = str(test_data_dir / "specs")

        try:
            # Создаем тестовые данные
            (test_data_dir / "specs").mkdir(exist_ok=True)
            test_market = "us_stocks"

            # Создаем тестовую спецификацию
            spec = {
                "openapi": "3.1.0",
                "info": {"title": "Test Market API", "version": "1.0.0"},
                "paths": {
                    "/america/scan": {
                        "post": {
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "symbols": {
                                                    "type": "object",
                                                    "properties": {
                                                        "tickers": {"type": "array", "items": {"type": "string"}}
                                                    },
                                                },
                                                "columns": {"type": "array", "items": {"type": "string"}},
                                            },
                                        }
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "data": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "s": {"type": "string"},
                                                                "d": {"type": "array"},
                                                            },
                                                        },
                                                    }
                                                },
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
            }

            with open(test_data_dir / "specs" / f"{test_market}_openapi.json", "w") as f:
                json.dump(spec, f)

            # Создаем тестовые поля
            with open(test_data_dir / f"{test_market}_openapi_fields.json", "w") as f:
                json.dump(
                    {
                        "close": {"type": "number", "description": "Close price"},
                        "volume": {"type": "number", "description": "Volume"},
                    },
                    f,
                )

            # Создаем тестовые тикеры
            with open(test_data_dir / f"{test_market}_tickers.json", "w") as f:
                json.dump([{"s": "NYSE:A", "d": ["A", 115.56, 0.03462603878116885, 0.04000000000000625, 3043869]}], f)

            # Запускаем тестирование
            await test_specs(verbose=True)

            # Проверяем созданный отчет
            assert (test_data_dir / "test_report.json").exists()

        finally:
            # Восстанавливаем оригинальные директории
            settings.results_dir = original_results
            settings.specs_dir = original_specs
