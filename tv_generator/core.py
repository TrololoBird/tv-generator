"""
Основная логика обработки данных TradingView API.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from loguru import logger
from .api import TradingViewAPI, TradingViewAPIError
from .config import settings


@dataclass
class MarketData:
    """Данные по рынку."""
    name: str
    endpoint: str
    label_product: str
    description: str
    metainfo: Dict[str, Any]
    tickers: List[Dict[str, Any]]
    fields: List[str]
    working_fields: List[str]
    openapi_fields: Dict[str, Any]


class PipelineError(Exception):
    """Базовый класс для ошибок пайплайна."""
    pass


class Pipeline:
    """Основной пайплайн обработки данных."""
    
    def __init__(self) -> None:
        self.api = TradingViewAPI()
        self.results_dir = Path(settings.results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Создаем директорию для логов
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Настройка логирования
        logger.remove()
        logger.add(
            "logs/pipeline.log",
            level=settings.log_level,
            format=settings.log_format,
            rotation="10 MB",
            retention="7 days"
        )
        logger.add(
            lambda msg: print(msg, end=""),
            level=settings.log_level,
            format=settings.log_format
        )
    
    def _extract_fields(self, metainfo: Dict[str, Any]) -> List[str]:
        """Извлекает поля из metainfo."""
        fields = []
        if 'fields' in metainfo:
            for field_info in metainfo['fields']:
                if isinstance(field_info, dict) and 'n' in field_info:
                    fields.append(field_info['n'])
                elif isinstance(field_info, str):
                    fields.append(field_info)
        return fields
    
    async def fetch_market_data(
        self, 
        market_name: str, 
        market_config: Dict[str, str]
    ) -> MarketData:
        """Получение данных для одного рынка."""
        logger.info(f"Processing market: {market_name}")
        endpoint = market_config["endpoint"]
        label_product = market_config["label_product"]
        description = market_config["description"]
        
        try:
            # Получение metainfo
            logger.info(f"Fetching metainfo for {market_name}")
            metainfo = await self.api.get_metainfo(endpoint)
            fields = self._extract_fields(metainfo)
            working_fields = fields.copy()
            openapi_fields = self._create_openapi_fields(metainfo, working_fields)
            
            # Получение тикеров
            logger.info(f"Fetching tickers for {market_name}")
            tickers = await self.api.scan_tickers(
                endpoint, 
                label_product, 
                limit=settings.test_tickers_per_market
            )
            
            # Всегда должен быть хотя бы один тикер для тестирования
            if not tickers:
                error_msg = f"No tickers found for market {market_name}"
                logger.error(error_msg)
                raise PipelineError(error_msg)
            
            logger.info(f"Found {len(fields)} fields for {market_name}")
            if fields:
                logger.info(f"First 3 extracted fields: {fields[:3]}")
            
            logger.info(f"Tickers fetched: {len(tickers)}")
            if tickers:
                logger.info(f"First ticker: {tickers[0]}")
            
            return MarketData(
                name=market_name,
                endpoint=endpoint,
                label_product=label_product,
                description=description,
                metainfo=metainfo,
                tickers=tickers,
                fields=fields,
                working_fields=working_fields,
                openapi_fields=openapi_fields
            )
        except TradingViewAPIError as e:
            logger.error(f"API error processing market {market_name}: {e}")
            raise PipelineError(f"Failed to process market {market_name}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error processing market {market_name}: {e}"
            )
            raise PipelineError(f"Unexpected error processing market {market_name}: {e}")
    
    def _create_openapi_fields(
        self, 
        metainfo: Dict[str, Any], 
        working_fields: List[str]
    ) -> Dict[str, Any]:
        """Создает OpenAPI спецификацию для полей."""
        openapi_fields = {}
        if 'fields' in metainfo:
            for field_info in metainfo['fields']:
                if isinstance(field_info, dict):
                    field_name = field_info.get('n')
                    if field_name and field_name in working_fields:
                        field_type = field_info.get('t', 'string')
                        field_desc = field_info.get('description', f'Field: {field_name}')
                        field_range = field_info.get('r')
                        
                        field_spec = {
                            'type': self._map_tradingview_type_to_openapi(field_type),
                            'description': field_desc
                        }
                        
                        # Добавляем enum если есть диапазон значений
                        if field_range and isinstance(field_range, list):
                            field_spec['enum'] = field_range
                        
                        openapi_fields[field_name] = field_spec
        return openapi_fields
    
    def _map_tradingview_type_to_openapi(self, tv_type: str) -> str:
        """Преобразует тип TradingView в тип OpenAPI."""
        type_mapping = {
            'string': 'string',
            'number': 'number',
            'integer': 'integer',
            'boolean': 'boolean',
            # Реальные типы из анализа данных TradingView
            'price': 'number',
            'num_slice': 'number',
            'text': 'string',
            'fundamental_price': 'number',
            'map': 'string',
            'percent': 'number',
            'time': 'string',
            'bool': 'boolean',
            'time-yyyymmdd': 'string',
            'interface': 'string',
            'set': 'string'
        }
        return type_mapping.get(tv_type, 'string')
    
    def save_market_data(self, market_data: MarketData) -> None:
        """Сохранение данных рынка в файлы."""
        market_name = market_data.name
        
        try:
            # Сохранение metainfo
            metainfo_file = self.results_dir / f"{market_name}_metainfo.json"
            with open(metainfo_file, "w", encoding="utf-8") as f:
                json.dump(market_data.metainfo, f, indent=2, ensure_ascii=False)
            
            # Сохранение тикеров
            tickers_file = self.results_dir / f"{market_name}_tickers.json"
            with open(tickers_file, "w", encoding="utf-8") as f:
                json.dump(market_data.tickers, f, indent=2, ensure_ascii=False)
            
            # Сохранение всех полей
            fields_file = self.results_dir / f"{market_name}_fields.txt"
            with open(fields_file, "w", encoding="utf-8") as f:
                for field in market_data.fields:
                    f.write(f"{field}\n")
            
            # Сохранение рабочих полей
            working_fields_file = self.results_dir / f"{market_name}_working_fields.txt"
            with open(working_fields_file, "w", encoding="utf-8") as f:
                for field in market_data.working_fields:
                    f.write(f"{field}\n")
            
            # Сохранение OpenAPI полей
            openapi_fields_file = self.results_dir / f"{market_name}_openapi_fields.json"
            with open(openapi_fields_file, "w", encoding="utf-8") as f:
                json.dump(market_data.openapi_fields, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved data for {market_name}")
            
        except Exception as e:
            logger.error(f"Failed to save data for {market_name}: {e}")
            raise PipelineError(f"Failed to save data for {market_name}: {e}")
    
    async def run(self) -> None:
        """Запуск основного пайплайна."""
        logger.info("Starting TradingView data pipeline")
        
        try:
            async with self.api:
                for market_name, market_config in settings.markets.items():
                    try:
                        market_data = await self.fetch_market_data(
                            market_name, market_config
                        )
                        self.save_market_data(market_data)
                    except Exception as e:
                        logger.error(f"Error processing market {market_name}: {e}")
                        continue
            
            logger.info("Pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise PipelineError(f"Pipeline failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья системы."""
        try:
            async with self.api:
                health_status = await self.api.health_check()
                health_status["pipeline"] = "healthy"
                return health_status
        except Exception as e:
            return {
                "status": "unhealthy",
                "pipeline": f"unhealthy: {e}",
                "timestamp": asyncio.get_event_loop().time()
            }


async def main() -> None:
    """Основная функция для запуска пайплайна."""
    pipeline = Pipeline()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main()) 