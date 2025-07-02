"""
Caching system for OpenAPI generator.
"""

import asyncio
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .base import BaseCache


class MemoryCache(BaseCache):
    """In-memory LRU cache implementation."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

    async def get(self, key: str) -> Any | None:
        """Get value from memory cache."""
        if key not in self.cache:
            return None

        item = self.cache[key]
        if time.time() - item["timestamp"] > self.ttl:
            await self.delete(key)
            return None

        # Move to end (LRU)
        self.cache.move_to_end(key)
        return item["value"]

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in memory cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            self.cache.popitem(last=False)

        self.cache[key] = {"value": value, "timestamp": time.time(), "ttl": ttl or self.ttl}
        self.cache.move_to_end(key)

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        self.cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()


class DiskCache(BaseCache):
    """Disk-based cache implementation."""

    def __init__(self, cache_dir: Path = Path("cache"), ttl: int = 86400):
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        return self.cache_dir / f"{key}.json"

    async def get(self, key: str) -> Any | None:
        """Get value from disk cache."""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            if time.time() - data["timestamp"] > data["ttl"]:
                await self.delete(key)
                return None

            return data["value"]
        except Exception as e:
            logger.warning(f"Failed to load cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in disk cache."""
        cache_path = self._get_cache_path(key)

        try:
            data = {"value": value, "timestamp": time.time(), "ttl": ttl or self.ttl}

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from disk cache."""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

    async def clear(self) -> None:
        """Clear all cache."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


class APICache(BaseCache):
    """API response cache implementation."""

    def __init__(self, ttl: int = 1800):  # 30 minutes for API responses
        self.ttl = ttl
        self.cache: dict[str, dict[str, Any]] = {}

    async def get(self, key: str) -> Any | None:
        """Get value from API cache."""
        if key not in self.cache:
            return None

        item = self.cache[key]
        if time.time() - item["timestamp"] > self.ttl:
            await self.delete(key)
            return None

        return item["value"]

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in API cache."""
        self.cache[key] = {"value": value, "timestamp": time.time(), "ttl": ttl or self.ttl}

    async def delete(self, key: str) -> None:
        """Delete value from API cache."""
        self.cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()


class MultiLevelCache:
    """Multi-level cache with memory, disk, and API levels."""

    def __init__(self, cache_dir: Path = Path("cache")):
        self.memory_cache = MemoryCache(max_size=1000, ttl=3600)
        self.disk_cache = DiskCache(cache_dir=cache_dir, ttl=86400)
        self.api_cache = APICache(ttl=1800)

    async def get(self, key: str) -> Any | None:
        """Get value from multi-level cache."""
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value

        # Try disk cache
        value = await self.disk_cache.get(key)
        if value is not None:
            # Store in memory cache for faster access
            await self.memory_cache.set(key, value)
            return value

        # Try API cache
        value = await self.api_cache.get(key)
        if value is not None:
            # Store in memory and disk cache
            await self.memory_cache.set(key, value)
            await self.disk_cache.set(key, value)
            return value

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in all cache levels."""
        await asyncio.gather(
            self.memory_cache.set(key, value, ttl),
            self.disk_cache.set(key, value, ttl),
            self.api_cache.set(key, value, ttl),
        )

    async def delete(self, key: str) -> None:
        """Delete value from all cache levels."""
        await asyncio.gather(self.memory_cache.delete(key), self.disk_cache.delete(key), self.api_cache.delete(key))

    async def clear(self) -> None:
        """Clear all cache levels."""
        await asyncio.gather(self.memory_cache.clear(), self.disk_cache.clear(), self.api_cache.clear())
