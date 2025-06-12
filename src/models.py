from __future__ import annotations

from pydantic import BaseModel, Field


class TVField(BaseModel):
    """TradingView field description."""

    n: str = Field(alias="name")
    t: str = Field(alias="type")
    flags: list[str] | None = None


class MetaInfoResponse(BaseModel):
    """Response containing field metadata."""

    data: list[TVField]

    @property
    def fields(self) -> list[TVField]:
        return self.data


class ScanItem(BaseModel):
    """Single scan item."""

    d: list[object]


class ScanResponse(BaseModel):
    """Response for scan results."""

    data: list[ScanItem]


__all__ = ["TVField", "MetaInfoResponse", "ScanItem", "ScanResponse"]
