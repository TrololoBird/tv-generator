print("[DEBUG] src/tv_generator/core.py loaded")

"""
Main logic for processing TradingView API data.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .api import TradingViewAPI
from .types import MarketData, OpenAPIGeneratorResult

# Data versions and sources
DATA_VERSION = "2.0.0"
METAINFO_SOURCE = "tv-screener"
TV_SCREENER_VERSION = "0.4.0"
GENERATOR_VERSION = "2.0.0"
DATA_SOURCE = "tv-screener"
GENERATION_DATE = datetime.now().isoformat()


class OpenAPIGeneratorError(Exception):
    """Base class for OpenAPI generator errors."""


class ValidationError(OpenAPIGeneratorError):
    """Validation error."""


class FileSystemError(OpenAPIGeneratorError):
    """File system error."""


def handle_errors(func):
    """Декоратор для централизованной обработки ошибок."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OpenAPIGeneratorError as e:
            logger.error(f"OpenAPI Generator error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise OpenAPIGeneratorError(f"Unexpected error in {func.__name__}: {e}") from e

    return wrapper


def handle_async_errors(func):
    """Декоратор для централизованной обработки асинхронных ошибок."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except OpenAPIGeneratorError as e:
            logger.error(f"OpenAPI Generator error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise OpenAPIGeneratorError(f"Unexpected error in {func.__name__}: {e}") from e

    return wrapper


class OpenAPIPipeline:
    """
    Single pipeline for generating OpenAPI specifications.

    Combines functionality for loading data, type conversion,
    generating schemas and exporting specifications in a single class.
    """

    def __init__(
        self,
        data_dir: Path = Path("data"),
        specs_dir: Path = Path("docs/specs"),
        results_dir: Path | None = None,
        api_client: TradingViewAPI | None = None,
        setup_logging: bool = True,
        skip_enum_validation: bool = False,
        no_examples: bool = False,
        tag_format: str = "default",
        include_metadata: bool = True,
        inline_body: bool = False,
        include_examples: bool = False,
        require_examples: bool = False,
        debug_trace: bool = False,
    ):
        """
        Initialize the OpenAPI pipeline.

        Args:
            data_dir: Directory containing market data
            specs_dir: Directory to save OpenAPI specifications
            results_dir: Directory to save results (optional)
            api_client: TradingView API client instance
            setup_logging: Whether to setup logging
            skip_enum_validation: Skip enum validation for unsafe mode
            no_examples: Skip adding example values to schemas
            tag_format: Format for tag names ("default" or "technical")
            include_metadata: Include OpenAPI metadata (tags, operationId, etc.)
            inline_body: Use inline body schemas instead of $ref references
            include_examples: Include examples in generated OpenAPI specifications
            require_examples: Require example coverage to be at least 80%
            debug_trace: Enable debug trace for logging
        """
        # Initialize caches early to avoid AttributeError
        self._markets_cache: list[str] | None = None
        self._display_names_cache: dict[str, str] | None = None

        self.data_dir = Path(data_dir)
        self.specs_dir = Path(specs_dir)
        self.results_dir = Path(results_dir) if results_dir is not None else None
        self.api_client = api_client or TradingViewAPI()
        self.skip_enum_validation = skip_enum_validation
        self.no_examples = no_examples
        self.tag_format = tag_format
        self.include_metadata = include_metadata
        self.inline_body = inline_body
        self.include_examples = include_examples
        self.require_examples = require_examples
        self.debug_trace = debug_trace

        # Initialize file paths before loading data
        self.markets_file = self.data_dir / "markets.json"
        self.display_names_file = self.data_dir / "column_display_names.json"

        if setup_logging:
            self._setup_logging()

        # Load data
        self.markets = self._load_markets()
        self.display_names = self._load_display_names()

        # Create necessary directories
        self.specs_dir.mkdir(exist_ok=True)
        if self.results_dir is not None:
            self.results_dir.mkdir(exist_ok=True)

        # File paths for data
        self.metainfo_dir = self.data_dir / "metainfo"

    def _setup_logging(self) -> None:
        """Configure logging for the pipeline."""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Add file logger
        logger.add(
            "logs/pipeline.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
        )

        # Add console logger
        logger.add(
            sys.stderr,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        )

    def _load_markets(self) -> list[str]:
        """Loads list of markets from file."""
        if self._markets_cache is not None:
            return self._markets_cache

        try:
            with open(self.markets_file, encoding="utf-8") as f:
                data = json.load(f)
            # Handle both array and object formats
            if isinstance(data, list):
                markets = data
            else:
                markets = data.get("countries", []) + data.get("other", [])
            self._markets_cache = [str(market) for market in markets]
            return self._markets_cache
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            self._markets_cache = []
            return []

    def _load_display_names(self) -> dict[str, str]:
        """Load display names from JSON file."""
        try:
            if self.display_names_file.exists():
                with open(self.display_names_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            else:
                logger.warning(f"Display names file not found: {self.display_names_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading display names: {e}")
            return {}

    def _load_metainfo(self, market: str) -> dict:
        metainfo_path = self.metainfo_dir / f"{market}.json"
        if not metainfo_path.exists():
            raise FileSystemError(f"Metainfo file not found: {metainfo_path}")
        with open(metainfo_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"fields": data}
        if isinstance(data, dict) and "fields" in data:
            return data
        raise FileSystemError(f"Unexpected metainfo format in {metainfo_path}: {type(data)}")

    def _map_tradingview_type_to_openapi(self, tv_type: str) -> str:
        """
        Converts TradingView type to OpenAPI type.

        Args:
            tv_type: Field type in TradingView

        Returns:
            Corresponding OpenAPI type
        """
        mapping = {
            "number": "number",
            "price": "number",
            "percent": "number",
            "integer": "integer",
            "string": "string",
            "text": "string",
            "bool": "boolean",
            "boolean": "boolean",
            "time": "string",
            "set": "array",
            "map": "object",
            "num_slice": "number",
            "fundamental_price": "number",
        }
        return mapping.get(tv_type, "string")

    def _generate_field_example(self, field: dict[str, Any]) -> Any:
        """
        Generates example for field based on its type and enum values.

        Args:
            field: Field definition from metadata

        Returns:
            Example value for field
        """
        tv_type = field.get("t", "string")
        enum_values = field.get("r")

        # If there are enum values, use the first one
        if enum_values and isinstance(enum_values, list):
            first_value = enum_values[0]
            if isinstance(first_value, dict) and "id" in first_value:
                return first_value["id"]
            return first_value

        # Generate examples based on type
        if tv_type in ("number", "price", "percent"):
            return 123.45
        if tv_type == "integer":
            return 42
        if tv_type in ("bool", "boolean"):
            return True
        if tv_type == "set":
            return ["A", "B"]
        if tv_type == "map":
            return {"key": "value"}

        return "example"

    def _convert_example_to_examples(self, example: Any, field_name: str = "field") -> dict:
        """Convert single example to GPT Builder compatible examples format."""
        return {"examples": {"default": {"value": example}}}

    def _create_field_schema(
        self,
        field: dict[str, Any],
        market: str | None = None,
        skip_enum_validation: bool = False,
        no_examples: bool = False,
        debug_trace: bool | None = None,
    ) -> dict[str, Any]:
        if debug_trace is None:
            debug_trace = self.debug_trace
        field_name = field.get("n", "unknown")
        tv_type = field.get("t", "string")
        openapi_type = self._map_tradingview_type_to_openapi(tv_type)

        # Initialize schema
        schema = {
            "type": openapi_type,
        }

        # Add description if available
        description = field.get("d")
        if description and isinstance(description, str):
            # Normalize description: trim whitespace, replace newlines with spaces
            normalized_desc = " ".join(description.strip().split())
            if len(normalized_desc) > 500:  # Truncate if too long
                normalized_desc = normalized_desc[:497] + "..."
            schema["description"] = normalized_desc

        # Add example if available and not disabled
        example = field.get("e")
        if example is not None and self._validate_example_type(example, openapi_type):
            schema.update(self._convert_example_to_examples(example, field.get("n", "field")))

        # Handle enum values
        enum_values = field.get("r")
        if enum_values and isinstance(enum_values, list):
            if skip_enum_validation:
                # Unsafe mode: pass through all values as-is
                if enum_values:
                    if isinstance(enum_values[0], dict) and "id" in enum_values[0]:
                        enum_list = [str(item["id"]) for item in enum_values]
                    else:
                        enum_list = [str(item) for item in enum_values]
                    schema["enum"] = enum_list
                    logger.warning(f"[enum/unsafe] {market}:{field_name}: bypassing validation, enum may be malformed")
            else:
                # Safe mode: validate enum values
                if self._validate_enum_values(enum_values, openapi_type):
                    if isinstance(enum_values[0], dict) and "id" in enum_values[0]:
                        enum_list = [str(item["id"]) for item in enum_values]
                    else:
                        enum_list = [str(item) for item in enum_values]
                    schema["enum"] = enum_list
                else:
                    logger.warning(
                        f"[enum/type] {market}:{field_name}: enum values don't match field type {openapi_type}"
                    )

        if debug_trace:
            schema["x-tradingview-id"] = field.get("n", "")
            schema["x-tradingview-type"] = field.get("t", "")

        return schema

    def _validate_example_type(self, example: Any, openapi_type: str) -> bool:
        """
        Validates that example value matches the expected OpenAPI type.

        Args:
            example: Example value to validate
            openapi_type: Expected OpenAPI type

        Returns:
            True if example matches type, False otherwise
        """
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
        return True  # Unknown type, accept any value

    def _validate_enum_values(self, enum_values: list[Any], openapi_type: str) -> bool:
        """
        Validates that all enum values match the expected OpenAPI type.

        Args:
            enum_values: List of enum values to validate
            openapi_type: Expected OpenAPI type

        Returns:
            True if all values match type, False otherwise
        """
        if not enum_values:
            return False

        # Extract actual values from enum objects
        actual_values = []
        for item in enum_values:
            if isinstance(item, dict) and "id" in item:
                actual_values.append(item["id"])
            else:
                actual_values.append(item)

        # Validate each value
        for value in actual_values:
            if not self._validate_example_type(value, openapi_type):
                return False

        return True

    def _extract_fields_from_metainfo(self, metainfo: list[dict[str, Any]]) -> list[str]:
        """Extracts field names from metadata."""
        fields = []
        for field in metainfo:
            if "n" in field:
                fields.append(str(field["n"]))
        return fields

    def _create_openapi_fields_schema(
        self,
        metainfo: list[dict[str, Any]],
        market: str = None,
        skip_enum_validation: bool = None,
        no_examples: bool = None,
    ) -> dict[str, Any]:
        if skip_enum_validation is None:
            skip_enum_validation = self.skip_enum_validation
        if no_examples is None:
            no_examples = self.no_examples
        fields = {}
        for field in metainfo:
            if "n" in field:
                fields[field["n"]] = self._create_field_schema(
                    field, market=market, skip_enum_validation=skip_enum_validation, no_examples=no_examples
                )
        return fields

    def _generate_field_schemas(
        self, metainfo: dict[str, Any], skip_enum_validation: bool, no_examples: bool, market: str | None = None
    ) -> dict[str, Any]:
        """
        Generate field schemas from metainfo dictionary.

        Args:
            metainfo: Dictionary of field descriptions
            skip_enum_validation: Skip enum validation for unsafe mode
            no_examples: Skip adding example values to schemas
            market: Market name for logging purposes

        Returns:
            Dictionary of field schemas
        """
        # Track statistics
        fields_with_description = 0
        fields_with_examples = 0

        fields = {}
        for field_name, field_info in metainfo.items():
            schema = self._create_field_schema(
                field_info, market=market, skip_enum_validation=skip_enum_validation, no_examples=no_examples
            )
            fields[field_name] = schema

            # Track statistics
            if "description" in schema:
                fields_with_description += 1
            if "examples" in schema:
                fields_with_examples += 1

        # Log statistics
        logger.info(f"[spec] {fields_with_description} fields with descriptions")
        logger.info(f"[spec] {fields_with_examples} fields with examples")
        if not no_examples:
            logger.info(f"[spec] Examples enabled - {fields_with_examples}/{len(fields)} fields have examples")

        # Аудит покрытия примерами
        fields_with_examples = [
            name for name, schema in fields.items() if isinstance(schema, dict) and "examples" in schema
        ]
        total_fields = len(fields)
        num_with_examples = len(fields_with_examples)
        fields_without_examples = [name for name in fields if name not in fields_with_examples]
        if market:
            logger.info(f"[coverage] {market}: {num_with_examples}/{total_fields} fields have examples")
            if fields_without_examples:
                logger.info(f"[coverage] {market}: fields without examples: {fields_without_examples}")
            coverage = num_with_examples / total_fields if total_fields else 1.0
            if self.require_examples and coverage < 0.8:
                logger.error(f"[coverage] {market}: example coverage {coverage:.0%} < 80% — spec not saved!")
                raise ValidationError(f"Example coverage {coverage:.0%} < 80% for {market}")

        return fields

    def _generate_filter_schemas(self, metainfo: dict[str, Any], skip_enum_validation: bool) -> dict[str, Any]:
        """
        Generates filter schemas for fields.

        Args:
            metainfo: Dictionary of field descriptions
            skip_enum_validation: Skip enum validation for unsafe mode

        Returns:
            Dictionary of filter schemas
        """
        filter_schemas = {}

        for field_name, field_info in metainfo.items():
            field_type = field_info.get("t", "string")

            if field_type == "number":
                filter_schemas[field_name] = {
                    "type": "object",
                    "properties": {
                        "left": {"type": "number"},
                        "right": {"type": "number"},
                    },
                    "required": ["left", "right"],
                }
            elif field_type == "string" and "r" in field_info and not skip_enum_validation:
                # Enum field
                enum_values = field_info["r"]
                filter_schemas[field_name] = {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "enum": enum_values,
                        }
                    },
                    "required": ["values"],
                }
            else:
                # Default string filter
                filter_schemas[field_name] = {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                }

        return filter_schemas

    def _generate_request_body_schema(self, fields: dict[str, Any], filter_schemas: dict[str, Any]) -> dict[str, Any]:
        """
        Generate the common request body schema.

        Args:
            fields: Field schemas for columns
            filter_schemas: Filter schemas for filters

        Returns:
            Request body schema
        """
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "object",
                            "properties": {
                                "types": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "examples": {"default": {"summary": "Example types", "value": ["stock"]}},
                                }
                            },
                        }
                    },
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "examples": {"default": {"summary": "Example columns", "value": list(fields.keys())[:5]}},
                },
                "filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "description": "Filter object with various criteria",
                        "properties": {
                            "field": {"type": "string", "description": "Field name to filter by"},
                            "value": {"type": "string", "description": "Filter value"},
                            "operator": {
                                "type": "string",
                                "enum": [">", "<", ">=", "<=", "=", "!="],
                                "description": "Comparison operator",
                            },
                        },
                    },
                },
                "range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "examples": {"default": {"summary": "Example range", "value": [0, 100]}},
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "lang": {
                            "type": "string",
                            "examples": {"default": {"summary": "Example language", "value": "en"}},
                        },
                    },
                },
            },
            "required": ["symbols", "columns"],
        }

    def _generate_filter_expression_schema(
        self, metainfo: dict[str, Any], skip_enum_validation: bool
    ) -> dict[str, Any]:
        """
        Generate the common filter expression schema.

        Args:
            metainfo: Dictionary of field descriptions
            skip_enum_validation: Skip enum validation for unsafe mode

        Returns:
            Filter expression schema
        """
        # Collect all possible operations from metainfo
        operations = set()

        for field_info in metainfo.values():
            field_type = field_info.get("t", "string")

            if field_type == "number":
                operations.update(["greater", "less", "equal", "not_equal", "in_range", "not_in_range"])
            elif field_type == "string":
                if "r" in field_info:
                    operations.update(["equal", "not_equal", "in", "not_in"])
                else:
                    operations.update(["equal", "not_equal", "contains", "not_contains"])
            elif field_type == "boolean":
                operations.update(["equal", "not_equal"])

        # Add logical operations
        operations.update(["and", "or", "not"])

        return {
            "type": "object",
            "properties": {
                "left": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": sorted(list(operations)),
                },
                "right": {
                    "type": "string",
                    "description": "Value for comparison (can be string, number, boolean, array, or object)",
                },
            },
            "required": ["left", "operation", "right"],
        }

    def _generate_components_schemas(
        self,
        fields: dict[str, Any],
        filter_schemas: dict[str, Any],
        metainfo: dict[str, Any],
        skip_enum_validation: bool,
    ) -> dict[str, Any]:
        """
        Generate all components schemas.

        Args:
            fields: Field schemas
            filter_schemas: Filter schemas
            metainfo: Dictionary of field descriptions
            skip_enum_validation: Skip enum validation for unsafe mode

        Returns:
            Components schemas dictionary
        """
        schemas = {
            "Field": {
                "type": "object",
                "properties": fields,
            },
            "Filter": {
                "type": "object",
                "description": "Filter object with various criteria",
                "properties": {
                    "field": {"type": "string", "description": "Field name to filter by"},
                    "value": {"type": "string", "description": "Filter value"},
                    "operator": {
                        "type": "string",
                        "enum": [">", "<", ">=", "<=", "=", "!="],
                        "description": "Comparison operator",
                    },
                },
            },
            "RequestBody": self._generate_request_body_schema(fields, filter_schemas),
            "FilterExpression": self._generate_filter_expression_schema(metainfo, skip_enum_validation),
        }

        return schemas

    def generate_openapi_spec(
        self,
        market: str,
        verified_fields: list[str] | None = None,
        skip_enum_validation: bool = None,
        no_examples: bool = None,
        tag_format: str = None,
        include_metadata: bool = None,
        inline_body: bool = None,
        include_examples: bool = None,
        scan_examples: list[dict] | None = None,
        require_examples: bool = False,
        debug_trace: bool = False,
    ) -> dict[str, Any]:
        """
        Generate OpenAPI specification for a market.

        Args:
            market: Market name
            verified_fields: List of verified field names (optional)
            skip_enum_validation: Skip enum validation for unsafe mode
            no_examples: Skip adding example values to schemas
            tag_format: Format for tag names ("default" or "technical")
            include_metadata: Include OpenAPI metadata (tags, operationId, etc.)
            inline_body: Use inline body schemas instead of $ref references
            include_examples: Include examples in generated OpenAPI specifications
            scan_examples: List of scan examples
            require_examples: Require example coverage to be at least 80%
            debug_trace: Enable debug trace for logging

        Returns:
            OpenAPI specification dictionary
        """
        if skip_enum_validation is None:
            skip_enum_validation = self.skip_enum_validation
        if no_examples is None:
            no_examples = self.no_examples
        if tag_format is None:
            tag_format = self.tag_format
        if include_metadata is None:
            include_metadata = self.include_metadata
        if inline_body is None:
            inline_body = self.inline_body
        if include_examples is None:
            include_examples = self.include_examples
        if debug_trace is None:
            debug_trace = self.debug_trace

        # Load metainfo
        metainfo = self._load_metainfo(market)
        if not metainfo:
            raise ValueError(f"No metainfo found for market: {market}")

        # Convert metainfo to dictionary format for easier processing
        metainfo_dict = {}
        for field in metainfo["fields"]:
            if "n" in field:
                metainfo_dict[field["n"]] = field

        # Filter fields if verification is enabled
        if verified_fields:
            metainfo_dict = {k: v for k, v in metainfo_dict.items() if k in verified_fields}
            logger.info(f"[spec] Using {len(metainfo_dict)} verified fields for {market}")

        # Generate schemas
        fields = self._generate_field_schemas(metainfo_dict, skip_enum_validation, no_examples, market)
        filter_schemas = self._generate_filter_schemas(metainfo_dict, skip_enum_validation)

        # Get display name
        display_name = self.display_names.get(market, market.title())

        # Generate OpenAPI metadata
        tag = self._generate_market_tag(market)
        operation_id = self._generate_operation_id(market)
        summary = self._generate_summary(market)
        description = self._generate_description(market)

        # Generate examples
        components_examples = None
        examples_ref = None
        used_tickers = []
        if include_examples and scan_examples:
            example_gen = OpenAPIExampleGenerator(scan_examples)
            components_examples, used_tickers = example_gen.generate_examples()
            if components_examples:
                # Формируем ссылку на примеры для requestBody
                examples_ref = {k: {"$ref": f"#/components/examples/{k}"} for k in components_examples.keys()}
                logger.info(
                    f"[examples] {market}: {len(components_examples)} examples generated, tickers: {used_tickers}"
                )
            else:
                logger.info(f"[examples] {market}: no valid examples found in scan responses")

        # Create request body schema
        if inline_body:
            request_body_schema = self._generate_request_body_schema(fields, filter_schemas)
        else:
            request_body_schema = {"$ref": "#/components/schemas/RequestBody"}

        # Формируем requestBody с примерами, если есть
        request_body = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": request_body_schema,
                }
            },
        }
        if examples_ref:
            request_body["content"]["application/json"]["examples"] = examples_ref

        # Create OpenAPI spec
        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": f"TradingView {display_name} API",
                "description": f"""### Purpose:
This API provides access to real-time {display_name} market data from TradingView Scanner.

### Supported Operations:
- Scan market with filters and technical indicators
- Filter and sort by various criteria (price, volume, indicators)
- Get market metadata and reference information

### Authentication:
- API Key via `Authorization: Bearer <token>`

### Features:
- Time format: ISO 8601, UTC
- All parameters and responses strictly typed per OpenAPI 3.1.0
- Compatible with GPT Builder Custom Actions

### Example Usage:
Get list of tickers with RSI > 70 via POST /scan with appropriate filters.""",
                "version": "1.0.0",
            },
            "servers": [
                {
                    "url": "https://scanner.tradingview.com",
                    "description": "TradingView Scanner API",
                }
            ],
            "security": [{"apiKeyAuth": []}],
            "paths": {
                "/scan": {
                    "post": {
                        "summary": summary or f"Scan {display_name}",
                        "description": description or f"Scan {display_name} market with filters",
                        "requestBody": request_body,
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": fields,
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Bad request"},
                            "500": {"description": "Internal server error"},
                        },
                    }
                }
            },
            "components": {
                "schemas": self._generate_components_schemas(
                    fields, filter_schemas, metainfo_dict, skip_enum_validation
                ),
                "securitySchemes": {
                    "apiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "Authorization",
                        "description": "API key for authentication",
                    }
                },
            },
        }
        if components_examples:
            spec["components"]["examples"] = components_examples

        # Add metadata fields only if they have values
        if tag:
            spec["paths"]["/scan"]["post"]["tags"] = [tag]
        if operation_id:
            spec["paths"]["/scan"]["post"]["operationId"] = operation_id

        # Аудит покрытия примерами
        fields_with_examples = [
            name for name, schema in fields.items() if isinstance(schema, dict) and "examples" in schema
        ]
        total_fields = len(fields)
        num_with_examples = len(fields_with_examples)
        fields_without_examples = [name for name in fields if name not in fields_with_examples]
        logger.info(f"[coverage] {market}: {num_with_examples}/{total_fields} fields have examples")
        if fields_without_examples:
            logger.info(f"[coverage] {market}: fields without examples: {fields_without_examples}")
        coverage = num_with_examples / total_fields if total_fields else 1.0
        if require_examples and coverage < 0.8:
            logger.error(f"[coverage] {market}: example coverage {coverage:.0%} < 80% — spec not saved!")
            raise ValidationError(f"Example coverage {coverage:.0%} < 80% for {market}")

        return spec

    def _generate_market_tag(self, market: str) -> str:
        """Generate market tag for OpenAPI."""
        if self.tag_format == "technical":
            return f"market-{market}"
        return market.title()

    def _generate_operation_id(self, market: str) -> str:
        """Generate operation ID for OpenAPI."""
        return f"scan_{market}"

    def _generate_summary(self, market: str) -> str:
        """Generate summary for OpenAPI."""
        display_name = self.display_names.get(market, market.title())
        return f"Scan {display_name} market"

    def _generate_description(self, market: str) -> str:
        """Generate description for OpenAPI."""
        display_name = self.display_names.get(market, market.title())
        return f"Scan {display_name} market with filters and technical indicators"

    def _replace_examples_recursive(self, obj):
        """Рекурсивно заменяет все example на examples."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == "example":
                    # Заменяем example на examples
                    result["examples"] = self._convert_example_to_examples(value)
                else:
                    result[key] = self._replace_examples_recursive(value)
            return result
        elif isinstance(obj, list):
            return [self._replace_examples_recursive(item) for item in obj]
        return obj

    def save_spec(self, market: str, spec: dict[str, Any]) -> None:
        """
        Saves specification to file.
        """
        # Рекурсивно заменяем все example на examples
        spec = self._replace_examples_recursive(spec)
        # Финальная очистка: удаляем все оставшиеся example (глобальная функция)
        spec = remove_all_examples(spec)
        spec_file = self.specs_dir / f"{market}_openapi.json"
        with open(spec_file, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved spec for {market}: {spec_file}")

    async def run(self) -> OpenAPIGeneratorResult:
        """
        Run the pipeline to generate all specifications.
        """
        results = {}
        errors = []

        for market in self.markets:
            try:
                logger.info(f"Generating spec for {market}")
                spec = self.generate_openapi_spec(market)
                self.save_spec(market, spec)
                results[market] = {"status": "success", "spec": spec}
            except Exception as e:
                logger.error(f"Error generating spec for {market}: {e}")
                errors.append(f"{market}: {str(e)}")
                results[market] = {"status": "error", "error": str(e)}

        return OpenAPIGeneratorResult(
            results=results,
            errors=errors,
            total_markets=len(self.markets),
            successful=len([r for r in results.values() if r["status"] == "success"]),
            failed=len(errors),
        )


def remove_all_examples(obj):
    if isinstance(obj, dict):
        return {key: remove_all_examples(value) for key, value in obj.items() if key != "example"}
    elif isinstance(obj, list):
        return [remove_all_examples(item) for item in obj]
    return obj


# Backward compatibility - old classes are now aliases
OpenAPIGenerator = OpenAPIPipeline
Pipeline = OpenAPIPipeline


async def main() -> None:
    """Main entry point."""
    pipeline = OpenAPIPipeline()
    await pipeline.run()


def generate_all_specifications(
    strict_verification: bool = False,
    min_coverage: float = 0.6,
    force_refresh: bool = False,
    report_path: Path | None = None,
    skip_enum_validation: bool = False,
    no_examples: bool = False,
    tag_format: str = "default",
    include_metadata: bool = True,
    inline_body: bool = False,
    include_examples: bool = False,
    require_examples: bool = False,
    debug_trace: bool = False,
) -> OpenAPIGeneratorResult:
    """
    Generate all OpenAPI specifications.

    Args:
        strict_verification: Enable strict field verification
        min_coverage: Minimum coverage threshold for verification
        force_refresh: Force refresh of verification cache
        report_path: Path for verification report
        skip_enum_validation: Skip enum validation for unsafe mode
        no_examples: Skip adding example values to schemas
        tag_format: Format for tag names ("default" or "technical")
        include_metadata: Include OpenAPI metadata (tags, operationId, etc.)
        inline_body: Use inline body schemas instead of $ref references
        include_examples: Include real scan examples in OpenAPI components.examples
        require_examples: Require example coverage to be at least 80%
        debug_trace: Enable debug trace for logging

    Returns:
        OpenAPIGeneratorResult with results
    """
    pipeline = OpenAPIPipeline(
        skip_enum_validation=skip_enum_validation,
        no_examples=no_examples,
        tag_format=tag_format,
        include_metadata=include_metadata,
        inline_body=inline_body,
        include_examples=include_examples,
        require_examples=require_examples,
        debug_trace=debug_trace,
    )
    return asyncio.run(pipeline.run())


class OpenAPIExampleGenerator:
    """
    Генерирует OpenAPI components.examples на основе реальных scan-ответов.
    """

    def __init__(self, scan_responses: list[dict], max_examples: int = 3):
        self.scan_responses = scan_responses
        self.max_examples = max_examples

    def _clean_example(self, example: dict) -> dict:
        """Удаляет пустые поля из примера."""
        return {k: v for k, v in example.items() if v not in (None, [], {}, "")}

    def generate_examples(self) -> dict:
        """
        Возвращает словарь для components.examples (не более 3 валидных примеров).
        """
        examples = {}
        used_tickers = set()
        count = 0
        for resp in self.scan_responses:
            if not isinstance(resp, dict):
                continue
            value = resp.get("d")
            if not value or not isinstance(value, dict):
                continue
            cleaned = self._clean_example(value)
            ticker = cleaned.get("symbol") or cleaned.get("s") or f"Example{count+1}"
            if ticker in used_tickers:
                continue
            used_tickers.add(ticker)
            summary = ticker
            examples[f"Example{count+1}"] = {
                "summary": summary,
                "value": cleaned,
            }
            count += 1
            if count >= self.max_examples:
                break
        return examples, list(used_tickers)
