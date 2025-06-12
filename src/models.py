from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TVBaseModel(BaseModel):
    """Base model with compatibility helpers."""

    @classmethod
    def parse_obj(cls, obj: Any) -> "TVBaseModel":
        """Create an instance from a parsed object (pydantic v1 style)."""
        return cls.model_validate(obj)


class TVField(TVBaseModel):
    """TradingView field description."""

    n: str = Field(alias="name")
    t: str = Field(alias="type")
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
                fields = [TVField.parse_obj(f) for f in fields_json]
                return cls(data=fields)
        return super().parse_obj(obj)

    @property
    def fields(self) -> list[TVField]:
        return self.data


class ScanItem(TVBaseModel):
    """Single scan item."""

    d: list[object]


class ScanResponse(TVBaseModel):
    """Response for scan results."""

    data: list[ScanItem]


__all__ = ["TVField", "MetaInfoResponse", "ScanItem", "ScanResponse"]
