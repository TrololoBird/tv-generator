"""
Конфигурация проекта TradingView OpenAPI Generator.
"""

import os
from typing import Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import ssl


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Версия проекта
    version: str = Field(
        default="1.0.54",
        description="Версия проекта"
    )
    
    # API настройки
    tradingview_base_url: str = Field(
        default="https://scanner.tradingview.com",
        description="Базовый URL TradingView API"
    )
    request_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Таймаут запросов в секундах"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Максимальное количество повторных попыток"
    )
    retry_delay: float = Field(
        default=1.0,
        gt=0.0,
        le=60.0,
        description="Задержка между повторными попытками в секундах"
    )
    
    # Rate limiting
    requests_per_second: int = Field(
        default=10,
        gt=0,
        le=100,
        description="Максимальное количество запросов в секунду"
    )
    burst_limit: int = Field(
        default=20,
        gt=0,
        le=1000,
        description="Максимальное количество запросов в пике"
    )
    window_size: float = Field(
        default=60.0,
        gt=0.0,
        le=3600.0,
        description="Размер окна для rate limiting в секундах"
    )
    
    # Настройки безопасности
    verify_ssl: bool = Field(
        default=True,
        description="Проверять SSL сертификаты"
    )
    ssl_verify_mode: int = Field(
        default=ssl.CERT_REQUIRED,
        ge=ssl.CERT_NONE,
        le=ssl.CERT_REQUIRED,
        description="Режим проверки SSL сертификатов"
    )
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        gt=0,
        le=10 * 1024 * 1024,  # 10MB
        description="Максимальный размер запроса в байтах"
    )
    allowed_content_types: list = Field(
        default=["application/json", "text/plain"],
        description="Разрешенные типы контента"
    )
    
    # Пути к файлам
    results_dir: str = Field(
        default="results",
        description="Директория для результатов"
    )
    specs_dir: str = Field(
        default="specs",
        description="Директория для спецификаций"
    )
    
    # Настройки рынков
    markets: Dict[str, Dict[str, str]] = Field(
        default={
            "us_stocks": {
                "endpoint": "america",
                "label_product": "screener-stock",
                "description": "US Stocks"
            },
            "us_etfs": {
                "endpoint": "america", 
                "label_product": "screener-etf",
                "description": "US ETFs"
            },
            "crypto_cex": {
                "endpoint": "crypto",
                "label_product": "screener-crypto-cex",
                "description": "Crypto CEX"
            },
            "crypto_dex": {
                "endpoint": "crypto",
                "label_product": "screener-crypto-dex", 
                "description": "Crypto DEX"
            },
            "crypto_coins": {
                "endpoint": "coin",
                "label_product": "screener-coin",
                "description": "Cryptocurrency Coins"
            },
            "forex": {
                "endpoint": "forex",
                "label_product": "screener-forex",
                "description": "Forex"
            },
            "futures": {
                "endpoint": "futures",
                "label_product": "screener-futures",
                "description": "Futures"
            },
            "cfd": {
                "endpoint": "cfd",
                "label_product": "screener-cfd",
                "description": "CFD"
            },
            "bonds": {
                "endpoint": "bond",
                "label_product": "screener-bond",
                "description": "Bonds"
            }
        },
        description="Конфигурация рынков"
    )
    
    # Настройки логирования
    log_level: str = Field(
        default="INFO",
        description="Уровень логирования"
    )
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Формат логов"
    )
    
    # Настройки тестирования
    test_tickers_per_market: int = Field(
        default=1,
        gt=0,
        le=1000,
        description="Количество тикеров для тестирования на рынок"
    )
    batch_size: int = Field(
        default=50,
        gt=0,
        le=1000,
        description="Размер батча для запросов полей"
    )
    
    # Путь к cookies для TradingView (авторизация)
    cookies_path: str = Field(
        default="",
        description=(
            "Путь к файлу cookies (Netscape/JSON/rookiepy) "
            "для TradingView API"
        )
    )
    
    @field_validator('tradingview_base_url')
    @classmethod
    def validate_url(cls, v):
        """Валидация URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL должен начинаться с http:// или https://')
        if not v.endswith('.tradingview.com'):
            raise ValueError('URL должен быть в домене tradingview.com')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Валидация уровня логирования."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Уровень логирования должен быть одним из: {valid_levels}')
        return v.upper()
    
    @field_validator('allowed_content_types')
    @classmethod
    def validate_content_types(cls, v):
        """Валидация разрешенных типов контента."""
        if not v:
            raise ValueError('Список разрешенных типов контента не может быть пустым')
        if not all(isinstance(ct, str) for ct in v):
            raise ValueError('Все типы контента должны быть строками')
        return v
    
    @field_validator('results_dir', 'specs_dir')
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Валидация директорий."""
        # Проверка на инъекции в путях
        if '..' in v or '//' in v:
            raise ValueError('Недопустимые символы в пути')
            
        # Создание директории если не существует
        if not os.path.exists(v):
            try:
                os.makedirs(v, mode=0o755, exist_ok=True)
            except OSError as e:
                raise ValueError(f'Не удалось создать директорию {v}: {e}')
                
        # Проверка прав доступа
        if not os.access(v, os.R_OK | os.W_OK):
            raise ValueError(f'Недостаточно прав для директории {v}')
            
        return v
    
    @field_validator('markets')
    @classmethod
    def validate_markets(cls, v: Dict) -> Dict:
        """Валидация конфигурации рынков."""
        if not v:
            raise ValueError('Список рынков не может быть пустым')
            
        required_keys = {'endpoint', 'label_product', 'description'}
        
        for market, config in v.items():
            # Проверка наличия всех обязательных полей
            if not isinstance(config, dict):
                raise ValueError(f'Неверный формат конфигурации для рынка {market}')
                
            missing_keys = required_keys - set(config.keys())
            if missing_keys:
                raise ValueError(
                    f'Отсутствуют обязательные поля для рынка {market}: {missing_keys}'
                )
            
            # Валидация значений
            if not isinstance(config['endpoint'], str):
                raise ValueError(
                    f'Endpoint для рынка {market} должен быть строкой'
                )
            if not isinstance(config['label_product'], str):
                raise ValueError(
                    f'Label product для рынка {market} должен быть строкой'
                )
            if not isinstance(config['description'], str):
                raise ValueError(
                    f'Description для рынка {market} должен быть строкой'
                )
                
            # Проверка формата значений
            if not config['endpoint'].isalnum():
                raise ValueError(
                    f'Endpoint для рынка {market} может содержать только буквы и цифры'
                )
            if not config['label_product'].startswith('screener-'):
                raise ValueError(
                    f'Label product для рынка {market} должен начинаться с "screener-"'
                )
                
        return v
    
    @field_validator('max_request_size')
    @classmethod
    def validate_max_request_size(cls, v: int) -> int:
        """Валидация максимального размера запроса."""
        min_size = 1024  # 1KB
        max_size = 10 * 1024 * 1024  # 10MB
        
        if not min_size <= v <= max_size:
            raise ValueError(
                f'Размер запроса должен быть между {min_size} и {max_size} байт'
            )
            
        return v
    
    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Валидация размера батча."""
        if not 1 <= v <= 1000:
            raise ValueError('Размер батча должен быть между 1 и 1000')
            
        return v
    
    @field_validator('test_tickers_per_market')
    @classmethod
    def validate_test_tickers(cls, v: int) -> int:
        """Валидация количества тестовых тикеров."""
        if not 1 <= v <= 1000:
            raise ValueError('Количество тестовых тикеров должно быть между 1 и 1000')
            
        return v
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False
    }


# Глобальный экземпляр настроек
settings = Settings() 