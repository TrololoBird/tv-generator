"""
Тесты для CLI модуля с реальными командами.
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from subprocess import run

import pytest
from loguru import logger

from scripts.tv_generator_cli import main
from tv_generator.config import settings


class TestCLI:
    """Тесты для CLI интерфейса с реальными командами."""

    @pytest.fixture
    def temp_test_dir(self):
        """Создает временную директорию для тестовых данных."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

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

    def test_config_loading(self) -> None:
        """Тест загрузки конфигурации."""
        assert settings.tradingview_base_url == "https://scanner.tradingview.com"
        assert settings.request_timeout == 30
        assert settings.max_retries == 3
        assert settings.requests_per_second == 10

    def test_markets_config(self) -> None:
        """Тест конфигурации рынков."""
        assert "america" in settings.markets
        assert "crypto" in settings.markets
        assert "forex" in settings.markets
        assert settings.markets["america"]["endpoint"] == "america"

    def test_specs_directory_structure(self) -> None:
        """Тест структуры директории спецификаций."""
        specs_dir = Path(settings.specs_dir)
        assert specs_dir.name == "specs"
        assert specs_dir.parent.name == "docs"

    def test_results_directory_structure(self) -> None:
        """Тест структуры директории результатов."""
        results_dir = Path(settings.results_dir)
        assert results_dir.name == "results"

    def test_cli_help(self, capture_output):
        """Тест вывода справки CLI."""
        try:
            main(["--help"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "usage:" in output.lower()
        assert "generate" in output
        assert "sync" in output
        assert "validate" in output

    def test_cli_generate_help(self, capture_output):
        """Тест вывода справки для команды generate."""
        try:
            main(["generate", "--help"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "generate" in output.lower()
        assert "markets" in output

    def test_cli_sync_help(self, capture_output):
        """Тест вывода справки для команды sync."""
        try:
            main(["sync", "--help"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "sync" in output.lower()
        assert "markets" in output

    def test_cli_validate_help(self, capture_output):
        """Тест вывода справки для команды validate."""
        try:
            main(["validate", "--help"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "validate" in output.lower()
        assert "data" in output

    @pytest.mark.real_api
    @pytest.mark.slow
    def test_cli_generate_single_market(self, temp_test_dir):
        """Тест генерации OpenAPI для одного рынка."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            # Создаем директории
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            # Запускаем генерацию для одного рынка
            main(["generate", "--markets", "america"])

            # Проверяем, что файлы созданы
            results_dir = Path(settings.results_dir)
            specs_dir = Path(settings.specs_dir)

            # Проверяем результаты
            assert results_dir.exists()
            market_files = list(results_dir.glob("america_*.json"))
            assert len(market_files) > 0

            # Проверяем спецификации
            assert specs_dir.exists()
            spec_files = list(specs_dir.glob("america_openapi.json"))
            assert len(spec_files) > 0

            # Проверяем содержимое спецификации
            spec_file = spec_files[0]
            with open(spec_file) as f:
                spec = json.load(f)

            assert spec["openapi"].startswith("3.")
            assert "info" in spec
            assert "paths" in spec
            assert "/america/scan" in spec["paths"]

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    def test_cli_generate_multiple_markets(self, temp_test_dir):
        """Тест генерации OpenAPI для нескольких рынков."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            # Создаем директории
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            # Запускаем генерацию для нескольких рынков
            main(["generate", "--markets", "america,crypto,forex"])

            # Проверяем, что файлы созданы
            results_dir = Path(settings.results_dir)
            specs_dir = Path(settings.specs_dir)

            # Проверяем результаты для каждого рынка
            for market in ["america", "crypto", "forex"]:
                market_files = list(results_dir.glob(f"{market}_*.json"))
                assert len(market_files) > 0

                spec_files = list(specs_dir.glob(f"{market}_openapi.json"))
                assert len(spec_files) > 0

                # Проверяем содержимое спецификации
                spec_file = spec_files[0]
                with open(spec_file) as f:
                    spec = json.load(f)

                assert spec["openapi"].startswith("3.")
                assert "info" in spec
                assert "paths" in spec
                assert f"/{market}/scan" in spec["paths"]

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    @pytest.mark.real_api
    @pytest.mark.slow
    def test_cli_sync_market(self, temp_test_dir):
        """Тест синхронизации данных рынка."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")

            # Создаем директорию
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)

            # Запускаем синхронизацию
            main(["sync", "--markets", "america"])

            # Проверяем, что файлы созданы
            results_dir = Path(settings.results_dir)

            # Проверяем metainfo
            metainfo_files = list(results_dir.glob("america_metainfo.json"))
            assert len(metainfo_files) > 0

            # Проверяем scan
            scan_files = list(results_dir.glob("america_scan.json"))
            assert len(scan_files) > 0

            # Проверяем содержимое metainfo
            metainfo_file = metainfo_files[0]
            with open(metainfo_file) as f:
                metainfo = json.load(f)

            assert "fields" in metainfo
            assert isinstance(metainfo["fields"], list)

            # Проверяем содержимое scan
            scan_file = scan_files[0]
            with open(scan_file) as f:
                scan = json.load(f)

            assert isinstance(scan, list)
            if scan:  # Если есть данные
                assert "s" in scan[0]  # symbol
                assert "d" in scan[0]  # data

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    def test_cli_validate_data(self, temp_test_dir):
        """Тест валидации данных."""
        # Временно изменяем пути
        original_results = settings.results_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")

            # Создаем директорию и тестовые данные
            results_dir = Path(settings.results_dir)
            results_dir.mkdir(parents=True, exist_ok=True)

            # Создаем тестовые файлы
            test_metainfo = {
                "fields": [
                    {"n": "close", "t": "number", "description": "Close price"},
                    {"n": "volume", "t": "number", "description": "Volume"},
                ]
            }

            test_scan = [{"s": "AAPL", "d": [150.0, 1000000]}, {"s": "GOOGL", "d": [2500.0, 500000]}]

            # Сохраняем тестовые данные
            with open(results_dir / "america_metainfo.json", "w") as f:
                json.dump(test_metainfo, f)

            with open(results_dir / "america_scan.json", "w") as f:
                json.dump(test_scan, f)

            # Запускаем валидацию
            main(["validate", "--data"])

            # Если валидация прошла успешно, тест пройден
            # Если есть ошибки, они будут выведены в stdout

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results

    def test_cli_invalid_command(self, capture_output):
        """Тест обработки невалидной команды."""
        try:
            main(["invalid_command"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "error" in output.lower() or "invalid" in output.lower()

    def test_cli_invalid_market(self, temp_test_dir):
        """Тест обработки невалидного рынка."""
        # Временно изменяем пути
        original_results = settings.results_dir
        original_specs = settings.specs_dir

        try:
            settings.results_dir = str(temp_test_dir / "results")
            settings.specs_dir = str(temp_test_dir / "specs")

            # Создаем директории
            Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.specs_dir).mkdir(parents=True, exist_ok=True)

            # Запускаем генерацию с невалидным рынком
            try:
                main(["generate", "--markets", "invalid_market_12345"])
            except SystemExit:
                pass
            except Exception as e:
                # Ожидаем ошибку
                assert "invalid" in str(e).lower() or "not found" in str(e).lower()

        finally:
            # Восстанавливаем оригинальные пути
            settings.results_dir = original_results
            settings.specs_dir = original_specs

    def test_cli_no_markets_specified(self, capture_output):
        """Тест обработки отсутствия указания рынков."""
        try:
            main(["generate"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        assert "markets" in output.lower() or "required" in output.lower()

    def test_cli_version(self, capture_output):
        """Тест вывода версии."""
        try:
            main(["--version"])
        except SystemExit:
            pass

        output = capture_output.getvalue()
        # Проверяем, что выводится версия
        assert any(char.isdigit() for char in output)
