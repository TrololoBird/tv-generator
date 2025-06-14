from __future__ import annotations

from typing import Any, cast, Dict

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    constr,
    confloat,
    AliasChoices,
    RootModel,
    field_validator,
)

# Accepted TradingView field types
KNOWN_FIELD_TYPES = [
    "number",
    "price",
    "fundamental_price",
    "percent",
    "integer",
    "float",
    "string",
    "bool",
    "boolean",
    "text",
    "map",
    "set",
    "interface",
    "time",
    "time-yyyymmdd",
    "array",
    "duration",
    "percentage",
]

FieldTypeLiteral = Literal[
    "number",
    "price",
    "fundamental_price",
    "percent",
    "integer",
    "float",
    "string",
    "bool",
    "boolean",
    "text",
    "map",
    "set",
    "interface",
    "time",
    "time-yyyymmdd",
    "array",
    "duration",
    "percentage",
]

FieldType = Annotated[str, FieldTypeLiteral]


class TVBaseModel(BaseModel):
    """Base model with compatibility helpers."""

    @classmethod
    def parse_obj(cls, obj: Any) -> "TVBaseModel":
        """Create an instance from a parsed object (pydantic v1 style)."""
        return cls.model_validate(obj)


class TVField(TVBaseModel):
    """TradingView field description."""

    n: Annotated[str, constr(strip_whitespace=True, min_length=1)] = Field(alias="name")
    t: FieldType = Field(alias="type")
    interval: Annotated[float, confloat(gt=0)] | None = None
    description: Annotated[str, constr(strip_whitespace=True, min_length=1)] | None = (
        None
    )
    flags: list[str] | None = None

    @field_validator("t", mode="before")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in KNOWN_FIELD_TYPES:
            import warnings

            warnings.warn(
                f"Unknown TradingView field type '{v}', falling back to str",
                RuntimeWarning,
            )
        return v


class MetaInfoResponse(TVBaseModel):
    """Response containing field metadata."""

    data: list[TVField]

    @classmethod
    def parse_obj(cls, obj: Any) -> "MetaInfoResponse":
        """Parse TradingView metainfo JSON into a model."""
        if isinstance(obj, dict):
            fields_json = None
            if isinstance(obj.get("data"), dict):
                fields_json = obj.get("data", {}).get("fields")
            if fields_json is None:
                fields_json = obj.get("fields")
            if isinstance(fields_json, list):
                fields = [cast(TVField, TVField.parse_obj(f)) for f in fields_json]
                return cls(data=fields)
        return cast(MetaInfoResponse, super().parse_obj(obj))

    @property
    def fields(self) -> list[TVField]:
        return self.data


class ScanItem(TVBaseModel):
    """Single scan item."""

    s: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    d: list[object]


class ScanResponse(TVBaseModel):
    """Response for scan results."""

    data: list[ScanItem]
    count: int | None = Field(
        default=None, validation_alias=AliasChoices("count", "totalCount")
    )


class GenericResponse(RootModel[Dict[str, Any]]):
    """Generic mapping used for search/history/summary."""

    root: Dict[str, Any]


class SearchResponse(GenericResponse):
    """Response model for ``/search`` endpoint."""


class HistoryResponse(GenericResponse):
    """Response model for ``/history`` endpoint."""


class SummaryResponse(GenericResponse):
    """Response model for ``/summary`` endpoint."""


__all__ = [
    "TVField",
    "MetaInfoResponse",
    "ScanItem",
    "ScanResponse",
    "SearchResponse",
    "HistoryResponse",
    "SummaryResponse",
]
