#!/usr/bin/env python3
"""
Enhanced TradingView OpenAPI Generator
Финальная версия генератора с поддержкой undocumented параметров
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enhanced_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedOpenAPIGenerator:
    """Улучшенный генератор OpenAPI спецификаций"""
    
    def __init__(self):
        self.specs_dir = Path("specs")
        self.results_dir = Path("results")
        self.markets = ["america", "crypto", "forex", "futures", "cfd", "bond", "coin"]
        
        # Undocumented параметры из gap-анализа
        self.undocumented_params = {
            "filter2": {"type": "object", "description": "Alternative filter structure"},
            "sort.sortBy": {"type": "string", "enum": ["name", "close", "volume", "change"]},
            "sort.sortOrder": {"type": "string", "enum": ["asc", "desc"]},
            "options.decimal_places": {"type": "integer", "minimum": 0, "maximum": 8},
            "options.currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]},
            "options.timezone": {"type": "string", "enum": ["UTC", "EST", "PST"]},
            "options.session": {"type": "string", "enum": ["regular", "extended", "premarket"]},
            "symbols.query.exchanges": {"type": "array", "items": {"type": "string"}},
            "symbols.query.types": {"type": "array", "items": {"type": "string"}},
            "symbols.tickers": {"type": "array", "items": {"type": "string"}},
            "filter.operation": {"type": "string", "enum": ["and", "or", "not", "gt", "lt", "eq", "nz"]},
            "filter.left": {"type": "object"},
            "filter.right": {"type": "object"},
            "filter.settings": {"type": "object"}
        }
        
        # Создаем директории
        self.specs_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
    
    def generate_market_specification(self, market: str) -> Dict[str, Any]:
        """Генерирует OpenAPI спецификацию для рынка"""
        logger.info(f"🔧 Генерирую спецификацию для рынка: {market}")
        
        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": f"TradingView Scanner API - {market.upper()}",
                "description": f"OpenAPI specification for TradingView Scanner API {market} market with undocumented parameters",
                "version": "2.0.0",
                "contact": {
                    "name": "TradingView Scanner API",
                    "url": "https://scanner.tradingview.com"
                }
            },
            "servers": [
                {
                    "url": "https://scanner.tradingview.com",
                    "description": "TradingView Scanner API"
                }
            ],
            "paths": {
                f"/{market}/scan": {
                    "post": {
                        "summary": f"Scan {market} market",
                        "description": f"Scan {market} market with filters and options",
                        "operationId": f"scan{market.capitalize()}",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{market.capitalize()}ScanRequest"
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful scan result",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{market.capitalize()}ScanResponse"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                f"/{market}/metainfo": {
                    "get": {
                        "summary": f"Get {market} market metadata",
                        "description": f"Get metadata for {market} market",
                        "operationId": f"get{market.capitalize()}Metainfo",
                        "responses": {
                            "200": {
                                "description": "Market metadata",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{market.capitalize()}Metainfo"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": self._generate_schemas(market)
            }
        }
        
        return spec
    
    def _generate_schemas(self, market: str) -> Dict[str, Any]:
        """Генерирует схемы для рынка"""
        schemas = {}
        
        # Основная схема запроса
        request_schema = {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "array",
                    "items": {
                        "$ref": "#/components/schemas/Filter"
                    },
                    "description": "Array of filters to apply"
                },
                "options": {
                    "$ref": "#/components/schemas/Options"
                },
                "markets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Markets to scan"
                },
                "symbols": {
                    "$ref": "#/components/schemas/Symbols"
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Columns to return"
                },
                "range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Range of results [start, end]"
                }
            },
            "required": ["markets", "columns", "range"]
        }
        
        # Добавляем undocumented параметры
        for param_name, param_schema in self.undocumented_params.items():
            request_schema["properties"][param_name] = {
                **param_schema,
                "x-experimental": True,
                "x-undocumented": True
            }
        
        schemas[f"{market.capitalize()}ScanRequest"] = request_schema
        
        # Схема ответа
        schemas[f"{market.capitalize()}ScanResponse"] = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True
                    }
                },
                "totalCount": {
                    "type": "integer"
                }
            }
        }
        
        # Схема метаинформации
        schemas[f"{market.capitalize()}Metainfo"] = {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        # Общие схемы
        schemas["Filter"] = {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["and", "or", "not", "gt", "lt", "eq", "nz"],
                    "x-experimental": True
                },
                "left": {
                    "type": "object",
                    "x-experimental": True
                },
                "right": {
                    "type": "object",
                    "x-experimental": True
                },
                "settings": {
                    "type": "object",
                    "x-experimental": True
                }
            }
        }
        
        schemas["Options"] = {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "enum": ["en", "ru", "zh"]
                },
                "decimal_places": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 8,
                    "x-experimental": True
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP"],
                    "x-experimental": True
                },
                "timezone": {
                    "type": "string",
                    "enum": ["UTC", "EST", "PST"],
                    "x-experimental": True
                },
                "session": {
                    "type": "string",
                    "enum": ["regular", "extended", "premarket"],
                    "x-experimental": True
                }
            }
        }
        
        schemas["Symbols"] = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "x-experimental": True
                        },
                        "exchanges": {
                            "type": "array",
                            "items": {"type": "string"},
                            "x-experimental": True
                        }
                    }
                },
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "x-experimental": True
                }
            }
        }
        
        return schemas
    
    def generate_all_specifications(self):
        """Генерирует все спецификации"""
        logger.info("🚀 Начинаю генерацию всех спецификаций")
        
        generated_specs = {}
        
        for market in self.markets:
            try:
                spec = self.generate_market_specification(market)
                generated_specs[market] = spec
                
                # Сохраняем спецификацию
                spec_file = self.specs_dir / f"{market}_openapi.json"
                with open(spec_file, 'w', encoding='utf-8') as f:
                    json.dump(spec, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Спецификация сохранена: {spec_file}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при генерации {market}: {e}")
        
        # Сохраняем отчет
        self._save_generation_report(generated_specs)
        
        return generated_specs
    
    def _save_generation_report(self, generated_specs: Dict[str, Any]):
        """Сохраняет отчет о генерации"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "generator_version": "2.0.0",
            "total_markets": len(generated_specs),
            "markets": list(generated_specs.keys()),
            "undocumented_parameters": len(self.undocumented_params),
            "experimental_features": True,
            "openapi_version": "3.1.0"
        }
        
        report_file = self.results_dir / "generation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Отчет сохранен: {report_file}")

def main():
    """Основная функция"""
    logger.info("🚀 Запуск Enhanced TradingView OpenAPI Generator")
    
    generator = EnhancedOpenAPIGenerator()
    specs = generator.generate_all_specifications()
    
    logger.info("✅ Генерация завершена!")
    logger.info(f"📊 Сгенерировано спецификаций: {len(specs)}")
    logger.info(f"🔍 Undocumented параметров: {len(generator.undocumented_params)}")

if __name__ == "__main__":
    main()
