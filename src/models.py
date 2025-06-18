from __future__ import annotations

from typing import Annotated, Literal, cast

from pydantic import (
    BaseModel,
    Field,
    constr,
    confloat,
    AliasChoices,
    RootModel,
    field_validator,
)

# JSON helper types
JSONValue = object
JSONDict = dict[str, JSONValue]

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
    """Base model with compatibility helpers.

    Examples
    --------
    >>> TVField.model_validate({'name': 'close', 'type': 'float'})
    TVField(n='close', t='float', interval=None, description=None, flags=None)
    """

    @classmethod
    def parse_obj(cls, obj: object) -> "TVBaseModel":
        """Create an instance from a parsed object (pydantic v1 style)."""
        return cls.model_validate(obj)


class TVField(TVBaseModel):
    """TradingView field description.

    Examples
    --------
    >>> TVField.model_validate({"name": "close", "type": "float"})
    TVField(n='close', t='float', interval=None, description=None, flags=None)
    """

    n: Annotated[str, constr(strip_whitespace=True, min_length=1)] = Field(
        serialization_alias="name",
        validation_alias=AliasChoices("name", "id", "n"),
    )
    t: FieldType = Field(
        serialization_alias="type",
        validation_alias=AliasChoices("type", "t"),
    )
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

    @field_validator("flags", mode="before")
    @classmethod
    def _validate_flags(cls, v: list[str] | str | None) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise TypeError("flags must be a list of strings")
        if not all(isinstance(item, str) and item.strip() for item in v):
            raise ValueError("flags must contain non-empty strings")
        return [item.strip() for item in v]

    @field_validator("interval", mode="before")
    @classmethod
    def _validate_interval(cls, v: float | str | None) -> float | None:
        if v is None:
            return None
        try:
            value = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("interval must be a positive number") from exc
        if value <= 0:
            raise ValueError("interval must be positive")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _validate_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise TypeError("description must be a string")
        v = v.strip()
        if not v:
            raise ValueError("description cannot be empty")
        return v


class MetaInfoResponse(TVBaseModel):
    """Response containing field metadata.

    Examples
    --------
    >>> MetaInfoResponse.model_validate({
    ...     "fields": [{"name": "close", "type": "float"}]
    ... })
    MetaInfoResponse(data=[TVField(n='close', t='float', interval=None, ...)])
    """

    data: list[TVField]

    @classmethod
    def parse_obj(cls, obj: object) -> "MetaInfoResponse":
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
    """Single scan item.

    Examples
    --------
    >>> ScanItem.model_validate({"s": "BINANCE:BTCUSD", "d": [50000.0]})
    ScanItem(s='BINANCE:BTCUSD', d=[50000.0])
    """

    s: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    d: list[JSONValue]


class ScanResponse(TVBaseModel):
    """Response for scan results.

    Examples
    --------
    >>> ScanResponse.model_validate({
    ...     "data": [{"s": "BINANCE:BTCUSD", "d": [1]}],
    ...     "count": 1,
    ... })
    ScanResponse(data=[ScanItem(s='BINANCE:BTCUSD', d=[1])], count=1)
    """

    data: list[ScanItem]
    count: int | None = Field(
        default=None, validation_alias=AliasChoices("count", "totalCount")
    )


class GenericResponse(RootModel[JSONDict]):
    """Generic mapping used for search/history/summary.

    Examples
    --------
    >>> SearchResponse.model_validate({"status": "ok"})
    SearchResponse(root={'status': 'ok'})
    """

    root: JSONDict


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
