"""
Тесты для config модуля.
"""

import pytest
import os
import json
from pathlib import Path
from pydantic import ValidationError
from typing import Dict, Any
import ssl

from tv_generator.config import Settings


class TestSettings:
    """Тесты для Settings."""
    
    @pytest.fixture
    def test_config_dir(self) -> Path:
        """Фикстура для директории с тестовыми конфигурациями."""
        config_dir = Path(__file__).parent / "test_config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def test_default_settings(self) -> None:
        """Тест настроек по умолчанию."""
        settings = Settings()
        
        # Базовые настройки
        assert settings.version == "1.0.54"
        assert settings.tradingview_base_url == "https://scanner.tradingview.com"
        assert settings.request_timeout == 60
        assert settings.max_retries == 3
        assert settings.retry_delay == 1.0
        
        # Настройки rate limiting
        assert settings.requests_per_second == 10
        assert settings.burst_limit == 20
        assert settings.window_size == 60.0
        
        # Настройки директорий
        assert settings.results_dir == "results"
        assert settings.specs_dir == "specs"
        
        # Настройки логирования
        assert settings.log_level == "INFO"
        assert "{time:" in settings.log_format
        
        # Настройки тестирования
        assert settings.test_tickers_per_market == 1
        assert settings.batch_size == 50
        
        # Настройки безопасности
        assert settings.verify_ssl is True
        assert settings.ssl_verify_mode == ssl.CERT_REQUIRED
        assert settings.max_request_size == 1024 * 1024  # 1MB
        assert settings.allowed_content_types == ["application/json", "text/plain"]
        
        # Настройки cookies
        assert settings.cookies_path == ""

    def test_custom_settings(self) -> None:
        """Тест пользовательских настроек."""
        # Используем переменные окружения для тестирования
        env_vars = {
            "REQUEST_TIMEOUT": "45",
            "MAX_RETRIES": "4",
            "REQUESTS_PER_SECOND": "8",
            "BURST_LIMIT": "15",
            "WINDOW_SIZE": "45.0",
            "VERIFY_SSL": "false",
            "MAX_REQUEST_SIZE": "2097152",  # 2MB
            "ALLOWED_CONTENT_TYPES": '["application/json", "text/plain"]',
            "COOKIES_PATH": "/custom/cookies.txt",
            "LOG_LEVEL": "DEBUG"
        }
        
        try:
            # Устанавливаем переменные окружения
            for key, value in env_vars.items():
                os.environ[key] = value
            
            # Создаем новые настройки
            settings = Settings()
            
            # Проверяем, что настройки загрузились
            assert settings.request_timeout == 45
            assert settings.max_retries == 4
            assert settings.requests_per_second == 8
            assert settings.burst_limit == 15
            assert settings.window_size == 45.0
            assert settings.verify_ssl is False
            assert settings.max_request_size == 2097152
            assert settings.allowed_content_types == ["application/json", "text/plain"]
            assert settings.cookies_path == "/custom/cookies.txt"
            assert settings.log_level == "DEBUG"
            
        finally:
            # Очищаем переменные окружения
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_markets_configuration(self) -> None:
        """Тест конфигурации рынков."""
        settings = Settings()
        
        # Проверяем наличие всех рынков
        expected_markets = {
            'us_stocks', 'us_etfs', 'crypto_cex', 'crypto_dex', 
            'crypto_coins', 'forex', 'futures', 'cfd', 'bonds'
        }
        assert set(settings.markets.keys()) == expected_markets
        
        # Проверяем структуру каждого рынка
        for market_name, market_config in settings.markets.items():
            assert isinstance(market_config, dict)
            assert "endpoint" in market_config
            assert "label_product" in market_config
            assert "description" in market_config
            
            assert isinstance(market_config["endpoint"], str)
            assert isinstance(market_config["label_product"], str)
            assert isinstance(market_config["description"], str)
            
            # Проверяем валидность endpoint
            assert "/" not in market_config["endpoint"]
            assert "\\" not in market_config["endpoint"]
            assert ";" not in market_config["endpoint"]
            
            # Проверяем валидность label_product
            assert market_config["label_product"].startswith("screener-")
            
            # Проверяем описание
            assert len(market_config["description"]) > 0

    def test_log_format_configuration(self) -> None:
        """Тест конфигурации формата логов."""
        settings = Settings()
        log_format = settings.log_format
        # Проверяем обязательные элементы
        required_elements = [
            "{time:",
            "{level:",
            "{name}",
            "{function}",
            "{line}",
            "{message}"
        ]
        for element in required_elements:
            assert element in log_format
        # Проверяем цветовое форматирование
        assert "<" in log_format  # Начало цветового тега
        assert ">" in log_format  # Конец цветового тега

    def test_environment_variables(self) -> None:
        """Тест загрузки настроек из переменных окружения."""
        env_vars = {
            "REQUEST_TIMEOUT": "45",
            "MAX_RETRIES": "4",
            "REQUESTS_PER_SECOND": "8",
            "BURST_LIMIT": "15",
            "WINDOW_SIZE": "45.0",
            "VERIFY_SSL": "false",
            "MAX_REQUEST_SIZE": "2097152",  # 2MB
            "ALLOWED_CONTENT_TYPES": '["application/json", "text/plain"]',
            "COOKIES_PATH": "/custom/cookies.txt",
            "LOG_LEVEL": "DEBUG"
        }
        
        try:
            # Устанавливаем переменные окружения
            for key, value in env_vars.items():
                os.environ[key] = value
            
            settings = Settings()
            
            # Проверяем все настройки
            assert settings.request_timeout == 45
            assert settings.max_retries == 4
            assert settings.requests_per_second == 8
            assert settings.burst_limit == 15
            assert settings.window_size == 45.0
            assert settings.verify_ssl is False
            assert settings.max_request_size == 2097152
            assert settings.allowed_content_types == ["application/json", "text/plain"]
            assert settings.cookies_path == "/custom/cookies.txt"
            assert settings.log_level == "DEBUG"
            
        finally:
            # Очищаем переменные окружения
            for key in env_vars:
                os.environ.pop(key, None)

    def test_settings_validation(self) -> None:
        """Тест валидации настроек."""
        invalid_settings = [
            {"request_timeout": -1},
            {"max_retries": -1},
            {"requests_per_second": 0},
            {"retry_delay": -1.0},
            {"test_tickers_per_market": 0},
            {"batch_size": 0},
            {"burst_limit": -1},
            {"window_size": -1.0},
            {"max_request_size": 0},
            {"allowed_content_types": []},
            {"log_level": "INVALID"}
        ]
        
        for invalid_setting in invalid_settings:
            with pytest.raises(ValidationError):
                Settings(**invalid_setting)

    def test_settings_serialization(self) -> None:
        """Тест сериализации настроек."""
        settings = Settings()
        
        # Тест в JSON
        json_data = settings.model_dump_json()
        assert isinstance(json_data, str)
        
        # Тест в dict
        dict_data = settings.model_dump()
        assert isinstance(dict_data, dict)
        assert "version" in dict_data
        assert "tradingview_base_url" in dict_data
        
        # Тест из dict
        new_settings = Settings(**dict_data)
        assert new_settings.version == settings.version
        assert new_settings.tradingview_base_url == settings.tradingview_base_url


class TestSettingsValidation:
    """Тесты валидации настроек."""
    
    def test_invalid_timeout(self) -> None:
        """Тест невалидного таймаута."""
        with pytest.raises(ValidationError):
            Settings(request_timeout=-1)
    
    def test_invalid_retries(self) -> None:
        """Тест невалидного количества повторных попыток."""
        with pytest.raises(ValidationError):
            Settings(max_retries=-1)
    
    def test_invalid_rate_limit(self) -> None:
        """Тест невалидного rate limit."""
        with pytest.raises(ValidationError):
            Settings(requests_per_second=0)
    
    def test_invalid_retry_delay(self) -> None:
        """Тест невалидной задержки повторных попыток."""
        with pytest.raises(ValidationError):
            Settings(retry_delay=-1.0)
    
    def test_invalid_test_tickers(self) -> None:
        """Тест невалидного количества тестовых тикеров."""
        with pytest.raises(ValidationError):
            Settings(test_tickers_per_market=0)
    
    def test_invalid_batch_size(self) -> None:
        """Тест невалидного размера батча."""
        with pytest.raises(ValidationError):
            Settings(batch_size=0)
    
    def test_invalid_log_level(self) -> None:
        """Тест невалидного уровня логирования."""
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")
    
    def test_invalid_url(self) -> None:
        """Тест невалидного URL."""
        with pytest.raises(ValidationError):
            Settings(tradingview_base_url="invalid-url")
    
    def test_invalid_ssl_verify_mode(self) -> None:
        """Тест невалидного режима проверки SSL."""
        with pytest.raises(ValidationError):
            Settings(ssl_verify_mode=999)
    
    def test_invalid_max_request_size(self) -> None:
        """Тест невалидного максимального размера запроса."""
        with pytest.raises(ValidationError):
            Settings(max_request_size=0)
    
    def test_invalid_content_types(self) -> None:
        """Тест невалидных типов контента."""
        with pytest.raises(ValidationError):
            Settings(allowed_content_types=[])


class TestSettingsIntegration:
    """Интеграционные тесты настроек."""
    
    def test_settings_singleton(self) -> None:
        """Тест синглтона настроек."""
        settings1 = Settings()
        settings2 = Settings()
        assert settings1.version == settings2.version
        assert settings1.tradingview_base_url == settings2.tradingview_base_url
    
    def test_settings_persistence(self, tmp_path: Path) -> None:
        """Тест персистентности настроек."""
        # Создаем временный файл конфигурации
        config_file = tmp_path / "test_config.json"
        config_data = {
            "request_timeout": 30,
            "max_retries": 2,
            "log_level": "DEBUG"
        }
        
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        
        # Загружаем настройки через переменные окружения
        os.environ["REQUEST_TIMEOUT"] = "30"
        os.environ["MAX_RETRIES"] = "2"
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        try:
            settings1 = Settings()
            settings2 = Settings()
            
            # Проверяем, что настройки одинаковые
            assert settings1.request_timeout == settings2.request_timeout
            assert settings1.max_retries == settings2.max_retries
            assert settings1.log_level == settings2.log_level
        finally:
            # Очищаем переменные окружения
            for key in ["REQUEST_TIMEOUT", "MAX_RETRIES", "LOG_LEVEL"]:
                if key in os.environ:
                    del os.environ[key]
    
    def test_markets_configuration_access(self) -> None:
        """Тест доступа к конфигурации рынков."""
        settings = Settings()
        
        # Проверяем доступ к рынкам
        assert "us_stocks" in settings.markets
        assert "crypto_cex" in settings.markets
        
        # Проверяем структуру рынка
        us_stocks = settings.markets["us_stocks"]
        assert us_stocks["endpoint"] == "america"
        assert us_stocks["label_product"] == "screener-stock"
        assert us_stocks["description"] == "US Stocks" 