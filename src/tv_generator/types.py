"""
Type definitions for tv-generator using Pydantic models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class FieldType(str, Enum):
    """Типы полей TradingView."""

    NUMBER = "number"
    PRICE = "price"
    PERCENT = "percent"
    INTEGER = "integer"
    STRING = "string"
    TEXT = "text"
    BOOLEAN = "boolean"
    TIME = "time"
    SET = "set"
    MAP = "map"


class FilterOperation(str, Enum):
    """Операции фильтрации."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"


class Language(str, Enum):
    """Языки для результатов."""

    EN = "en"
    RU = "ru"


class Session(str, Enum):
    """Торговые сессии."""

    REGULAR = "regular"
    EXTENDED = "extended"


class SecurityType(str, Enum):
    """Типы безопасности."""

    COOKIE = "cookie"
    API_KEY = "apiKey"


class FieldReference(BaseModel):
    """Ссылка на значение поля."""

    id: str
    title: str | None = None


class FieldDefinition(BaseModel):
    """Определение поля TradingView."""

    n: str = Field(..., description="Field name")
    t: FieldType = Field(..., description="Field type")
    r: list[str | FieldReference] | None = Field(None, description="Field references/enum values")
    s: str | None = Field(None, description="Field source")

    model_config = ConfigDict(use_enum_values=True)


class MarketInfo(BaseModel):
    """Информация о рынке."""

    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    description: str | None = Field(None, description="Market description")


class FilterDefinition(BaseModel):
    """Определение фильтра."""

    left: str = Field(..., description="Field name to filter on")
    operation: FilterOperation = Field(..., description="Filter operation")
    right: str | int | float | bool | list[Any] = Field(..., description="Filter value(s)")

    model_config = ConfigDict(use_enum_values=True)


class Options(BaseModel):
    """Опции запроса."""

    lang: Language = Field(Language.EN, description="Language for results")
    session: Session = Field(Session.REGULAR, description="Trading session")

    model_config = ConfigDict(use_enum_values=True)


class SecurityScheme(BaseModel):
    """Схема безопасности."""

    type: SecurityType = Field(..., description="Security type")
    in_: str = Field(..., alias="in", description="Location of security parameter")
    name: str = Field(..., description="Parameter name")
    description: str | None = Field(None, description="Security description")

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)


class ScanRequest(BaseModel):
    """Запрос сканирования."""

    filter: list[FilterDefinition] | None = Field(None, description="Array of filters to apply")
    options: Options | None = Field(None, description="Request options")
    columns: list[str] | None = Field(None, description="Columns to return")
    range: list[int] | None = Field(None, description="Range of results [start, end]")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "range": [0, 10],
                    "columns": ["name", "price", "change"],
                    "filter": [{"left": "price", "operation": "greater", "right": 100}],
                }
            ]
        }
    )


class MarketData(BaseModel):
    """Данные рынка."""

    name: str = Field(..., description="Market name")
    endpoint: str = Field(..., description="Market endpoint")
    label_product: str = Field(..., description="Market label product")
    description: str = Field(..., description="Market description")
    metainfo: dict[str, Any] = Field(..., description="Market metadata")
    tickers: list[dict[str, Any]] = Field(..., description="Market tickers")
    fields: list[str] = Field(..., description="Available fields")
    working_fields: list[str] = Field(..., description="Working fields")
    openapi_fields: dict[str, Any] = Field(..., description="OpenAPI field definitions")

    model_config = ConfigDict(extra="allow")


class ScanResponse(BaseModel):
    """Ответ сканирования."""

    totalCount: int = Field(..., description="Total number of results")
    data: list[MarketData] = Field(..., description="Market data array")


class OpenAPISpecInfo(BaseModel):
    """Информация OpenAPI спецификации."""

    title: str = Field(..., description="API title")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    contact: dict[str, str] | None = Field(None, description="Contact information")
    license: dict[str, str] | None = Field(None, description="License information")
    x_data_source: str | None = Field(None, alias="x-data-source", description="Data source")
    x_data_version: str | None = Field(None, alias="x-data-version", description="Data version")
    x_generator: str | None = Field(None, alias="x-generator", description="Generator name")
    x_generator_version: str | None = Field(None, alias="x-generator-version", description="Generator version")
    x_generated_date: str | None = Field(None, alias="x-generated-date", description="Generation date")
    x_market: str | None = Field(None, alias="x-market", description="Market name")
    x_field_count: int | None = Field(None, alias="x-field-count", description="Field count")

    model_config = ConfigDict(populate_by_name=True)


class OpenAPISpec(BaseModel):
    """OpenAPI спецификация."""

    openapi: str = Field("3.1.0", description="OpenAPI version")
    info: OpenAPISpecInfo = Field(..., description="API information")
    servers: list[dict[str, str]] | None = Field(None, description="API servers")
    security: list[dict[str, list[str]]] | None = Field(None, description="Security requirements")
    tags: list[dict[str, str]] | None = Field(None, description="API tags")
    paths: dict[str, Any] = Field(..., description="API paths")
    components: dict[str, Any] = Field(..., description="API components")


class GeneratorConfig(BaseModel):
    """Конфигурация генератора."""

    version: str = Field("2.0.0", description="Generator version")
    openapi_version: str = Field("3.1.0", description="OpenAPI version")
    data_source: str = Field("tv-screener", description="Data source")
    data_version: str = Field("0.4.0", description="Data source version")
    sync_auto: bool = Field(False, description="Auto sync data")
    validate_after_generate: bool = Field(True, description="Validate after generation")
    structure_tests: bool = Field(True, description="Run structure tests")
    consistency_tests: bool = Field(True, description="Run consistency tests")


class ValidationResult(BaseModel):
    """Результат валидации."""

    is_valid: bool = Field(..., description="Validation result")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class TestResult(BaseModel):
    """Результат тестирования."""

    structure_ok: int = Field(0, description="Structure tests passed")
    structure_fail: int = Field(0, description="Structure tests failed")
    consistency_ok: int = Field(0, description="Consistency tests passed")
    consistency_fail: int = Field(0, description="Consistency tests failed")
    total_tests: int = Field(0, description="Total tests")

    @property
    def all_passed(self) -> bool:
        """Все ли тесты прошли."""
        return self.structure_fail == 0 and self.consistency_fail == 0

    @property
    def success_rate(self) -> float:
        """Процент успешных тестов."""
        if self.total_tests == 0:
            return 0.0
        return (self.structure_ok + self.consistency_ok) / self.total_tests


class SyncResult(BaseModel):
    """Результат синхронизации."""

    files_copied: int = Field(0, description="Files copied")
    files_skipped: int = Field(0, description="Files skipped")
    errors: list[str] = Field(default_factory=list, description="Sync errors")
    warnings: list[str] = Field(default_factory=list, description="Sync warnings")

    @property
    def success(self) -> bool:
        """Успешна ли синхронизация."""
        return len(self.errors) == 0


class GenerationResult(BaseModel):
    """Результат генерации."""

    markets_processed: int = Field(0, description="Markets processed")
    specs_generated: int = Field(0, description="Specs generated")
    errors: list[str] = Field(default_factory=list, description="Generation errors")
    warnings: list[str] = Field(default_factory=list, description="Generation warnings")
    generation_time: datetime | None = Field(None, description="Generation time")

    @property
    def success(self) -> bool:
        """Успешна ли генерация."""
        return len(self.errors) == 0


class OpenAPIGeneratorResult(BaseModel):
    """Результат работы генератора OpenAPI."""

    markets_processed: int = Field(0, description="Markets processed")
    specs_generated: int = Field(0, description="Specs generated")
    errors: list[str] = Field(default_factory=list, description="Generation errors")
    warnings: list[str] = Field(default_factory=list, description="Generation warnings")
    generation_time: datetime | None = Field(None, description="Generation time")
    validation_result: ValidationResult | None = Field(None, description="Validation result")

    @property
    def success(self) -> bool:
        """Успешна ли генерация."""
        return len(self.errors) == 0 and (self.validation_result is None or self.validation_result.is_valid)
