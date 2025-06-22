import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml
from jsonschema import validate as json_validate
from jsonschema.exceptions import ValidationError as JsonValidationError
from loguru import logger


class OpenAPIGeneratorError(Exception):
    """Базовый класс для ошибок генератора."""


class ValidationError(OpenAPIGeneratorError):
    """Ошибка валидации данных."""


class FileSystemError(OpenAPIGeneratorError):
    """Ошибка файловой системы."""


class OpenAPIGenerator:
    """Генерирует OpenAPI спецификации для различных рынков."""

    def __init__(self, results_dir: Path = Path("results")):
        self.results_dir = results_dir
        self.specs_dir = Path("specs")

        try:
            self.results_dir.mkdir(exist_ok=True)
            self.specs_dir.mkdir(exist_ok=True)
        except OSError as e:
            raise FileSystemError(f"Failed to create directories: {e}")

        if not os.access(self.results_dir, os.R_OK | os.W_OK):
            raise FileSystemError(
                f"No read/write access to {self.results_dir}"
            )
        if not os.access(self.specs_dir, os.R_OK | os.W_OK):
            raise FileSystemError(
                f"No read/write access to {self.specs_dir}"
            )

    @staticmethod
    def sanitize_field_name(name: str) -> str:
        """
        Очищает имя поля для совместимости с правилами именования
        компонентов OpenAPI 3.1.0.
        """
        # Заменяем все недопустимые символы на подчеркивание
        normalized = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
        # Убираем множественные подчеркивания
        normalized = re.sub(r"_+", "_", normalized)
        # Убираем подчеркивания в начале и конце
        normalized = normalized.strip("_")
        # Если имя пустое, используем fallback
        if not normalized:
            normalized = "field"
        return normalized

    @staticmethod
    def normalize_field_name(name: str) -> str:
        """
        Нормализует имя поля для использования в OpenAPI схемах.
        """
        return OpenAPIGenerator.sanitize_field_name(name)

    def load_user_spec(self, spec_path: Path) -> Dict[str, Any]:
        """Загружает пользовательскую спецификацию."""
        if not spec_path.exists():
            raise FileSystemError(f"User spec file not found: {spec_path}")
        try:
            with open(spec_path, encoding="utf-8") as f:
                user_spec = yaml.safe_load(f)
                if not isinstance(user_spec, dict):
                    raise ValidationError("User spec is not a valid dictionary.")
                return user_spec
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in {spec_path}: {e}")
        except OSError as e:
            raise FileSystemError(f"Failed to read {spec_path}: {e}")

    def get_results_market_name(self, market_name: str) -> str:
        """Маппинг логического имени рынка на имя файла в results/."""
        if not isinstance(market_name, str):
            raise ValidationError("Market name must be a string")

        mapping: Dict[str, str] = {
            "us_stocks": "us_stocks",
            "us_etf": "us_etfs",
            "crypto_cex": "crypto_cex",
            "crypto_dex": "crypto_dex",
            "coin": "crypto_coins",
            "bond": "bonds",
        }
        return mapping.get(market_name, market_name)

    def validate_market_data(self, data: Dict[str, Any]) -> None:
        """Валидация структуры данных рынка."""
        schema = {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "patternProperties": {
                        "^.*$": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "enum": {"type": "array"},
                                "format": {"type": "string"},
                                "example": {},
                            },
                        }
                    },
                },
                "metainfo": {"type": "object"},
            },
        }
        try:
            json_validate(instance=data, schema=schema)
        except JsonValidationError as e:
            raise ValidationError(f"Invalid market data structure: {e}")

    def load_market_data(self, market_name: str) -> Dict[str, Any]:
        """Загружает данные рынка."""
        data: Dict[str, Any] = {}
        results_name = self.get_results_market_name(market_name)

        openapi_path = self.results_dir / f"{results_name}_openapi_fields.json"
        if not openapi_path.exists():
            raise FileSystemError(
                f"OpenAPI fields file not found: {openapi_path}"
            )

        try:
            with open(openapi_path, encoding="utf-8") as f:
                data["fields"] = json.load(f)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {openapi_path}: {e}")
        except OSError as e:
            raise FileSystemError(f"Failed to read {openapi_path}: {e}")

        metainfo_path = self.results_dir / f"{results_name}_metainfo.json"
        if metainfo_path.exists():
            try:
                with open(metainfo_path, encoding="utf-8") as f:
                    data["metainfo"] = json.load(f)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON in {metainfo_path}: {e}")
            except OSError as e:
                raise FileSystemError(f"Failed to read {metainfo_path}: {e}")

        self.validate_market_data(data)
        return data

    def get_market_info(self, market_name: str) -> Dict[str, Any]:
        """Возвращает информацию о рынке."""
        if not isinstance(market_name, str):
            raise ValidationError("Market name must be a string")

        default_info: Dict[str, Any] = {
            "version": "1.0.0",
            "contact": {"name": "API Support", "email": "support@example.com"},
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT",
            },
        }

        market_info_map: Dict[str, Dict[str, Any]] = {
            "us_stocks": {
                "title": "US Stocks API",
                "description": "API for scanning and filtering US stock market data",
                **default_info,
            },
            "us_etf": {
                "title": "US ETFs API",
                "description": "API for scanning and filtering US ETF data",
                **default_info,
            },
            "global_stocks": {
                "title": "Global Stocks API",
                "description": "API for scanning and filtering global stock market data",
                **default_info,
            },
            "crypto_cex": {
                "title": "Centralized Crypto Exchanges API",
                "description": "API for scanning and filtering centralized "
                "cryptocurrency exchange data",
                **default_info,
            },
            "crypto_dex": {
                "title": "Decentralized Crypto Exchanges API",
                "description": "API for scanning and filtering decentralized "
                "cryptocurrency exchange data",
                **default_info,
            },
            "coin": {
                "title": "Cryptocurrency Coins API",
                "description": "API for scanning and filtering cryptocurrency coin data",
                **default_info,
            },
            "bond": {
                "title": "Bonds API",
                "description": "API for scanning and filtering bond market data",
                **default_info,
            },
        }

        info: Dict[str, Any] = market_info_map.get(
            market_name,
            {
                "title": f"{market_name.replace('_', ' ').title()} API",
                "description": f"API for {market_name} market data",
                **default_info,
            },
        )

        return info

    def get_market_endpoint(self, market_name: str) -> str:
        """Возвращает endpoint для рынка."""
        if not isinstance(market_name, str):
            raise ValidationError("Market name must be a string")
        return market_name

    def get_market_label_product(self, market_name: str) -> str:
        """Возвращает label-product для рынка."""
        if not isinstance(market_name, str):
            raise ValidationError("Market name must be a string")

        label_products = {
            "us_stocks": "screener-stock",
            "us_etf": "screener-etf",
            "global_stocks": "screener-stock",
            "crypto_cex": "screener-crypto-cex",
            "crypto_dex": "screener-crypto-dex",
            "coin": "screener-coin",
            "bond": "screener-bond",
        }
        return label_products.get(market_name, "")

    def _map_tradingview_type_to_openapi(
        self, tradingview_type: str
    ) -> str:
        """Маппинг типов TradingView в OpenAPI типы."""
        type_mapping = {
            "number": "number",
            "price": "number",
            "percent": "number",
            "integer": "integer",
            "string": "string",
            "bool": "boolean",
            "boolean": "boolean",
            "time": "string",
            "set": "array",
            "map": "object",
        }
        return type_mapping.get(tradingview_type, "string")

    def create_field_schema(
        self, field_name: str, field: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает схему для поля (имя поля передаётся отдельно)."""
        if not isinstance(field_name, str):
            raise ValidationError("Field name must be a string")
        if not isinstance(field, dict):
            raise ValidationError("Field must be a dictionary")
        if "type" not in field:
            raise ValidationError(
                f"Field {field_name} missing required 'type' property"
            )

        schema: Dict[str, Any] = {
            "type": self._map_tradingview_type_to_openapi(field["type"]),
            "description": field.get("description", f"Field: {field_name}"),
        }

        if field.get("nullable"):
            current_type = schema["type"]
            if isinstance(current_type, str):
                schema["type"] = [current_type, "null"]

        if "enum" in field:
            if not isinstance(field["enum"], list):
                raise ValidationError(f"Field {field_name} enum must be a list")
            schema["enum"] = field["enum"]

        if "format" in field:
            if not isinstance(field["format"], str):
                raise ValidationError(f"Field {field_name} format must be a string")
            schema["format"] = field["format"]

        if "example" in field:
            schema["example"] = field["example"]

        return schema

    def create_properties_schema(
        self, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает схему properties для всех полей (dict-версия)."""
        if not isinstance(fields, dict):
            raise ValidationError("Fields must be a dictionary")

        properties = {}
        for field_name, field in fields.items():
            # Нормализуем имя поля для OpenAPI
            normalized_name = self.normalize_field_name(field_name)
            properties[normalized_name] = self.create_field_schema(
                field_name, field
            )

        return {"type": "object", "properties": properties}

    def generate_openapi_spec(self, market_name: str) -> Dict[str, Any]:
        """Генерирует OpenAPI спецификацию для рынка."""
        if market_name == "crypto_cex":
            try:
                user_spec = self.load_user_spec(
                    Path("user_provided_spec.yaml")
                )

                openapi_spec: Dict[str, Any] = {
                    "openapi": "3.1.0",
                    "info": user_spec.get(
                        "info",
                        {
                            "title": "Numeric Indicator API",
                            "version": "1.0.0",
                            "description": "API for retrieving numeric technical "
                            "indicator values for cryptocurrency tickers.",
                            "contact": {
                                "name": "API Support",
                                "email": "support@example.com",
                            },
                        },
                    ),
                    "servers": user_spec.get("servers", []),
                    "tags": [
                        {
                            "name": "crypto_cex",
                            "description": "Centralized cryptocurrency "
                            "exchange operations",
                        }
                    ],
                    "paths": user_spec.get("paths", {}),
                    "components": user_spec.get("components", {}),
                }

                def copy_examples(src: Any, dst: Any) -> None:
                    if isinstance(src, dict) and isinstance(dst, dict):
                        for k, v in src.items():
                            if k in ("example", "examples"):
                                dst[k] = v
                            elif k in dst:
                                copy_examples(v, dst[k])
                    elif isinstance(src, list) and isinstance(dst, list):
                        if len(src) == len(dst):
                            for s_item, d_item in zip(src, dst):
                                copy_examples(s_item, d_item)

                user_paths = user_spec.get("paths", {})
                openapi_paths = openapi_spec["paths"]
                copy_examples(user_paths, openapi_paths)

                user_components = user_spec.get("components", {})
                openapi_components = openapi_spec["components"]
                copy_examples(user_components, openapi_components)

                def move_examples_to_schema(paths: Dict[str, Any]) -> None:
                    if not isinstance(paths, dict):
                        return
                    for path_item in paths.values():
                        if not isinstance(path_item, dict):
                            continue
                        for method in path_item.values():
                            if not isinstance(method, dict):
                                continue
                            req_body = method.get("requestBody", {})
                            content = req_body.get("content", {})
                            for media in content.values():
                                if not isinstance(media, dict):
                                    continue
                                schema = media.get("schema", {})
                                for ex_key in ("example", "examples"):
                                    if ex_key in media and ex_key not in schema:
                                        schema[ex_key] = media[ex_key]
                                        media["schema"] = schema
                            responses = method.get("responses", {})
                            for resp in responses.values():
                                if not isinstance(resp, dict):
                                    continue
                                content = resp.get("content", {})
                                for media in content.values():
                                    if not isinstance(media, dict):
                                        continue
                                    schema = media.get("schema", {})
                                    for ex_key in ("example", "examples"):
                                        if ex_key in media and ex_key not in schema:
                                            schema[ex_key] = media[ex_key]
                                            media["schema"] = schema

                move_examples_to_schema(openapi_spec["paths"])

                return openapi_spec
            except (FileSystemError, ValidationError) as e:
                logger.error(
                    f"Failed to generate spec for "
                    f"{market_name} from user spec: {e}"
                )
                return {}

        try:
            market_data = self.load_market_data(market_name)
            market_info = self.get_market_info(market_name)
            endpoint = self.get_market_endpoint(market_name)

            if not market_data.get("fields"):
                raise ValidationError(f"No fields found for market: {market_name}")

            field_schemas: Dict[str, Any] = {}
            field_names: List[str] = []
            sanitized_to_original_map: Dict[str, str] = {}

            for field_name, field_info in market_data["fields"].items():
                sanitized_name = self.sanitize_field_name(field_name)
                field_schemas[sanitized_name] = self.create_detailed_field_schema(
                    field_name, field_info
                )
                field_names.append(sanitized_name)
                sanitized_to_original_map[sanitized_name] = field_name

            field_enum = {
                "type": "string",
                "description": f"Available fields for {market_name} market. "
                "Only fields listed in this enum are valid.",
                "enum": field_names,
            }

            example_columns = (
                field_names[:3] if len(field_names) >= 3 else field_names
            )
            example_tickers = self.get_example_tickers(market_name)

            example_request = {
                "symbols": {
                    "tickers": example_tickers[:2],
                    "query": {"types": []},
                },
                "columns": example_columns,
                "filter": [
                    {
                        "left": example_columns[0]
                        if example_columns
                        else "volume",
                        "operation": ">",
                        "right": 0,
                    }
                ],
                "sort": {
                    "sortBy": example_columns[0]
                    if example_columns
                    else "volume",
                    "sortOrder": "desc",
                },
                "range": [0, 10],
            }

            request_schema = {
                "type": "object",
                "required": ["symbols", "columns"],
                "properties": {
                    "symbols": {
                        "type": "object",
                        "required": ["tickers"],
                        "properties": {
                            "tickers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of ticker symbols to scan",
                                "example": example_tickers[:2],
                            },
                            "query": {
                                "type": "object",
                                "properties": {
                                    "types": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Types of symbols to include",
                                    }
                                },
                            },
                        },
                    },
                    "columns": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/FieldEnum"},
                        "description": "Fields to retrieve for each symbol",
                        "example": example_columns,
                    },
                    "filter": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["left", "operation", "right"],
                            "properties": {
                                "left": {"type": "string"},
                                "operation": {"type": "string"},
                                "right": {},
                            },
                        },
                        "description": "Filter conditions",
                    },
                    "sort": {
                        "type": "object",
                        "properties": {
                            "sortBy": {"type": "string"},
                            "sortOrder": {
                                "type": "string",
                                "enum": ["asc", "desc"],
                            },
                        },
                    },
                    "range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "Range of results to return [start, end]",
                    },
                },
            }

            response_data_item_properties: Dict[str, Any] = {
                "s": {
                    "type": "string",
                    "description": "Symbol name",
                }
            }
            for s_name in field_names:
                response_data_item_properties[s_name] = {
                    "$ref": f"#/components/schemas/{s_name}"
                }

            response_schema = {
                "type": "object",
                "properties": {
                    "totalCount": {
                        "type": "integer",
                        "description": "Total number of symbols matching the criteria",
                    },
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": response_data_item_properties,
                        },
                    },
                },
            }

            def get_example_data(
                tickers: List[str],
                columns: List[str],
                data: Dict[str, Any],
                s_map: Dict[str, str],
            ) -> List[Dict[str, Any]]:
                example_data: List[Dict[str, Any]] = []
                for ticker in tickers:
                    item: Dict[str, Any] = {"s": ticker}
                    for col in columns:
                        original_name = s_map.get(col, "")
                        field_info = data.get("fields", {}).get(original_name, {})
                        item[col] = self.get_example_value(field_info)
                    example_data.append(item)
                return example_data

            example_response_data = get_example_data(
                example_tickers[:2],
                example_columns,
                market_data,
                sanitized_to_original_map,
            )

            spec: Dict[str, Any] = {
                "openapi": "3.1.0",
                "info": {
                    "title": market_info["title"],
                    "description": market_info["description"],
                    "version": market_info["version"],
                    "contact": market_info.get("contact", {}),
                    "license": market_info.get("license", {}),
                },
                "servers": [
                    {
                        "url": "https://scanner.tradingview.com",
                        "description": "TradingView Scanner API",
                    }
                ],
                "security": [],
                "tags": [
                    {
                        "name": market_name,
                        "description": f"{market_info['title']} operations",
                    }
                ],
                "paths": {
                    f"/{endpoint}/scan": {
                        "post": {
                            "tags": [market_name],
                            "summary": f"Scan {market_name} market data",
                            "description": f"Retrieve and filter {market_name} "
                            "market data based on specified criteria",
                            "operationId": "scan"
                            f"{market_name.replace('_', '').title()}",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": request_schema,
                                        "example": example_request,
                                    }
                                },
                            },
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                    "content": {
                                        "application/json": {
                                            "schema": response_schema,
                                            "example": {
                                                "totalCount": len(
                                                    example_response_data
                                                ),
                                                "data": example_response_data,
                                            },
                                        }
                                    },
                                },
                                "400": {
                                    "description": "Bad Request - Invalid parameters",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "error": {"type": "string"},
                                                    "details": {"type": "string"},
                                                },
                                            },
                                            "example": {
                                                "error": "Invalid request parameters",
                                                "details": "Missing required field: "
                                                "symbols",
                                            },
                                        }
                                    },
                                },
                                "429": {
                                    "description": "Too Many Requests "
                                    "(rate limit exceeded)",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "error": {"type": "string"},
                                                    "totalCount": {
                                                        "type": "integer"
                                                    },
                                                    "data": {"type": "null"},
                                                },
                                            },
                                            "example": {
                                                "error": "Rate limit exceeded",
                                                "totalCount": 0,
                                                "data": None,
                                            },
                                        }
                                    },
                                },
                            },
                        }
                    }
                },
                "components": {
                    "schemas": {"FieldEnum": field_enum, **field_schemas}
                },
            }

            return spec

        except Exception as e:
            logger.error(f"Failed to generate spec for {market_name}: {e}")
            return {}

    def create_detailed_field_schema(
        self, field_name: str, field_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создает детальную схему для поля с валидацией и описанием."""
        base_type = self._map_tradingview_type_to_openapi(
            field_info.get("type", "string")
        )

        schema_type: Union[str, List[str]]
        if field_info.get("nullable"):
            schema_type = [base_type, "null"]
        else:
            schema_type = base_type

        schema: Dict[str, Any] = {
            "type": schema_type,
            "description": f"Field: {field_name} "
            f"(Type: {field_info.get('type', 'unknown')})",
        }

        if field_info.get("r") and isinstance(field_info["r"], list):
            schema["enum"] = field_info["r"]

        description_parts: List[str] = [schema["description"]]
        if base_type in ["number", "integer"]:
            if field_name.startswith("price") or field_info.get("type") == "price":
                schema["minimum"] = 0
                description_parts.append("Price value (non-negative)")
            elif field_name.startswith("volume") or field_name.startswith("vol"):
                schema["minimum"] = 0
                description_parts.append("Volume value (non-negative)")
            elif (
                field_name.startswith("percent")
                or field_info.get("type") == "percent"
            ):
                schema["minimum"] = -100
                schema["maximum"] = 1000
                description_parts.append("Percentage value")
        schema["description"] = " - ".join(description_parts)

        # Добавляем пример для каждого поля
        schema["example"] = self.get_example_value(field_info)

        return schema

    def get_example_value(self, field_info: Dict[str, Any]) -> Any:
        """Возвращает пример значения для поля."""
        field_type = field_info.get("type", "string")

        if field_type in ["number", "price", "percent"]:
            return 123.45
        if field_type == "integer":
            return 123
        if field_type == "bool":
            return True
        if field_type == "time":
            return "2024-01-01T00:00:00Z"
        if field_type == "set":
            return ["value1", "value2"]
        if field_type == "map":
            return {"key": "value"}
        return "example_value"

    def get_example_tickers(self, market_name: str) -> List[str]:
        """Возвращает примеры тикеров для рынка."""
        ticker_examples = {
            "crypto_cex": ["BINANCE:BTCUSDT.P", "BINANCE:ETHUSDT.P"],
            "crypto_dex": ["UNISWAP:UNIUSDT.P", "SUSHISWAP:SUSHIUSDT.P"],
            "us_stocks": ["NASDAQ:AAPL", "NYSE:MSFT"],
            "us_etf": ["AMEX:SPY", "NASDAQ:QQQ"],
            "forex": ["FX:EURUSD", "FX:GBPUSD"],
            "cfd": ["FX:EURUSD", "FX:GBPUSD"],
            "futures": ["CME:ES1!", "CME:NQ1!"],
            "bond": ["US10Y", "US30Y"],
            "coin": ["BTCUSD", "ETHUSD"],
            "global_stocks": ["LSE:VOD", "TSE:7203"],
        }

        return ticker_examples.get(market_name, ["EXAMPLE:TICKER"])

    def save_spec(self, market_name: str, spec: Dict[str, Any]) -> None:
        """Сохраняет спецификацию в файл."""
        try:
            output_path = self.specs_dir / f"{market_name}_openapi.json"
            logger.info(f"Saving OpenAPI spec for {market_name} to {output_path}")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Successfully saved OpenAPI spec for {market_name} at {output_path}")

        except OSError as e:
            logger.error(f"❌ Failed to save spec for {market_name}: {e}")
            raise FileSystemError(f"Failed to save spec for {market_name}: {e}")

    def generate_all_specs(self) -> None:
        """
        Генерирует все спецификации для всех рынков,
        для которых существуют файлы данных.
        """
        logger.info(f"🔍 Scanning for market data in '{self.results_dir}'...")

        market_files = list(self.results_dir.glob("*_openapi_fields.json"))

        # Этот маппинг нужен, чтобы по имени файла получить логическое имя рынка
        # например, по 'us_stocks_openapi_fields.json' получить 'us_stocks'
        # а по 'crypto_coins_openapi_fields.json' получить 'coin'
        reverse_market_name_map = {
            "us_stocks": "us_stocks",
            "us_etfs": "us_etf",
            "crypto_cex": "crypto_cex",
            "crypto_dex": "crypto_dex",
            "crypto_coins": "coin",
            "bonds": "bond",
            "global_stocks": "global_stocks",
            "cfd": "cfd",
            "forex": "forex",
            "futures": "futures"
        }

        markets_to_generate = []
        for f in market_files:
            # извлекаем 'us_stocks' из 'us_stocks_openapi_fields.json'
            file_market_name = f.name.replace("_openapi_fields.json", "")

            # Находим логическое имя рынка
            logical_name = reverse_market_name_map.get(file_market_name)

            if logical_name:
                markets_to_generate.append(logical_name)
            else:
                # Если в маппинге нет, используем как есть (например, для 'futures')
                markets_to_generate.append(file_market_name)

        if not markets_to_generate:
            logger.warning("⚠️ No market data files found. Nothing to generate.")
            return

        logger.info(f"📊 Found data for markets: {', '.join(markets_to_generate)}")

        successful_generations = 0
        failed_generations = 0

        for market in markets_to_generate:
            logger.info(f"🔄 Generating OpenAPI spec for {market}...")
            try:
                spec = self.generate_openapi_spec(market)
                if spec:
                    self.save_spec(market, spec)
                    successful_generations += 1
                    logger.info(f"✅ Successfully generated spec for {market}")
                else:
                    logger.error(f"❌ Failed to generate spec for {market}: Empty spec returned")
                    failed_generations += 1
            except Exception as e:
                logger.error(f"❌ Failed to generate spec for {market}: {e}")
                failed_generations += 1

        logger.info(f"📈 Generation summary: {successful_generations} successful, {failed_generations} failed")


def main() -> None:
    """Основная функция для запуска генератора."""
    try:
        generator = OpenAPIGenerator()

        logger.info("Starting OpenAPI spec generation...")
        generator.generate_all_specs()

        logger.info("OpenAPI specs generated successfully.")

    except OpenAPIGeneratorError as e:
        logger.error(f"Generator error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()
