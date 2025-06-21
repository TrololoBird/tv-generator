"""
Интеграционные тесты для end-to-end сценариев.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
from tv_generator.core import Pipeline, MarketData, PipelineError
from tv_generator.api import TradingViewAPI
from tv_generator.config import settings
import os
import json
from openapi_spec_validator import validate_spec


class TestIntegration:
    """Интеграционные тесты."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Фикстура для временной директории результатов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_api_responses(self):
        """Фикстура с мок-ответами API."""
        return {
            "metainfo": {
                "fields": [
                    {"name": "close", "type": "number", "description": "Close price"},
                    {"name": "volume", "type": "number", "description": "Volume"},
                    {"name": "name", "type": "string", "description": "Company name"}
                ]
            },
            "tickers": [
                {"name": "AAPL", "close": 150.0, "volume": 1000000},
                {"name": "GOOGL", "close": 2500.0, "volume": 500000}
            ],
            "field_data": {
                "close": 150.0,
                "volume": 1000000,
                "name": "Apple Inc."
            }
        }
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, temp_results_dir, mock_api_responses):
        """Тест полного пайплайна с моками."""
        with patch.object(settings, 'results_dir', str(temp_results_dir)):
            with patch('tv_generator.api.TradingViewAPI') as mock_api_class:
                # Настройка мока API
                mock_api = AsyncMock(spec=TradingViewAPI)
                mock_api_class.return_value = mock_api
                
                mock_api.get_metainfo.return_value = mock_api_responses["metainfo"]
                mock_api.scan_tickers.return_value = mock_api_responses["tickers"]
                mock_api.test_field.side_effect = [True, True, True]  # Все поля работают
                mock_api.get_field_data.return_value = mock_api_responses["field_data"]
                
                # Мокаем контекстный менеджер
                mock_api.__aenter__ = AsyncMock(return_value=mock_api)
                mock_api.__aexit__ = AsyncMock(return_value=None)
                
                # Запуск пайплайна
                pipeline = Pipeline()
                await pipeline.run()
                
                # Проверяем, что файлы созданы
                assert (temp_results_dir / "us_stocks_metainfo.json").exists()
                assert (temp_results_dir / "us_stocks_tickers.json").exists()
                assert (temp_results_dir / "us_stocks_fields.txt").exists()
                assert (temp_results_dir / "us_stocks_working_fields.txt").exists()
                assert (temp_results_dir / "us_stocks_openapi_fields.json").exists()
    
    @pytest.mark.asyncio
    async def test_single_market_processing(self, temp_results_dir, mock_api_responses):
        """Тест обработки одного рынка."""
        with patch.object(settings, 'results_dir', str(temp_results_dir)):
            with patch('tv_generator.api.TradingViewAPI') as mock_api_class:
                mock_api = AsyncMock(spec=TradingViewAPI)
                mock_api_class.return_value = mock_api
                
                mock_api.get_metainfo.return_value = mock_api_responses["metainfo"]
                mock_api.scan_tickers.return_value = [mock_api_responses["tickers"][0]]  # 1 тикер
                mock_api.test_field.side_effect = [True, True, True]
                mock_api.get_field_data.return_value = mock_api_responses["field_data"]
                
                mock_api.__aenter__ = AsyncMock(return_value=mock_api)
                mock_api.__aexit__ = AsyncMock(return_value=None)
                
                pipeline = Pipeline()
                market_config = settings.markets["us_stocks"]
                market_data = await pipeline.fetch_market_data("us_stocks", market_config)
                
                # Проверяем результат
                assert market_data.name == "us_stocks"
                assert len(market_data.tickers) == 1  # теперь всегда 1 тикер
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, temp_results_dir):
        """Тест обработки ошибок API."""
        print(f"DEBUG: Starting test_api_error_handling")
        print(f"DEBUG: temp_results_dir = {temp_results_dir}")
        
        with patch.object(settings, 'results_dir', str(temp_results_dir)):
            pipeline = Pipeline()
            market_config = settings.markets["us_stocks"]
            
            print(f"DEBUG: Created pipeline with results_dir = {pipeline.results_dir}")
            print(f"DEBUG: Market config = {market_config}")
            print(f"DEBUG: About to call fetch_market_data with 'us_stocks'")
            
            # Применяем mock к уже созданному API экземпляру
            with patch.object(pipeline.api, 'get_metainfo', side_effect=Exception("API Error")):
                # Ожидаем PipelineError, а не typer.Exit
                try:
                    await pipeline.fetch_market_data("us_stocks", market_config)
                    print(f"DEBUG: fetch_market_data completed without exception")
                    assert False, "Expected PipelineError but no exception was raised"
                except PipelineError as e:
                    print(f"DEBUG: Caught expected PipelineError: {e}")
                    # Тест прошел успешно
                except Exception as e:
                    print(f"DEBUG: Caught unexpected exception: {type(e).__name__}: {e}")
                    raise
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, temp_results_dir):
        """Тест проверки здоровья системы."""
        with patch.object(settings, 'results_dir', str(temp_results_dir)):
            with patch('tv_generator.api.TradingViewAPI') as mock_api_class:
                mock_api = AsyncMock(spec=TradingViewAPI)
                mock_api_class.return_value = mock_api
                
                mock_api.health_check.return_value = {
                    "status": "healthy",
                    "endpoints": {"america": "healthy"}
                }
                
                mock_api.__aenter__ = AsyncMock(return_value=mock_api)
                mock_api.__aexit__ = AsyncMock(return_value=None)
                
                pipeline = Pipeline()
                health_status = await pipeline.health_check()
                
                assert health_status["status"] == "healthy"
                assert "pipeline" in health_status
    
    def test_config_validation(self):
        """Тест валидации конфигурации."""
        # Проверяем, что все необходимые поля присутствуют
        assert hasattr(settings, 'tradingview_base_url')
        assert hasattr(settings, 'request_timeout')
        assert hasattr(settings, 'max_retries')
        assert hasattr(settings, 'requests_per_second')
        assert hasattr(settings, 'markets')
        
        # Проверяем структуру рынков
        for market_name, config in settings.markets.items():
            assert 'endpoint' in config
            assert 'label_product' in config
            assert 'description' in config
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, temp_results_dir, mock_api_responses):
        """Тест батчевой обработки полей."""
        with patch.object(settings, 'results_dir', str(temp_results_dir)):
            with patch.object(settings, 'batch_size', 2):  # Маленький размер батча для теста
                with patch('tv_generator.api.TradingViewAPI') as mock_api_class:
                    mock_api = AsyncMock(spec=TradingViewAPI)
                    mock_api_class.return_value = mock_api
                    
                    mock_api.get_metainfo.return_value = mock_api_responses["metainfo"]
                    mock_api.scan_tickers.return_value = [mock_api_responses["tickers"][0]]  # 1 тикер
                    mock_api.test_field.side_effect = [True, True, True]
                    mock_api.get_field_data.return_value = mock_api_responses["field_data"]
                    
                    mock_api.__aenter__ = AsyncMock(return_value=mock_api)
                    mock_api.__aexit__ = AsyncMock(return_value=None)
                    
                    pipeline = Pipeline()
                    market_config = settings.markets["us_stocks"]
                    market_data = await pipeline.fetch_market_data("us_stocks", market_config)
                    
                    # Теперь все поля рабочие (NO COOKIES MODE)
                    assert len(market_data.working_fields) == len(market_data.fields)


class TestCLIIntegration:
    """Интеграционные тесты CLI."""
    
    def test_cli_info_command(self, capsys):
        """Тест команды info."""
        from tv_generator.cli import info
        
        info()
        captured = capsys.readouterr()
        
        assert "TradingView OpenAPI Generator Info" in captured.out
        assert "Поддерживаемые рынки" in captured.out
        assert "us_stocks" in captured.out
    
    def test_cli_validate_command(self, capsys):
        """Тест команды validate."""
        from tv_generator.cli import validate
        
        validate()
        captured = capsys.readouterr()
        
        assert "Результаты валидации" in captured.out
        assert "Конфигурация рынков" in captured.out
        assert "API URL" in captured.out
    
    @pytest.mark.asyncio
    async def test_cli_health_command(self, capsys):
        """Тест команды health."""
        with patch('tv_generator.api.TradingViewAPI') as mock_api_class:
            mock_api = AsyncMock(spec=TradingViewAPI)
            mock_api_class.return_value = mock_api
            
            mock_api.health_check.return_value = {
                "status": "healthy",
                "endpoints": {"america": "healthy"}
            }
            
            mock_api.__aenter__ = AsyncMock(return_value=mock_api)
            mock_api.__aexit__ = AsyncMock(return_value=None)
            
            from tv_generator.cli import health_check_async
            await health_check_async()
            out, _ = capsys.readouterr()
            assert "healthy" in out
    
    @pytest.mark.asyncio
    async def test_cli_fetch_data_command(self, capsys):
        """Тест команды fetch-data."""
        with patch('tv_generator.core.Pipeline') as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            
            mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
            mock_pipeline.__aexit__ = AsyncMock(return_value=None)
            
            from tv_generator.cli import fetch_data_async
            await fetch_data_async()
            out, _ = capsys.readouterr()
            assert "Сбор данных завершен успешно" in out


class TestDataPersistence:
    """Тесты сохранения данных."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Фикстура для временной директории результатов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_market_data_serialization(self, temp_results_dir):
        """Тест сериализации данных рынка."""
        market_data = MarketData(
            name="test_market",
            endpoint="america",
            label_product="screener-stock",
            description="Test Market",
            metainfo={"fields": [{"name": "close", "type": "number"}]},
            tickers=[{"name": "AAPL", "close": 150.0}],
            fields=["close"],
            working_fields=["close"],
            openapi_fields={"close": {"type": "number"}}
        )
        
        pipeline = Pipeline()
        pipeline.results_dir = temp_results_dir
        
        # Сохраняем данные
        pipeline.save_market_data(market_data)
        
        # Проверяем, что файлы созданы
        assert (temp_results_dir / "test_market_metainfo.json").exists()
        assert (temp_results_dir / "test_market_tickers.json").exists()
        assert (temp_results_dir / "test_market_fields.txt").exists()
        assert (temp_results_dir / "test_market_working_fields.txt").exists()
        assert (temp_results_dir / "test_market_openapi_fields.json").exists()
    
    def test_data_file_contents(self, temp_results_dir):
        """Тест содержимого файлов данных."""
        market_data = MarketData(
            name="test_market",
            endpoint="america",
            label_product="screener-stock",
            description="Test Market",
            metainfo={"fields": [{"name": "close", "type": "number"}]},
            tickers=[{"name": "AAPL", "close": 150.0}],
            fields=["close"],
            working_fields=["close"],
            openapi_fields={"close": {"type": "number"}}
        )
        
        pipeline = Pipeline()
        pipeline.results_dir = temp_results_dir
        
        # Сохраняем данные
        pipeline.save_market_data(market_data)
        
        # Проверяем содержимое файлов
        import json
        
        # Проверяем metainfo
        with open(temp_results_dir / "test_market_metainfo.json", "r") as f:
            metainfo = json.load(f)
            assert "fields" in metainfo
            assert len(metainfo["fields"]) == 1
        
        # Проверяем tickers
        with open(temp_results_dir / "test_market_tickers.json", "r") as f:
            tickers = json.load(f)
            assert len(tickers) == 1
            assert tickers[0]["name"] == "AAPL"
        
        # Проверяем fields
        with open(temp_results_dir / "test_market_fields.txt", "r") as f:
            fields = f.read().strip().split("\n")
            assert "close" in fields
        
        # Проверяем working_fields
        with open(temp_results_dir / "test_market_working_fields.txt", "r") as f:
            working_fields = f.read().strip().split("\n")
            assert "close" in working_fields
        
        # Проверяем openapi_fields
        with open(temp_results_dir / "test_market_openapi_fields.json", "r") as f:
            openapi_fields = json.load(f)
            assert "close" in openapi_fields
            assert openapi_fields["close"]["type"] == "number"


SPECS_DIR = os.path.join(os.path.dirname(__file__), '..', 'specs')

# Список всех спецификаций, которые должны быть
EXPECTED_SPECS = [
    'us_stocks_openapi.json',
    'us_etf_openapi.json',
    'crypto_dex_openapi.json',
    'coin_openapi.json',
    'bond_openapi.json',
    'forex_openapi.json',
    'cfd_openapi.json',
    'futures_openapi.json',
]

def load_spec(filename):
    path = os.path.join(SPECS_DIR, filename)
    with open(path, encoding='utf-8') as f:
        return json.load(f)

@pytest.mark.parametrize('spec_file', EXPECTED_SPECS)
def test_openapi_spec_valid(spec_file):
    """Проверяет, что спецификация валидна по OpenAPI 3.1.0."""
    spec = load_spec(spec_file)
    validate_spec(spec)

@pytest.mark.parametrize('spec_file', EXPECTED_SPECS)
def test_openapi_spec_has_examples(spec_file):
    """Проверяет, что в спецификации есть хотя бы один пример запроса/ответа."""
    spec = load_spec(spec_file)
    found_example = False
    
    # Проверяем примеры в requestBody и responses
    paths = spec.get('paths', {})
    for path_item in paths.values():
        for method in path_item.values():
            # Примеры в requestBody
            req_body = method.get('requestBody', {})
            content = req_body.get('content', {})
            for media in content.values():
                # Проверяем примеры в content
                if 'example' in media or 'examples' in media:
                    found_example = True
                # Проверяем примеры в schema
                schema = media.get('schema', {})
                if 'example' in schema or 'examples' in schema:
                    found_example = True
            
            # Примеры в responses
            responses = method.get('responses', {})
            for resp in responses.values():
                content = resp.get('content', {})
                for media in content.values():
                    # Проверяем примеры в content
                    if 'example' in media or 'examples' in media:
                        found_example = True
                    # Проверяем примеры в schema
                    schema = media.get('schema', {})
                    if 'example' in schema or 'examples' in schema:
                        found_example = True
    
    # Проверяем примеры в компонентах схем
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    for schema_name, schema_data in schemas.items():
        if 'example' in schema_data:
            found_example = True
    
    assert found_example, f"No examples found in {spec_file}" 