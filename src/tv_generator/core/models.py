from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TVField(BaseModel):
    n: str = Field(..., description="Field name")
    t: str = Field(..., description="Field type")
    r: list[Any] | None = Field(None, description="Enum values or None")
    d: str | None = Field(None, description="Description")
    # Можно добавить другие поля по мере необходимости


class TVFilter(BaseModel):
    n: str = Field(..., description="Filter name")
    type: str = Field(..., description="Filter type")
    values: list[Any] | None = Field(None, description="Enum values or None")
    required: bool | None = Field(False, description="Is filter required")
    # Можно добавить другие поля по мере необходимости
