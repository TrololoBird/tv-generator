"""
Async file manager for OpenAPI generator.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from loguru import logger

from .base import BaseFileManager


class AsyncFileManager(BaseFileManager):
    """Async file manager for efficient file operations."""

    def __init__(self, data_dir: Path = Path("data"), specs_dir: Path = Path("docs/specs")):
        self.data_dir = data_dir
        self.specs_dir = specs_dir
        self.metainfo_dir = data_dir / "metainfo"
        self.scan_dir = data_dir / "scan"

        # Ensure directories exist
        asyncio.create_task(self.ensure_directory(self.specs_dir))
        asyncio.create_task(self.ensure_directory(self.metainfo_dir))
        asyncio.create_task(self.ensure_directory(self.scan_dir))

    async def ensure_directory(self, path: Path) -> None:
        """Ensure directory exists."""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise

    async def save_spec(self, market: str, spec: dict[str, Any]) -> None:
        """Save OpenAPI specification to file."""
        spec_path = self.specs_dir / f"{market}_openapi.json"

        try:
            async with aiofiles.open(spec_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(spec, indent=2, ensure_ascii=False))
            logger.info(f"Saved OpenAPI spec for {market}")
        except Exception as e:
            logger.error(f"Failed to save spec for {market}: {e}")
            raise

    async def load_metainfo(self, market: str) -> dict[str, Any]:
        """Load market metainfo from file."""
        metainfo_path = self.metainfo_dir / f"{market}.json"
        if not metainfo_path.exists():
            logger.warning(f"Metainfo file not found for {market}: {metainfo_path}")
            return {}
        try:
            async with aiofiles.open(metainfo_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                if isinstance(data, list):
                    return {"fields": data}
                return data
        except Exception as e:
            logger.error(f"Failed to load metainfo for {market}: {e}")
            return {}

    async def save_metainfo(self, market: str, metainfo: dict[str, Any]) -> None:
        """Save market metainfo to file."""
        metainfo_path = self.metainfo_dir / f"{market}.json"

        try:
            async with aiofiles.open(metainfo_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metainfo, indent=2, ensure_ascii=False))
            logger.info(f"Saved metainfo for {market}")
        except Exception as e:
            logger.error(f"Failed to save metainfo for {market}: {e}")
            raise

    async def load_scan_data(self, market: str) -> list[dict[str, Any]]:
        """Load market scan data from file."""
        scan_path = self.scan_dir / f"{market}.json"

        if not scan_path.exists():
            logger.warning(f"Scan file not found for {market}: {scan_path}")
            return []

        try:
            async with aiofiles.open(scan_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return data.get("data", []) if isinstance(data, dict) else data
        except Exception as e:
            logger.error(f"Failed to load scan data for {market}: {e}")
            return []

    async def save_scan_data(self, market: str, scan_data: list[dict[str, Any]]) -> None:
        """Save market scan data to file."""
        scan_path = self.scan_dir / f"{market}.json"

        try:
            data = {"data": scan_data, "totalCount": len(scan_data)}
            async with aiofiles.open(scan_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"Saved scan data for {market}")
        except Exception as e:
            logger.error(f"Failed to save scan data for {market}: {e}")
            raise

    async def load_markets(self) -> list[str]:
        """Load list of markets from file."""
        markets_path = self.data_dir / "markets.json"

        if not markets_path.exists():
            logger.warning(f"Markets file not found: {markets_path}")
            return []

        try:
            async with aiofiles.open(markets_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("countries", []) + data.get("other", [])
                else:
                    return []
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            return []

    async def save_markets(self, markets: list[str]) -> None:
        """Save list of markets to file."""
        markets_path = self.data_dir / "markets.json"

        try:
            async with aiofiles.open(markets_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(markets, indent=2, ensure_ascii=False))
            logger.info(f"Saved {len(markets)} markets")
        except Exception as e:
            logger.error(f"Failed to save markets: {e}")
            raise

    async def load_display_names(self) -> dict[str, str]:
        """Load display names from file."""
        display_names_path = self.data_dir / "column_display_names.json"

        if not display_names_path.exists():
            logger.warning(f"Display names file not found: {display_names_path}")
            return {}

        try:
            async with aiofiles.open(display_names_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to load display names: {e}")
            return {}

    async def save_display_names(self, display_names: dict[str, str]) -> None:
        """Save display names to file."""
        display_names_path = self.data_dir / "column_display_names.json"

        try:
            async with aiofiles.open(display_names_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(display_names, indent=2, ensure_ascii=False))
            logger.info(f"Saved {len(display_names)} display names")
        except Exception as e:
            logger.error(f"Failed to save display names: {e}")
            raise

    async def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        return file_path.exists()

    async def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        try:
            return file_path.stat().st_size
        except Exception:
            return 0

    async def get_file_mtime(self, file_path: Path) -> float | None:
        """Get file modification time."""
        try:
            return file_path.stat().st_mtime
        except Exception:
            return None
