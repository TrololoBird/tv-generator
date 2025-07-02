"""
Base classes and interfaces for core module.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

# Full debug logger setup for all base classes
logger = logging.getLogger("tv_generator.core.base")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    fh = logging.FileHandler("base_debug.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s:%(lineno)d - " "%(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)


class BaseSchemaGenerator(ABC):
    """Base class for schema generators."""

    @abstractmethod
    def generate_field_schema(self, field: dict[str, Any], market: str | None = None) -> dict[str, Any]:
        logger.debug(f"Called generate_field_schema with field={field}, market={market}")
        pass

    @abstractmethod
    def generate_filter_schema(self, metainfo: dict[str, Any]) -> dict[str, Any]:
        logger.debug(f"Called generate_filter_schema with metainfo={metainfo}")
        pass

    @abstractmethod
    def generate_request_body_schema(self, fields: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
        logger.debug(f"Called generate_request_body_schema with fields={fields}, filters={filters}")
        pass


class BaseValidator(ABC):
    """Base class for validators."""

    @abstractmethod
    def validate_field(self, field: dict[str, Any]) -> bool:
        logger.debug(f"Called validate_field with field={field}")
        pass

    @abstractmethod
    def validate_schema(self, schema: dict[str, Any]) -> bool:
        logger.debug(f"Called validate_schema with schema={schema}")
        pass

    @abstractmethod
    def validate_example(self, example: Any, schema_type: str) -> bool:
        logger.debug(f"Called validate_example with example={example}, schema_type={schema_type}")
        pass


class BaseCache(ABC):
    """Base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        logger.debug(f"Called get with key={key}")
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        logger.debug(f"Called set with key={key}, value={value}, ttl={ttl}")
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        logger.debug(f"Called delete with key={key}")
        pass

    @abstractmethod
    async def clear(self) -> None:
        logger.debug("Called clear")
        pass


class BaseFileManager(ABC):
    """Base class for file operations."""

    @abstractmethod
    async def save_spec(self, market: str, spec: dict[str, Any]) -> None:
        logger.debug(f"Called save_spec with market={market}, spec={spec}")
        pass

    @abstractmethod
    async def load_metainfo(self, market: str) -> dict[str, Any]:
        logger.debug(f"Called load_metainfo with market={market}")
        pass

    @abstractmethod
    async def load_scan_data(self, market: str) -> list[dict[str, Any]]:
        logger.debug(f"Called load_scan_data with market={market}")
        pass

    @abstractmethod
    async def ensure_directory(self, path: Path) -> None:
        logger.debug(f"Called ensure_directory with path={path}")
        pass
