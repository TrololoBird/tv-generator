"""
Configuration module for tv-generator.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config:
    """Конфигурация tv-generator."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path("config.json")
        self.data = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Загружает конфигурацию из файла."""
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        else:
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Возвращает конфигурацию по умолчанию."""
        return {
            "generator": {"version": "2.0.0", "openapi_version": "3.1.0"},
            "data": {"source": "tv-screener", "source_version": "0.4.0", "sync_auto": False},
            "output": {"specs_dir": "docs/specs", "validate_after_generate": True},
            "validation": {"enabled": True, "strict": False},
            "testing": {"enabled": True, "structure_tests": True, "consistency_tests": True},
        }

    def save(self) -> None:
        """Сохраняет конфигурацию в файл."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение конфигурации по ключу."""
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Устанавливает значение конфигурации по ключу."""
        keys = key.split(".")
        data = self.data

        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]

        data[keys[-1]] = value


class Settings(BaseSettings):
    """Настройки с поддержкой переменных окружения."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # TradingView API Configuration
    tradingview_base_url: str = Field(
        default="https://scanner.tradingview.com", description="Base URL for TradingView API"
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    requests_per_second: int = Field(default=2, description="Rate limit: requests per second")
    burst_limit: int = Field(default=10, description="Rate limit: burst limit")
    window_size: float = Field(default=60.0, description="Rate limit: sliding window size in seconds")

    # Data directories
    data_dir: str = Field(default="data", description="Directory for data files")
    specs_dir: str = Field(default="docs/specs", description="Directory for OpenAPI specifications")
    results_dir: str = Field(default="results", description="Directory for results")
    logs_dir: str = Field(default="logs", description="Directory for log files")

    # Cookies (optional)
    cookies_path: str | None = Field(default=None, description="Path to cookies file")

    # Debug settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Legacy settings for compatibility
    version: str = "1.0.54"
    allowed_content_types: list[str] = ["application/json", "text/plain"]
    max_request_size: int = 1024 * 1024  # 1MB
    log_format: str = "{time:HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    test_tickers_per_market: int = 10
    batch_size: int = 10

    # Обновленный список поддерживаемых рынков на основе актуальных данных TradingView
    markets: dict[str, dict[str, str]] = {
        # Основные категории активов
        "forex": {"endpoint": "forex", "label_product": "forex", "description": "Forex - Валютные пары"},
        "crypto": {"endpoint": "crypto", "label_product": "crypto", "description": "Cryptocurrencies - Криптовалюты"},
        "futures": {"endpoint": "futures", "label_product": "futures", "description": "Futures - Фьючерсы"},
        "bonds": {"endpoint": "bonds", "label_product": "bonds", "description": "Bonds - Облигации"},
        "bond": {"endpoint": "bond", "label_product": "bond", "description": "Bond - Облигации (альтернативный)"},
        "options": {"endpoint": "options", "label_product": "options", "description": "Options - Опционы"},
        "cfd": {"endpoint": "cfd", "label_product": "cfd", "description": "CFD - Контракты на разность цен"},
        "coin": {"endpoint": "coin", "label_product": "coin", "description": "Coins - Монеты"},
        # Европейские рынки
        "uk": {"endpoint": "uk", "label_product": "uk", "description": "United Kingdom - Великобритания"},
        "germany": {"endpoint": "germany", "label_product": "germany", "description": "Germany - Германия"},
        "france": {"endpoint": "france", "label_product": "france", "description": "France - Франция"},
        "italy": {"endpoint": "italy", "label_product": "italy", "description": "Italy - Италия"},
        "spain": {"endpoint": "spain", "label_product": "spain", "description": "Spain - Испания"},
        "switzerland": {
            "endpoint": "switzerland",
            "label_product": "switzerland",
            "description": "Switzerland - Швейцария",
        },
        "austria": {"endpoint": "austria", "label_product": "austria", "description": "Austria - Австрия"},
        "belgium": {"endpoint": "belgium", "label_product": "belgium", "description": "Belgium - Бельгия"},
        "denmark": {"endpoint": "denmark", "label_product": "denmark", "description": "Denmark - Дания"},
        "finland": {"endpoint": "finland", "label_product": "finland", "description": "Finland - Финляндия"},
        "norway": {"endpoint": "norway", "label_product": "norway", "description": "Norway - Норвегия"},
        "sweden": {"endpoint": "sweden", "label_product": "sweden", "description": "Sweden - Швеция"},
        "poland": {"endpoint": "poland", "label_product": "poland", "description": "Poland - Польша"},
        "czech": {"endpoint": "czech", "label_product": "czech", "description": "Czech Republic - Чехия"},
        "hungary": {"endpoint": "hungary", "label_product": "hungary", "description": "Hungary - Венгрия"},
        "greece": {"endpoint": "greece", "label_product": "greece", "description": "Greece - Греция"},
        "portugal": {"endpoint": "portugal", "label_product": "portugal", "description": "Portugal - Португалия"},
        "ireland": {"endpoint": "ireland", "label_product": "ireland", "description": "Ireland - Ирландия"},
        "iceland": {"endpoint": "iceland", "label_product": "iceland", "description": "Iceland - Исландия"},
        "estonia": {"endpoint": "estonia", "label_product": "estonia", "description": "Estonia - Эстония"},
        "latvia": {"endpoint": "latvia", "label_product": "latvia", "description": "Latvia - Латвия"},
        "lithuania": {"endpoint": "lithuania", "label_product": "lithuania", "description": "Lithuania - Литва"},
        "slovakia": {"endpoint": "slovakia", "label_product": "slovakia", "description": "Slovakia - Словакия"},
        "romania": {"endpoint": "romania", "label_product": "romania", "description": "Romania - Румыния"},
        "turkey": {"endpoint": "turkey", "label_product": "turkey", "description": "Turkey - Турция"},
        "russia": {"endpoint": "russia", "label_product": "russia", "description": "Russia - Россия"},
        # Американские рынки
        "america": {"endpoint": "america", "label_product": "america", "description": "America - США"},
        "canada": {"endpoint": "canada", "label_product": "canada", "description": "Canada - Канада"},
        "brazil": {"endpoint": "brazil", "label_product": "brazil", "description": "Brazil - Бразилия"},
        "mexico": {"endpoint": "mexico", "label_product": "mexico", "description": "Mexico - Мексика"},
        "argentina": {"endpoint": "argentina", "label_product": "argentina", "description": "Argentina - Аргентина"},
        "chile": {"endpoint": "chile", "label_product": "chile", "description": "Chile - Чили"},
        "colombia": {"endpoint": "colombia", "label_product": "colombia", "description": "Colombia - Колумбия"},
        "peru": {"endpoint": "peru", "label_product": "peru", "description": "Peru - Перу"},
        # Азиатские рынки
        "japan": {"endpoint": "japan", "label_product": "japan", "description": "Japan - Япония"},
        "china": {"endpoint": "china", "label_product": "china", "description": "China - Китай"},
        "india": {"endpoint": "india", "label_product": "india", "description": "India - Индия"},
        "singapore": {"endpoint": "singapore", "label_product": "singapore", "description": "Singapore - Сингапур"},
        "hongkong": {"endpoint": "hongkong", "label_product": "hongkong", "description": "Hong Kong - Гонконг"},
        "australia": {"endpoint": "australia", "label_product": "australia", "description": "Australia - Австралия"},
        "newzealand": {
            "endpoint": "newzealand",
            "label_product": "newzealand",
            "description": "New Zealand - Новая Зеландия",
        },
        # Африканские рынки
        "southafrica": {"endpoint": "southafrica", "label_product": "southafrica", "description": "South Africa - ЮАР"},
        "kenya": {"endpoint": "kenya", "label_product": "kenya", "description": "Kenya - Кения"},
        "nigeria": {"endpoint": "nigeria", "label_product": "nigeria", "description": "Nigeria - Нигерия"},
        "egypt": {"endpoint": "egypt", "label_product": "egypt", "description": "Egypt - Египет"},
        "morocco": {"endpoint": "morocco", "label_product": "morocco", "description": "Morocco - Марокко"},
        "tunisia": {"endpoint": "tunisia", "label_product": "tunisia", "description": "Tunisia - Тунис"},
        # Ближневосточные рынки
        "israel": {"endpoint": "israel", "label_product": "israel", "description": "Israel - Израиль"},
        "uae": {"endpoint": "uae", "label_product": "uae", "description": "UAE - ОАЭ"},
        "qatar": {"endpoint": "qatar", "label_product": "qatar", "description": "Qatar - Катар"},
        "kuwait": {"endpoint": "kuwait", "label_product": "kuwait", "description": "Kuwait - Кувейт"},
        "bahrain": {"endpoint": "bahrain", "label_product": "bahrain", "description": "Bahrain - Бахрейн"},
    }


# Глобальный объект настроек
settings = Settings()
