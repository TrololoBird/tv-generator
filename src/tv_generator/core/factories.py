"""
Factory classes for creating schema generators and validators.
"""

from typing import Any, Dict, Optional

from .base import BaseSchemaGenerator, BaseValidator


class SchemaGeneratorFactory:
    """Factory for creating schema generators."""

    _generators: dict[str, type[BaseSchemaGenerator]] = {}

    @classmethod
    def register(cls, name: str, generator_class: type[BaseSchemaGenerator]) -> None:
        """Register a schema generator class."""
        cls._generators[name] = generator_class

    @classmethod
    def create_generator(cls, market_type: str, config: dict[str, Any] | None = None) -> BaseSchemaGenerator:
        """Create a schema generator for the given market type."""
        if market_type not in cls._generators:
            # Default to generic generator
            from .schema_generator import SchemaGenerator

            return SchemaGenerator(config or {})

        generator_class = cls._generators[market_type]
        return generator_class(config or {})

    @classmethod
    def get_available_generators(cls) -> list[str]:
        """Get list of available generator types."""
        return list(cls._generators.keys())


class ValidatorFactory:
    """Factory for creating validators."""

    _validators: dict[str, type[BaseValidator]] = {}

    @classmethod
    def register(cls, name: str, validator_class: type[BaseValidator]) -> None:
        """Register a validator class."""
        cls._validators[name] = validator_class

    @classmethod
    def create_validator(cls, validation_type: str = "default") -> BaseValidator:
        """Create a validator for the given validation type."""
        if validation_type not in cls._validators:
            # Default to standard validator
            from .validator import Validator

            return Validator()

        validator_class = cls._validators[validation_type]
        return validator_class()

    @classmethod
    def get_available_validators(cls) -> list[str]:
        """Get list of available validator types."""
        return list(cls._validators.keys())


class CacheFactory:
    """Factory for creating cache instances."""

    @staticmethod
    def create_memory_cache(max_size: int = 1000, ttl: int = 3600):
        """Create a memory cache instance."""
        from .cache import MemoryCache

        return MemoryCache(max_size=max_size, ttl=ttl)

    @staticmethod
    def create_disk_cache(cache_dir: str = "cache", ttl: int = 86400):
        """Create a disk cache instance."""
        from pathlib import Path

        from .cache import DiskCache

        return DiskCache(cache_dir=Path(cache_dir), ttl=ttl)

    @staticmethod
    def create_api_cache(ttl: int = 1800):
        """Create an API cache instance."""
        from .cache import APICache

        return APICache(ttl=ttl)

    @staticmethod
    def create_multi_level_cache(cache_dir: str = "cache"):
        """Create a multi-level cache instance."""
        from pathlib import Path

        from .cache import MultiLevelCache

        return MultiLevelCache(cache_dir=Path(cache_dir))


class FileManagerFactory:
    """Factory for creating file manager instances."""

    @staticmethod
    def create_async_file_manager(data_dir: str = "data", specs_dir: str = "docs/specs"):
        """Create an async file manager instance."""
        from pathlib import Path

        from .file_manager import AsyncFileManager

        return AsyncFileManager(data_dir=Path(data_dir), specs_dir=Path(specs_dir))
