from __future__ import annotations

from typing import Any, cast, ClassVar, Literal

from pydantic import BaseModel, Field, constr, confloat, AliasChoices

# Accepted TradingView field types
FieldType = Literal[
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
]


class TVBaseModel(BaseModel):
    """Base model with compatibility helpers."""

    @classmethod
    def parse_obj(cls, obj: Any) -> "TVBaseModel":
        """Create an instance from a parsed object (pydantic v1 style)."""
        return cls.model_validate(obj)


class TVField(TVBaseModel):
    """TradingView field description."""

    n: constr(strip_whitespace=True, min_length=1) = Field(alias="name")
    t: FieldType = Field(alias="type")
    interval: confloat(gt=0) | None = None
    description: constr(strip_whitespace=True, min_length=1) | None = None
    flags: list[str] | None = None


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

    s: constr(strip_whitespace=True, min_length=1)
    d: list[object]


class ScanResponse(TVBaseModel):
    """Response for scan results."""

    data: list[ScanItem]
    count: int | None = Field(
        default=None, validation_alias=AliasChoices("count", "totalCount")
    )


__all__ = ["TVField", "MetaInfoResponse", "ScanItem", "ScanResponse"]
