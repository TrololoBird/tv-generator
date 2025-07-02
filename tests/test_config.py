"""
Тесты для модуля конфигурации.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from tv_generator.config import Settings


class TestSettings:
    """Тесты для класса Settings."""

    def test_default_settings(self):
        """Тест значений по умолчанию."""
        settings = Settings()

        assert settings.version == "1.0.54"
        assert settings.tradingview_base_url == "https://scanner.tradingview.com"
        assert settings.request_timeout == 30
        assert settings.max_retries == 3
        assert settings.retry_delay == 1.0
        assert settings.requests_per_second == 10
        assert settings.burst_limit == 10
        assert settings.window_size == 60.0
        assert settings.max_request_size == 1024 * 1024
        assert settings.cookies_path is None
        assert settings.results_dir == "results"
        assert settings.specs_dir == "docs/specs"
        assert settings.log_level == "INFO"
        assert settings.test_tickers_per_market == 10
        assert settings.batch_size == 10

    def test_markets_configuration(self):
        """Тест конфигурации рынков."""
        settings = Settings()

        expected_markets = {"america", "crypto", "forex", "futures", "cfd", "bond", "coin"}

        assert set(settings.markets.keys()) == expected_markets

        # Проверяем структуру каждого рынка
        for market_name, config in settings.markets.items():
            assert "endpoint" in config
            assert "label_product" in config
            assert "description" in config
            assert isinstance(config["endpoint"], str)
            assert isinstance(config["label_product"], str)
            assert isinstance(config["description"], str)

    def test_log_format_configuration(self):
        """Тест конфигурации формата логов."""
        settings = Settings()

        log_format = settings.log_format
        assert isinstance(log_format, str)
        assert "{time" in log_format
        assert "{level" in log_format
        assert "{name" in log_format
        assert "{function" in log_format
        assert "{line" in log_format
        assert "{message" in log_format

    def test_allowed_content_types(self):
        """Тест разрешенных типов контента."""
        settings = Settings()

        assert isinstance(settings.allowed_content_types, list)
        assert "application/json" in settings.allowed_content_types
        assert "text/plain" in settings.allowed_content_types

    def test_settings_persistence(self):
        """Тест персистентности настроек."""
        settings1 = Settings()
        settings2 = Settings()

        # Проверяем, что настройки одинаковые
        assert settings1.version == settings2.version
        assert settings1.tradingview_base_url == settings2.tradingview_base_url
        assert settings1.request_timeout == settings2.request_timeout

    def test_markets_configuration_access(self):
        """Тест доступа к конфигурации рынков."""
        settings = Settings()

        # Проверяем доступ к конкретным рынкам
        assert "america" in settings.markets
        assert settings.markets["america"]["endpoint"] == "america"
        assert settings.markets["america"]["description"] == "US Stocks"

        assert "crypto" in settings.markets
        assert settings.markets["crypto"]["endpoint"] == "crypto"
        assert settings.markets["crypto"]["description"] == "Cryptocurrencies"


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
        settings = Settings()

        # Проверяем, что настройки сохраняются
        assert settings.version == "1.0.54"
        assert settings.tradingview_base_url == "https://scanner.tradingview.com"

    def test_markets_configuration_access(self) -> None:
        """Тест доступа к конфигурации рынков."""
        settings = Settings()

        # Проверяем доступ к конкретным рынкам
        assert "america" in settings.markets
        assert settings.markets["america"]["endpoint"] == "america"
        assert settings.markets["america"]["description"] == "US Stocks"
