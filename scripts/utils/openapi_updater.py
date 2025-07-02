#!/usr/bin/env python3
"""
Enhanced OpenAPI Specification Updater
Автоматическое обновление OpenAPI спецификаций с поддержкой undocumented параметров
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EnhancedOpenAPIUpdater:
    """Система обновления OpenAPI спецификаций с поддержкой undocumented параметров"""

    def __init__(self):
        self.specs_dir = Path("docs/specs")
        self.results_dir = Path("results")
        self.analysis_dir = self.results_dir / "parameter_analysis"
        self.new_specs_dir = self.specs_dir / "v_next"
        self.reports_dir = Path("reports")

        # Создаем директории
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.new_specs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

        # Undocumented параметры для специальной обработки
        self.undocumented_params = [
            "filter2",
            "symbols.query.types",
            "sort.sortBy",
            "sort.sortOrder",
            "options.decimal_places",
            "options.currency",
            "options.timezone",
            "options.session",
            "symbols.query.exchanges",
            "symbols.tickers",
        ]

    def load_parameter_analysis(self) -> dict[str, Any]:
        """Загружает результаты анализа параметров"""
        report_path = self.results_dir / "parameter_discovery_report.json"

        if not report_path.exists():
            logger.error(f"Файл отчета не найден: {report_path}")
            return {}

        with open(report_path, encoding="utf-8") as f:
            return json.load(f)

    def create_enhanced_schema(self, param_name: str, param_info: dict[str, Any]) -> dict[str, Any]:
        """Создает улучшенную схему для параметра с поддержкой x-experimental"""
        schema = {
            "type": self.map_python_type_to_json(param_info.get("data_type", "string")),
            "description": f"Parameter: {param_name}",
            "example": param_info.get("examples", [None])[0] if param_info.get("examples") else None,
        }

        # Добавляем enum если есть варианты значений
        if param_info.get("enum_values"):
            schema["enum"] = param_info["enum_values"]

        # Обработка массивов
        if param_info.get("data_type") == "array":
            schema["type"] = "array"
            schema["items"] = {"type": "string"}  # По умолчанию

        # Обработка объектов
        elif param_info.get("data_type") == "dict":
            schema["type"] = "object"
            schema["additionalProperties"] = True

        # Добавляем пометку для undocumented параметров
        if param_info.get("is_undocumented") or param_name in self.undocumented_params:
            schema["description"] += " (EXPERIMENTAL/UNDOCUMENTED)"
            schema["x-experimental"] = True
            schema["x-undocumented"] = True

        return schema

    def map_python_type_to_json(self, python_type: str) -> str:
        """Преобразует Python тип в JSON Schema тип"""
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "array": "array",
            "object": "object",
        }
        return type_mapping.get(python_type, "string")

    def create_complex_filter_schema(self) -> dict[str, Any]:
        """Создает схему для сложных фильтров"""
        return {
            "type": "object",
            "description": "Complex filter configuration with logical operations",
            "x-experimental": True,
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Logical operation",
                    "enum": ["and", "or", "not", "gt", "lt", "gte", "lte", "eq", "ne", "nz"],
                    "example": "and",
                },
                "left": {
                    "oneOf": [
                        {"type": "string", "description": "Field name or indicator"},
                        {"$ref": "#/components/schemas/ComplexFilter"},
                    ],
                    "description": "Left operand",
                },
                "right": {
                    "oneOf": [
                        {"type": "string", "description": "Field name or indicator"},
                        {"type": "number", "description": "Numeric value"},
                        {"$ref": "#/components/schemas/ComplexFilter"},
                    ],
                    "description": "Right operand",
                },
                "settings": {
                    "type": "object",
                    "description": "Additional filter settings",
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "example": {
                "operation": "and",
                "left": {"operation": "gt", "left": "close", "right": 100},
                "right": {"operation": "lt", "left": "rsi(close, 14)", "right": 70},
            },
        }

    def create_enhanced_request_schema(self, market: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Создает улучшенную схему запроса с undocumented параметрами"""
        properties = {}
        required = []

        # Базовые параметры
        base_params = {
            "filter": {
                "type": "array",
                "description": "Array of filter conditions",
                "items": {
                    "oneOf": [
                        {"type": "object", "description": "Simple filter"},
                        {"$ref": "#/components/schemas/ComplexFilter"},
                    ]
                },
                "example": [],
            },
            "columns": {
                "type": "array",
                "description": "Array of column names to retrieve",
                "items": {"type": "string"},
                "example": ["name", "close", "volume"],
            },
            "range": {
                "type": "array",
                "description": "Range of results [start, end]",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "example": [0, 100],
            },
            "markets": {
                "type": "array",
                "description": "Array of market identifiers",
                "items": {"type": "string"},
                "example": [market],
            },
        }

        properties.update(base_params)
        required.extend(["filter", "columns", "range", "markets"])

        # Добавляем обнаруженные параметры
        for param_name, param_info in parameters.items():
            if param_name not in properties:
                properties[param_name] = self.create_enhanced_schema(param_name, param_info)

        # Специальная обработка для сложных параметров
        if "symbols" in parameters:
            properties["symbols"] = {
                "type": "object",
                "description": "Symbol query configuration",
                "properties": {
                    "query": {
                        "type": "object",
                        "properties": {
                            "types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Symbol types to include",
                                "example": ["stock", "crypto"],
                                "x-experimental": True,
                            },
                            "exchanges": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Exchange identifiers",
                                "example": ["NASDAQ", "NYSE"],
                                "x-experimental": True,
                            },
                        },
                    },
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific ticker symbols",
                        "example": ["NASDAQ:AAPL", "NASDAQ:MSFT"],
                        "x-experimental": True,
                    },
                },
            }

        if "sort" in parameters:
            properties["sort"] = {
                "type": "object",
                "description": "Sorting configuration",
                "x-experimental": True,
                "properties": {
                    "sortBy": {
                        "type": "string",
                        "description": "Field to sort by",
                        "example": "name",
                        "x-experimental": True,
                    },
                    "sortOrder": {
                        "type": "string",
                        "description": "Sort order (asc/desc)",
                        "enum": ["asc", "desc"],
                        "example": "asc",
                        "x-experimental": True,
                    },
                },
            }

        if "options" in parameters:
            properties["options"] = {
                "type": "object",
                "description": "Request options",
                "properties": {
                    "lang": {"type": "string", "description": "Language for response", "example": "en"},
                    "decimal_places": {
                        "type": "integer",
                        "description": "Number of decimal places",
                        "example": 2,
                        "x-experimental": True,
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency for values",
                        "example": "USD",
                        "x-experimental": True,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for dates",
                        "example": "UTC",
                        "x-experimental": True,
                    },
                    "session": {
                        "type": "string",
                        "description": "Trading session",
                        "example": "extended",
                        "x-experimental": True,
                    },
                },
            }

        # Undocumented параметры
        if "filter2" in parameters:
            properties["filter2"] = {
                "type": "object",
                "description": "EXPERIMENTAL: Additional filter configuration",
                "x-experimental": True,
                "x-undocumented": True,
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Logical operation (and/or)",
                        "enum": ["and", "or"],
                        "example": "and",
                    }
                },
            }

        return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}

    def create_components_schemas(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Создает компоненты схем для сложных типов"""
        schemas = {"ComplexFilter": self.create_complex_filter_schema()}

        # Добавляем схемы для undocumented параметров
        for param_name, param_info in parameters.items():
            if param_info.get("is_undocumented") or param_name in self.undocumented_params:
                schema_name = param_name.replace(".", "_").replace("[", "_").replace("]", "_")
                schemas[schema_name] = self.create_enhanced_schema(param_name, param_info)

        return schemas

    def update_specification(self, market: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Обновляет спецификацию для рынка с поддержкой undocumented параметров"""
        # Загружаем существующую спецификацию
        existing_spec = self.load_existing_spec(market)

        if not existing_spec:
            # Создаем новую спецификацию
            spec = self.create_base_specification(market)
        else:
            spec = existing_spec.copy()

        # Обновляем схему запроса
        request_schema = self.create_enhanced_request_schema(market, parameters)

        # Добавляем компоненты схем
        if "components" not in spec:
            spec["components"] = {}
        spec["components"]["schemas"] = self.create_components_schemas(parameters)

        # Находим и обновляем POST операцию
        if "paths" in spec and f"/{market}/scan" in spec["paths"]:
            post_operation = spec["paths"][f"/{market}/scan"]["post"]

            # Обновляем requestBody
            if "requestBody" not in post_operation:
                post_operation["requestBody"] = {}

            post_operation["requestBody"]["content"] = {"application/json": {"schema": request_schema}}

        # Добавляем информацию о версии и обновлении
        spec["info"]["version"] = "2.0.0"
        spec["info"][
            "description"
        ] += f"\n\nEnhanced with automatic parameter discovery and undocumented parameters support. Updated: {datetime.now().isoformat()}"

        # Добавляем теги для undocumented параметров
        if any(param.get("is_undocumented") for param in parameters.values()):
            spec["tags"].append({"name": "experimental", "description": "Experimental and undocumented parameters"})
            spec["tags"].append({"name": "undocumented", "description": "Undocumented API features (use with caution)"})

        return spec

    def load_existing_spec(self, market: str) -> dict[str, Any]:
        """Загружает существующую спецификацию"""
        spec_path = self.specs_dir / f"{market}_openapi.json"

        if not spec_path.exists():
            logger.warning(f"Спецификация не найдена: {spec_path}")
            return {}

        with open(spec_path, encoding="utf-8") as f:
            return json.load(f)

    def create_base_specification(self, market: str) -> dict[str, Any]:
        """Создает базовую спецификацию для рынка"""
        market_names = {
            "america": "US Markets",
            "crypto": "Cryptocurrency",
            "forex": "Forex",
            "futures": "Futures",
            "cfd": "CFD",
            "bond": "Bonds",
            "coin": "Coins",
            "global": "Global Markets",
        }

        return {
            "openapi": "3.1.0",
            "info": {
                "title": f"{market_names.get(market, market.title())} API",
                "description": f"Enhanced API for {market_names.get(market, market)} market data with undocumented parameters support",
                "version": "2.0.0",
                "contact": {"name": "API Support", "email": "support@example.com"},
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            },
            "servers": [{"url": "https://scanner.tradingview.com", "description": "TradingView Scanner API"}],
            "security": [],
            "tags": [
                {"name": market, "description": f"{market_names.get(market, market.title())} API operations"},
                {"name": "experimental", "description": "Experimental and undocumented parameters"},
                {"name": "undocumented", "description": "Undocumented API features (use with caution)"},
            ],
            "paths": {
                f"/{market}/scan": {
                    "post": {
                        "tags": [market],
                        "summary": f"Scan {market} market data",
                        "description": f"Retrieve and filter {market} market data with enhanced parameter support including undocumented features",
                        "operationId": f"scan{market.title()}",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object", "properties": {}, "required": []}}
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "data": {"type": "array", "items": {"type": "object"}},
                                                "totalCount": {"type": "integer"},
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

    def save_updated_specification(self, market: str, spec: dict[str, Any]):
        """Сохраняет обновленную спецификацию"""
        # Сохраняем в новую версию
        new_spec_path = self.new_specs_dir / f"{market}_openapi_v2.json"

        with open(new_spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Обновленная спецификация сохранена: {new_spec_path}")

        # Также обновляем основную спецификацию
        main_spec_path = self.specs_dir / f"{market}_openapi.json"

        with open(main_spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Основная спецификация обновлена: {main_spec_path}")

    def update_all_specifications(self):
        """Обновляет все спецификации"""
        logger.info("Начинаю обновление OpenAPI спецификаций")

        # Загружаем анализ параметров
        analysis = self.load_parameter_analysis()

        if not analysis:
            logger.error("Не удалось загрузить анализ параметров")
            return

        updated_markets = []
        total_parameters = 0
        undocumented_parameters = 0

        # Обновляем спецификации для каждого рынка
        for market, market_data in analysis.get("markets", {}).items():
            logger.info(f"🔄 Обновляю спецификацию для рынка: {market}")

            # Загружаем параметры для рынка
            market_analysis_path = self.analysis_dir / f"{market}_parameter_analysis.json"

            if market_analysis_path.exists():
                with open(market_analysis_path, encoding="utf-8") as f:
                    market_analysis = json.load(f)

                parameters = market_analysis.get("parameters", {})

                # Обновляем спецификацию
                updated_spec = self.update_specification(market, parameters)
                self.save_updated_specification(market, updated_spec)

                updated_markets.append(market)
                total_parameters += len(parameters)
                undocumented_parameters += market_data.get("undocumented_parameters", 0)

                logger.info(
                    f"✅ {market}: {len(parameters)} параметров, {market_data.get('undocumented_parameters', 0)} undocumented"
                )

        # Генерируем отчет
        self.generate_update_report(updated_markets, total_parameters, undocumented_parameters)

        logger.info("Обновление спецификаций завершено!")
        logger.info(f"📊 Обновлено рынков: {len(updated_markets)}")
        logger.info(f"📊 Всего параметров: {total_parameters}")
        logger.info(f"🔍 Undocumented параметров: {undocumented_parameters}")

    def generate_update_report(self, updated_markets: list[str], total_parameters: int, undocumented_parameters: int):
        """Генерирует отчет об обновлении"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "updated_markets": len(updated_markets),
                "total_parameters": total_parameters,
                "undocumented_parameters": undocumented_parameters,
            },
            "updated_markets": updated_markets,
            "changes": {
                "enhanced_request_schemas": True,
                "added_undocumented_parameters": undocumented_parameters > 0,
                "improved_documentation": True,
                "experimental_tags": undocumented_parameters > 0,
                "x-experimental_extensions": undocumented_parameters > 0,
            },
        }

        report_path = self.reports_dir / "openapi_update_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 Отчет об обновлении сохранен: {report_path}")
        return report


def main():
    """Основная функция"""
    updater = EnhancedOpenAPIUpdater()
    updater.update_all_specifications()


if __name__ == "__main__":
    main()
