"""
Schema generator for OpenAPI specifications.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .base import BaseSchemaGenerator
from .example_utils import extract_enum_values, generate_field_example
from .models import TVField, TVFilter
from .utils import log_and_catch


class SchemaGenerator(BaseSchemaGenerator):
    """
    Schema generator for OpenAPI specifications.

    Основная задача: преобразовать TradingView metainfo/filters в корректные OpenAPI-схемы.
    Использует pydantic-модели для валидации и автогенерации схем.
    Все ошибки обрабатываются централизованно через декоратор log_and_catch.
    """

    def __init__(self, config: dict[str, Any] | None = None, compact: bool = False, max_fields: int | None = None):
        self.config = config or {}
        self.skip_enum_validation = self.config.get("skip_enum_validation", False)
        self.no_examples = self.config.get("no_examples", False)
        self.debug_trace = self.config.get("debug_trace", False)
        self.include_examples = self.config.get("include_examples", False)
        self.require_examples = self.config.get("require_examples", False)
        self.compact = compact
        self.max_fields = max_fields

    def _map_tradingview_type_to_openapi(self, tv_type: str) -> str:
        """Map TradingView field type to OpenAPI type."""
        type_mapping = {
            "number": "number",
            "price": "number",
            "percent": "number",
            "integer": "integer",
            "string": "string",
            "text": "string",
            "boolean": "boolean",
            "time": "string",
            "set": "array",
            "map": "object",
        }
        return type_mapping.get(tv_type, "string")

    def _validate_example_type(self, example: Any, openapi_type: str) -> bool:
        """Validate that example matches OpenAPI type."""
        try:
            if openapi_type == "string":
                return isinstance(example, str)
            elif openapi_type == "number":
                return isinstance(example, (int, float)) and not isinstance(example, bool)
            elif openapi_type == "integer":
                return isinstance(example, int) and not isinstance(example, bool)
            elif openapi_type == "boolean":
                return isinstance(example, bool)
            elif openapi_type == "array":
                return isinstance(example, list)
            elif openapi_type == "object":
                return isinstance(example, dict)
            else:
                return True
        except Exception:
            return False

    def _validate_enum_values(self, enum_values: list[Any], openapi_type: str) -> bool:
        """Validate enum values against OpenAPI type."""
        if not enum_values:
            return False

        for value in enum_values:
            if not self._validate_example_type(value, openapi_type):
                logger.warning(f"Invalid enum value {value} for type {openapi_type}")
                return False
        return True

    def _convert_example_to_examples(self, example: Any, field_name: str = "field") -> dict[str, Any]:
        """Convert single example to GPT Builder compatible examples format."""
        if self.no_examples:
            return {}

        return {"examples": {"default": {"summary": f"Example {field_name}", "value": example}}}

    @log_and_catch(default={"type": "string", "description": "Error generating schema"})
    def generate_field_schema(self, field: dict[str, Any], market: str | None = None) -> dict[str, Any]:
        """
        Генерирует OpenAPI-схему для одного поля TradingView.
        Использует pydantic-модель TVField для валидации структуры.
        Возвращает dict, пригодный для включения в OpenAPI components.schemas.
        В случае ошибки возвращает дефолтную строковую схему с описанием ошибки.
        """
        try:
            tv_field = TVField(**field)
            schema = tv_field.schema()
            schema["title"] = tv_field.n
            if not self.compact:
                schema["description"] = f"Field: {tv_field.n}"

            # Обрезаем длинные enum
            if "enum" in schema and isinstance(schema["enum"], list) and len(schema["enum"]) > 3:
                schema["enum"] = schema["enum"][:3]

            # Конвертируем example в examples для GPT Builder
            if "example" in schema and not self.compact:
                example_value = schema.pop("example")
                examples_data = self._convert_example_to_examples(example_value, tv_field.n)
                schema.update(examples_data)

            return schema
        except Exception as e:
            logger.error(f"Error generating schema for field {field.get('n', '?')}: {e}")
            return {"type": "string", "description": f"Error: {e}"}

    @log_and_catch(default={"type": "object", "description": "Error generating filter schema", "properties": {}})
    def generate_filter_schema(self, metainfo: dict[str, Any]) -> dict[str, Any]:
        """
        Генерирует OpenAPI-схему для фильтров TradingView.
        Использует pydantic-модель TVFilter для каждого фильтра.
        Возвращает dict, пригодный для включения в OpenAPI components.schemas.
        В случае ошибки возвращает дефолтную object-схему с описанием ошибки.
        """
        filters = metainfo.get("filters", {})
        if not filters:
            return {
                "type": "object",
                "title": "Filters",
                "description": "No filters available for this market",
                "properties": {},
            }
        properties = {}
        required = []
        for filter_name, filter_data in filters.items():
            try:
                tv_filter = TVFilter(**filter_data)
                property_schema = tv_filter.schema()
                property_schema["title"] = tv_filter.n
                property_schema["description"] = f"Filter: {tv_filter.n}"

                # Конвертируем example в examples для GPT Builder
                if "example" in property_schema:
                    example_value = property_schema.pop("example")
                    examples_data = self._convert_example_to_examples(example_value, tv_filter.n)
                    property_schema.update(examples_data)

                if tv_filter.required:
                    required.append(filter_name)
                properties[filter_name] = property_schema
            except Exception as e:
                logger.error(f"Error generating schema for filter {filter_name}: {e}")
        schema = {
            "type": "object",
            "title": "Filters",
            "description": "Market filters",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    @log_and_catch(default={"type": "object", "description": "Error generating request body schema", "properties": {}})
    def generate_request_body_schema(self, fields: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
        """
        Генерирует OpenAPI-схему для requestBody (объединяет поля и фильтры).
        Возвращает dict, пригодный для включения в OpenAPI components.schemas.
        В случае ошибки возвращает дефолтную object-схему с описанием ошибки.
        """
        try:
            properties = {}
            required = []

            # Add fields
            if "properties" in fields:
                properties.update(fields["properties"])
                required.extend(fields.get("required", []))

            # Add filters
            if "properties" in filters:
                properties.update(filters["properties"])
                required.extend(filters.get("required", []))

            schema = {
                "type": "object",
                "title": "Request Body",
                "description": "Request body containing fields and filters",
                "properties": properties,
            }

            if required:
                schema["required"] = required

            # Add examples if enabled
            if not self.no_examples and self.include_examples:
                example = {}
                for prop_name, prop_schema in properties.items():
                    if "examples" in prop_schema and "default" in prop_schema["examples"]:
                        example[prop_name] = prop_schema["examples"]["default"]["value"]
                    elif "enum" in prop_schema and prop_schema["enum"]:
                        example[prop_name] = prop_schema["enum"][0]
                    else:
                        # Generate basic example based on type
                        prop_type = prop_schema.get("type", "string")
                        if prop_type == "number":
                            example[prop_name] = 123.45
                        elif prop_type == "integer":
                            example[prop_name] = 123
                        elif prop_type == "boolean":
                            example[prop_name] = True
                        elif prop_type == "array":
                            example[prop_name] = ["item1", "item2"]
                        elif prop_type == "object":
                            example[prop_name] = {"key": "value"}
                        else:
                            example[prop_name] = "example_value"

                if example:
                    schema.update(self._convert_example_to_examples(example, "request"))

            return schema
        except Exception as e:
            logger.error(f"Error generating request body schema: {e}")
            return {
                "type": "object",
                "title": "Request Body",
                "description": f"Error generating request body schema: {e}",
                "properties": {},
            }

    def generate_components_schemas(
        self,
        fields: dict[str, Any],
        filter_schemas: dict[str, Any],
        metainfo: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate OpenAPI components schemas."""
        try:
            components = {
                "schemas": {
                    "Fields": fields,
                    "Filters": filter_schemas,
                    "RequestBody": self.generate_request_body_schema(fields, filter_schemas),
                }
            }

            # Add response schemas if available
            if "responses" in metainfo:
                components["schemas"]["Response"] = {
                    "type": "object",
                    "title": "Response",
                    "description": "Market data response",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Fields"},
                            "description": "Array of market data items",
                        },
                        "totalCount": {
                            "type": "integer",
                            "description": "Total number of items",
                        },
                    },
                }

            return components

        except Exception as e:
            logger.error(f"Error generating components schemas: {e}")
            return {
                "schemas": {
                    "Fields": fields,
                    "Filters": filter_schemas,
                    "RequestBody": self.generate_request_body_schema(fields, filter_schemas),
                }
            }

    def generate_field_schemas(self, metainfo: dict[str, Any], market: str | None = None) -> dict[str, Any]:
        """Generate field schemas from metainfo."""
        try:
            # Отладочная информация
            logger.debug(f"[schema_generator] generate_field_schemas called with type: {type(metainfo)}")
            logger.debug(
                f"[schema_generator] metainfo keys: {list(metainfo.keys()) if isinstance(metainfo, dict) else 'not dict'}"
            )

            fields = metainfo.get("fields", {})
            if not fields:
                return {
                    "type": "object",
                    "title": "Fields",
                    "description": "No fields available for this market",
                    "properties": {},
                }
            # Исправление: если fields — список, преобразуем в dict
            if isinstance(fields, list):
                fields = {f["n"]: f for f in fields if isinstance(f, dict) and "n" in f}
            properties = {}
            required = []
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict):
                    field_schema = self.generate_field_schema(field_data, market)
                    properties[field_name] = field_schema
                    # Add to required if field is mandatory
                    if field_data.get("required", False):
                        required.append(field_name)
            schema = {
                "type": "object",
                "title": "Fields",
                "description": "Market fields",
                "properties": properties,
            }
            if required:
                schema["required"] = required
            return schema
        except Exception as e:
            logger.error(f"Error generating field schemas: {e}")
            return {
                "type": "object",
                "title": "Fields",
                "description": f"Error generating field schemas: {e}",
                "properties": {},
            }

    def generate_filter_expression_schema(self, metainfo: dict[str, Any]) -> dict[str, Any]:
        """Generate filter expression schema."""
        try:
            schema = {
                "type": "string",
                "title": "Filter Expression",
                "description": "Filter expression string",
            }

            if not self.no_examples:
                schema.update(
                    self._convert_example_to_examples("close > 100 and volume > 1000000", "filter_expression")
                )

            return schema
        except Exception as e:
            logger.error(f"Error generating filter expression schema: {e}")
            return {
                "type": "string",
                "title": "Filter Expression",
                "description": f"Error generating filter expression schema: {e}",
            }

    def generate_info_description(self, market: str, metainfo: dict, security: str | None = None) -> str:
        """
        Формирует production-ready info.description по шаблону для GPT Builder:
        - Назначение и сфера применения API
        - Краткое описание групп методов
        - Общие требования к авторизации
        - Особенности (лимиты, форматы, edge-cases)
        - Примеры сценариев использования
        """
        lines = []
        # Назначение
        lines.append(
            f"### Purpose:\nThis API provides access to real-time {market.title()} market data from TradingView Scanner."
        )
        # Группы методов
        lines.append("\n### Supported Operations:")
        lines.append("- Scan market with filters and technical indicators")
        lines.append("- Filter and sort by various criteria (price, volume, indicators)")
        lines.append("- Get market metadata and reference information")
        # Авторизация
        if security:
            lines.append(f"\n### Authentication:\n- API Key via `Authorization: Bearer <token>`")
        else:
            lines.append("\n### Authentication:\n- API Key via `Authorization: Bearer <token>`")
        # Особенности
        lines.append("\n### Features:")
        if "limits" in metainfo:
            lines.append(f"- Rate limits: {metainfo['limits']}")
        lines.append("- Time format: ISO 8601, UTC")
        lines.append("- All parameters and responses strictly typed per OpenAPI 3.1.0")
        lines.append("- Compatible with GPT Builder Custom Actions")
        # Пример сценария
        lines.append("\n### Example Usage:\nGet list of tickers with RSI > 70 via POST /scan with appropriate filters.")
        return "\n".join(lines)

    def generate_enum_schema(
        self, name: str, values: list, description: str | None = None, example: str | None = None
    ) -> dict:
        """
        Генерирует production-ready enum-схему для components.schemas:
        - name: имя схемы
        - values: список допустимых значений
        - description: подробное пояснение (что означает каждое значение)
        - example: типовое значение
        """
        schema = {
            "type": "string",
            "enum": values,
            "description": description or f"Possible values for {name}",
        }

        if not self.no_examples:
            example_value = example or (values[0] if values else "example_value")
            schema.update(self._convert_example_to_examples(example_value, name))

        return schema

    def generate_scan_request_schema(self, indicator_enum_ref: str = "#/components/schemas/IndicatorFieldName") -> dict:
        """
        Генерирует production-ready схему тела запроса для /scan:
        - symbols: объект с массивом тикеров
        - columns: массив индикаторов (enum)
        - filter, sort, range, markets — опционально
        - Примеры, ограничения, описания
        """
        schema = {
            "type": "object",
            "description": "Scan request with tickers, indicators, and optional filters",
            "required": ["symbols", "columns"],
            "properties": {
                "symbols": {
                    "type": "object",
                    "required": ["tickers"],
                    "properties": {
                        "tickers": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "pattern": "^[A-Z0-9:._-]+$",
                                "description": "Ticker (например, MOEX:GAZP, BINANCE:BTCUSDT.P)",
                            },
                            "description": "Массив тикеров в формате MARKET:TICKER (например, MOEX:GAZP)",
                            "minItems": 1,
                            "maxItems": 25,
                        }
                    },
                },
                "columns": {
                    "type": "array",
                    "description": "Список индикаторов/полей для запроса. Только значения из IndicatorFieldName.",
                    "items": {"$ref": indicator_enum_ref},
                    "minItems": 1,
                    "maxItems": 30,
                },
                "filter": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["left", "operation", "right"],
                        "properties": {
                            "left": {"type": "string", "description": "Имя индикатора/поля для фильтрации"},
                            "operation": {
                                "type": "string",
                                "enum": [">", "<", ">=", "<=", "=", "!="],
                                "description": "Оператор сравнения",
                            },
                            "right": {"type": "number", "description": "Значение для сравнения"},
                        },
                    },
                    "description": "Массив условий фильтрации (например, RSI > 70)",
                },
                "sort": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "description": "Имя индикатора/поля для сортировки"},
                        "order": {"type": "string", "enum": ["asc", "desc"], "description": "Порядок сортировки"},
                    },
                    "description": "Параметры сортировки (например, RSI по убыванию)",
                },
                "range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Пагинация: [start, count]",
                },
                "markets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 1,
                    "description": "Рынок (например, 'russia', 'crypto')",
                },
            },
        }

        if not self.no_examples:
            example = {
                "symbols": {"tickers": ["MOEX:GAZP"]},
                "columns": ["RSI", "EMA20"],
                "filter": [{"left": "RSI", "operation": ">", "right": 70}],
                "sort": {"field": "RSI", "order": "desc"},
                "range": [0, 10],
                "markets": ["russia"],
            }
            schema.update(self._convert_example_to_examples(example, "scan_request"))

        return schema

    def generate_scan_response_schema(self) -> dict:
        """
        Генерирует production-ready схему успешного ответа для /scan (ScanResponse, IndicatorResponse):
        - totalCount: integer
        - data: array of IndicatorResponse
        - Пример ответа
        """
        schema = {
            "type": "object",
            "required": ["totalCount", "data"],
            "properties": {
                "totalCount": {"type": "integer", "description": "Общее количество найденных тикеров"},
                "data": {
                    "type": "array",
                    "description": "Массив результатов по тикерам",
                    "items": {"$ref": "#/components/schemas/IndicatorResponse"},
                },
            },
        }

        if not self.no_examples:
            example = {
                "totalCount": 2,
                "data": [{"s": "MOEX:GAZP", "d": [50.2, 5.0, 22000.5]}, {"s": "MOEX:SBER", "d": [48.1, 4.5, 21000.0]}],
            }
            schema.update(self._convert_example_to_examples(example, "scan_response"))

        return schema

    def generate_indicator_response_schema(self) -> dict:
        """
        Генерирует production-ready схему IndicatorResponse (один тикер и массив значений индикаторов).
        """
        schema = {
            "type": "object",
            "required": ["s", "d"],
            "properties": {
                "s": {"type": "string", "description": "Тикер (например, MOEX:GAZP)"},
                "d": {
                    "type": "array",
                    "description": "Значения индикаторов в том же порядке, что и в columns",
                    "items": {"type": "number"},
                },
            },
        }

        if not self.no_examples:
            example = {"s": "MOEX:GAZP", "d": [50.2, 5.0, 22000.5]}
            schema.update(self._convert_example_to_examples(example, "indicator_response"))

        return schema

    def generate_error_schema(self, code: int = 400, message: str = "Ошибка запроса") -> dict:
        """
        Генерирует production-ready схему ошибки для responses (ErrorResponse).
        """
        schema = {
            "type": "object",
            "required": ["error", "code"],
            "properties": {
                "error": {"type": "string", "description": "Сообщение об ошибке"},
                "code": {"type": "integer", "description": "Код ошибки"},
            },
        }

        if not self.no_examples:
            example = {"error": message, "code": code}
            schema.update(self._convert_example_to_examples(example, "error_response"))

        return schema
