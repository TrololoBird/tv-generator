"""
Pipeline implementation for OpenAPI generation.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..api import TradingViewAPI
from ..types import MarketData, OpenAPIGeneratorResult
from .cache import MultiLevelCache
from .file_manager import AsyncFileManager
from .metrics import GenerationMetrics, MetricsCollector
from .schema_generator import SchemaGenerator
from .validator import Validator


class OpenAPIPipeline:
    """Pipeline for generating OpenAPI specifications."""

    def __init__(
        self,
        data_dir: Path = Path("data"),
        specs_dir: Path = Path("docs/specs"),
        results_dir: Path | None = None,
        api_client: TradingViewAPI | None = None,
        cache_dir: Path = Path("cache"),
        setup_logging: bool = True,
        skip_enum_validation: bool = False,
        no_examples: bool = False,
        tag_format: str = "default",
        include_metadata: bool = True,
        inline_body: bool = False,
        include_examples: bool = False,
        require_examples: bool = False,
        debug_trace: bool = False,
        compact: bool = False,
        max_fields: int | None = None,
    ):
        """Initialize the OpenAPI pipeline."""
        self.data_dir = Path(data_dir)
        self.specs_dir = Path(specs_dir)
        self.results_dir = Path(results_dir) if results_dir is not None else None
        self.api_client = api_client or TradingViewAPI()

        # Configuration
        self.skip_enum_validation = skip_enum_validation
        self.no_examples = no_examples
        self.tag_format = tag_format
        self.include_metadata = include_metadata
        self.inline_body = inline_body
        self.include_examples = include_examples
        self.require_examples = require_examples
        self.debug_trace = debug_trace
        self.compact = compact
        self.max_fields = max_fields

        # Initialize components
        self.cache = MultiLevelCache(cache_dir=cache_dir)
        self.file_manager = AsyncFileManager(data_dir=data_dir, specs_dir=specs_dir)
        self.metrics_collector = MetricsCollector()
        self.schema_generator = SchemaGenerator(
            {
                "skip_enum_validation": skip_enum_validation,
                "no_examples": no_examples,
                "debug_trace": debug_trace,
                "include_examples": include_examples,
                "require_examples": require_examples,
            },
            compact=compact,
            max_fields=max_fields,
        )
        self.validator = Validator(strict=False)

        # Data caches
        self._markets_cache: list[str] | None = None
        self._display_names_cache: dict[str, str] | None = None

        if setup_logging:
            self._setup_logging()

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

    async def load_markets(self) -> list[str]:
        """Load list of markets from file."""
        if self._markets_cache is not None:
            return self._markets_cache

        try:
            markets = await self.file_manager.load_markets()
            self._markets_cache = markets
            return markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            self._markets_cache = []
            return []

    async def load_display_names(self) -> dict[str, str]:
        """Load display names from file."""
        if self._display_names_cache is not None:
            return self._display_names_cache

        try:
            display_names = await self.file_manager.load_display_names()
            self._display_names_cache = display_names
            return display_names
        except Exception as e:
            logger.error(f"Failed to load display names: {e}")
            self._display_names_cache = {}
            return {}

    async def load_metainfo(self, market: str) -> dict[str, Any]:
        """Load market metainfo from file."""
        try:
            metainfo = await self.file_manager.load_metainfo(market)
            return metainfo if isinstance(metainfo, dict) else {"fields": metainfo}
        except Exception as e:
            logger.error(f"Failed to load metainfo for {market}: {e}")
            return {}

    async def load_scan_data(self, market: str) -> list[dict[str, Any]]:
        """Load market scan data from file."""
        try:
            scan_data = await self.file_manager.load_scan_data(market)
            return scan_data
        except Exception as e:
            logger.error(f"Failed to load scan data for {market}: {e}")
            return []

    def _generate_market_tag(self, market: str) -> str:
        """Generate market tag for OpenAPI specification."""
        if self.tag_format == "technical":
            return f"market-{market}"
        else:
            # Convert market name to readable format
            tag = market.replace("_", " ").title()
            return f"{tag} Market"

    def _generate_operation_id(self, market: str) -> str:
        """Generate operation ID for OpenAPI specification."""
        return f"get_{market}_data"

    def _generate_summary(self, market: str) -> str:
        """Generate summary for OpenAPI specification."""
        return f"Get {market.replace('_', ' ').title()} market data"

    def _generate_description(self, market: str) -> str:
        """Generate description for OpenAPI specification."""
        return (
            f"Retrieve {market.replace('_', ' ').title()} market data with filtering and field selection capabilities."
        )

    async def generate_openapi_spec(
        self,
        market: str,
        verified_fields: list[str] | None = None,
        scan_examples: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate OpenAPI specification for a market."""
        start_time = datetime.now()

        try:
            # Load data
            metainfo = await self.load_metainfo(market)
            if not metainfo:
                raise ValueError(f"No metainfo found for market: {market}")

            # Generate schemas
            fields_schema = self.schema_generator.generate_field_schemas(metainfo, market)
            filter_schema = self.schema_generator.generate_filter_schema(metainfo)
            filter_expression_schema = self.schema_generator.generate_filter_expression_schema(metainfo)

            # Generate info.description
            security_scheme = None
            if hasattr(self, "security") and self.security:
                security_scheme = self.security
            info_description = self.schema_generator.generate_info_description(
                market, metainfo, security=security_scheme
            )

            # Generate components
            components = self.schema_generator.generate_components_schemas(fields_schema, filter_schema, metainfo)

            # Добавляю production-ready enum-схему для индикаторов/полей (IndicatorFieldName)
            indicator_enum = None
            if "fields" in metainfo and isinstance(metainfo["fields"], list):
                indicator_names = [f["n"] for f in metainfo["fields"] if isinstance(f, dict) and "n" in f]
                if indicator_names:
                    indicator_enum = self.schema_generator.generate_enum_schema(
                        name="IndicatorFieldName",
                        values=indicator_names,
                        description="Технический индикатор или поле, допустимое для данного рынка.",
                        example=indicator_names[0],
                    )
                    components["schemas"]["IndicatorFieldName"] = indicator_enum

            # Добавляю production-ready схему ScanRequest
            scan_request_schema = self.schema_generator.generate_scan_request_schema()
            components["schemas"]["ScanRequest"] = scan_request_schema

            # Добавляю production-ready схемы ScanResponse, IndicatorResponse, ErrorResponse
            scan_response_schema = self.schema_generator.generate_scan_response_schema()
            indicator_response_schema = self.schema_generator.generate_indicator_response_schema()
            error_schema_400 = self.schema_generator.generate_error_schema(400, "Некорректный запрос")
            error_schema_404 = self.schema_generator.generate_error_schema(404, "Данные не найдены")
            error_schema_500 = self.schema_generator.generate_error_schema(500, "Внутренняя ошибка сервера")
            components["schemas"]["ScanResponse"] = scan_response_schema
            components["schemas"]["IndicatorResponse"] = indicator_response_schema
            components["schemas"][
                "ErrorResponse"
            ] = error_schema_400  # Для simplicity, 400/404/500 одинаковая структура

            # Build OpenAPI specification
            spec = {
                "openapi": "3.1.0",
                "info": {
                    "title": f"{market.replace('_', ' ').title()} Market API",
                    "description": info_description,
                    "version": "1.0.0",
                    "contact": {
                        "name": "TradingView API Support",
                        "email": "support@tradingview.com",
                    },
                },
                "servers": [
                    {
                        "url": "https://scanner.tradingview.com",
                        "description": "TradingView Scanner API",
                    }
                ],
                "paths": {
                    "/scan": {
                        "post": {
                            "tags": [f"{market.replace('_', ' ').title()} Market"],
                            "summary": f"Get {market.replace('_', ' ').title()} market data",
                            "description": f"Retrieve {market.replace('_', ' ').title()} market data with filtering and field selection capabilities.",
                            "operationId": f"get_{market}_data",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ScanRequest"},
                                        "examples": {"Default": {"value": scan_request_schema["example"]}},
                                    }
                                },
                            },
                            "responses": {
                                "200": {
                                    "description": "Успешный ответ с результатами сканирования",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/ScanResponse"},
                                            "examples": {"Success": {"value": scan_response_schema["example"]}},
                                        }
                                    },
                                },
                                "400": {
                                    "description": "Некорректный запрос",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                            "examples": {"BadRequest": {"value": error_schema_400["example"]}},
                                        }
                                    },
                                },
                                "404": {
                                    "description": "Данные не найдены",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                            "examples": {"NotFound": {"value": error_schema_404["example"]}},
                                        }
                                    },
                                },
                                "500": {
                                    "description": "Внутренняя ошибка сервера",
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                                            "examples": {"ServerError": {"value": error_schema_500["example"]}},
                                        }
                                    },
                                },
                            },
                        }
                    }
                },
                "components": components,
            }

            # Add metadata if enabled
            if self.include_metadata:
                spec["tags"] = [
                    {
                        "name": self._generate_market_tag(market),
                        "description": f"Operations for {market.replace('_', ' ').title()} market",
                    }
                ]

            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            memory_usage = self.metrics_collector.get_memory_usage()

            metrics = GenerationMetrics(
                market=market,
                fields_processed=len(metainfo.get("fields", {})),
                duration=duration,
                memory_usage=memory_usage,
                api_calls=0,  # No API calls in this implementation
                success=True,
            )

            self.metrics_collector.record_generation(metrics)

            logger.info(f"Generated OpenAPI spec for {market} in {duration:.2f}s")
            return spec

        except Exception as e:
            logger.error(f"Error generating OpenAPI spec for {market}: {e}")

            # Record error metrics
            duration = (datetime.now() - start_time).total_seconds()
            memory_usage = self.metrics_collector.get_memory_usage()

            metrics = GenerationMetrics(
                market=market,
                fields_processed=0,
                duration=duration,
                memory_usage=memory_usage,
                api_calls=0,
                success=False,
                errors=[str(e)],
            )

            self.metrics_collector.record_generation(metrics)
            raise

    async def save_spec(self, market: str, spec: dict[str, Any]) -> None:
        """Save OpenAPI specification to file."""
        try:
            await self.file_manager.save_spec(market, spec)
            logger.info(f"Saved OpenAPI spec for {market}")
        except Exception as e:
            logger.error(f"Failed to save spec for {market}: {e}")
            raise

    async def generate_and_save_spec(self, market: str) -> bool:
        """Generate and save OpenAPI specification for a market."""
        try:
            spec = await self.generate_openapi_spec(market)
            await self.save_spec(market, spec)
            return True
        except Exception as e:
            logger.error(f"Failed to generate and save spec for {market}: {e}")
            return False

    async def generate_all_specs(self) -> OpenAPIGeneratorResult:
        """Generate OpenAPI specifications for all markets."""
        self.metrics_collector.start_generation()

        try:
            markets = await self.load_markets()
            if not markets:
                logger.warning("No markets found")
                return OpenAPIGeneratorResult(
                    success=False,
                    message="No markets found",
                    generated_specs=0,
                    total_markets=0,
                    errors=["No markets found"],
                )

            logger.info(f"Starting generation for {len(markets)} markets")

            # Generate specs sequentially (will be parallelized later)
            successful_generations = 0
            failed_generations = 0
            errors = []

            for market in markets:
                try:
                    success = await self.generate_and_save_spec(market)
                    if success:
                        successful_generations += 1
                    else:
                        failed_generations += 1
                        errors.append(f"Failed to generate spec for {market}")
                except Exception as e:
                    failed_generations += 1
                    errors.append(f"Error generating spec for {market}: {e}")

            # Get metrics summary
            metrics_summary = self.metrics_collector.get_summary()

            result = OpenAPIGeneratorResult(
                success=failed_generations == 0,
                message=f"Generated {successful_generations} specs, {failed_generations} failed",
                generated_specs=successful_generations,
                total_markets=len(markets),
                errors=errors if errors else None,
                metrics=metrics_summary,
            )

            logger.info(f"Generation completed: {result.message}")
            return result

        except Exception as e:
            logger.error(f"Error in generate_all_specs: {e}")
            return OpenAPIGeneratorResult(
                success=False,
                message=f"Generation failed: {e}",
                generated_specs=0,
                total_markets=0,
                errors=[str(e)],
            )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check of the pipeline."""
        try:
            # Check if markets can be loaded
            markets = await self.load_markets()

            # Check if display names can be loaded
            display_names = await self.load_display_names()

            # Check cache
            await self.cache.set("health_check", "ok", ttl=60)
            cache_status = await self.cache.get("health_check") == "ok"

            return {
                "status": "healthy",
                "markets_count": len(markets),
                "display_names_count": len(display_names),
                "cache_status": cache_status,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            await self.cache.clear()
            logger.info("Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
