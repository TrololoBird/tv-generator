"""Configuration management for tv-generator.

This module provides a single :class:`Settings` instance that loads
configuration from environment variables using pydantic's
:class:`BaseSettings`. Currently only the ``TV_API_TOKEN`` variable is
supported and, if set, must be at least 10 characters long.  The loaded
settings are used across the code base and should never be printed to
logs.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    tv_api_token: str | None = Field(
        default=None,
        env="TV_API_TOKEN",
    )  # type: ignore[call-overload]

    @field_validator("tv_api_token")
    def _validate_token(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 10:
            raise ValueError("TV_API_TOKEN too short")
        return value


settings = Settings()
