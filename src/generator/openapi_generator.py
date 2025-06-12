import logging
from pathlib import Path
from typing import Any, Dict, Iterable

import json
import toml

import yaml
from src.utils import tv2ref


class _IndentedDumper(yaml.SafeDumper):
    """YAML dumper that indents sequences properly."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """Override to disable indentless lists."""
        super().increase_indent(flow, False)


logger = logging.getLogger(__name__)


class OpenAPIGenerator:
    """Generate a simple OpenAPI spec from collected field data."""

    def __init__(self, results_dir: Path) -> None:
        """Create generator using directory with scan results."""

        self.results_dir = results_dir
        root = Path(__file__).resolve().parents[2]
        self.version = toml.load(root / "pyproject.toml")["project"]["version"]

    def collect_market_fields(
        self, market_dir: Path
    ) -> tuple[list[tuple[str, Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
        """Return available fields and their OpenAPI definitions for a market."""
        meta_file = market_dir / "metainfo.json"
        if not meta_file.exists():
            raise RuntimeError(f"Missing metainfo.json for market {market_dir.name}")
        meta = json.loads(meta_file.read_text())

        fields_data: list[dict[str, Any]] = []
        if isinstance(meta.get("data"), dict) and isinstance(
            meta["data"].get("fields"), list
        ):
            fields_data = list(meta["data"].get("fields", []))
        elif isinstance(meta.get("fields"), list):
            fields_data = list(meta.get("fields", []))

        ordered_fields: list[tuple[str, Dict[str, Any]]] = []
        field_defs: Dict[str, Dict[str, Any]] = {}
        for item in fields_data:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("id")
            if not name:
                continue
            type_name = str(item.get("type", "string")).lower()
            try:
                ref = tv2ref(type_name)
            except KeyError:
                ref = "#/components/schemas/Str"
            schema = {"$ref": ref}
            ordered_fields.append((str(name), schema))
            field_defs[str(name)] = schema

        ordered_fields.sort(key=lambda x: x[0])
        return ordered_fields, field_defs

    def _add_metainfo_path(
        self, openapi: dict[str, Any], market: str, cap: str
    ) -> None:
        """Add /{market}/metainfo endpoint to OpenAPI spec."""

        openapi["paths"][f"/{market}/metainfo"] = {
            "post": {
                "summary": f"Get {market} metainfo",
                "operationId": f"{cap}Metainfo",
                "x-openai-isConsequential": False,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": (
                                        f"#/components/schemas/{cap}MetainfoResponse"
                                    )
                                }
                            }
                        },
                    },
                    "400": {"description": "Bad Request"},
                    "500": {"description": "Server Error"},
                },
            }
        }
        openapi["components"]["schemas"][f"{cap}MetainfoResponse"] = {
            "type": "object",
            "properties": {"fields": {"type": "array", "items": {"type": "string"}}},
        }

    def render(self, market: str | None = None, max_size: int = 1_048_576) -> str:
        """Return OpenAPI YAML for the given market scope."""

        openapi: Dict[str, Any] = {
            "openapi": "3.1.0",
            "x-oai-custom-action-schema-version": "v1",
            "info": {
                "title": "Unofficial TradingView Scanner API",
                "version": self.version,
                "description": "Auto-generated from collected field data.",
            },
            "servers": [{"url": "https://scanner.tradingview.com"}],
            "paths": {},
            "components": {"schemas": {}},
        }

        base = {
            "Num": {"type": "number"},
            "Str": {"type": "string"},
            "Bool": {"type": "boolean"},
            "Time": {"type": "string", "format": "date-time"},
        }
        openapi["components"]["schemas"].update(base)

        markets: Iterable[Path]
        if market:
            markets = [self.results_dir / market]
        else:
            markets = [p for p in self.results_dir.iterdir() if p.is_dir()]

        for market_path in markets:
            if not market_path.is_dir():
                raise FileNotFoundError(market_path.name)
            market = market_path.name
            fields, field_defs = self.collect_market_fields(market_path)
            cap = market.capitalize()
            openapi["paths"][f"/{market}/scan"] = {
                "post": {
                    "summary": f"Scan {market}",
                    "operationId": f"{cap}Scan",
                    "x-openai-isConsequential": False,
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{cap}ScanRequest"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": (
                                            f"#/components/schemas/{cap}ScanResponse"
                                        )
                                    }
                                }
                            },
                        },
                        "400": {"description": "Bad Request"},
                        "500": {"description": "Server Error"},
                    },
                }
            }

            for ep_name, req, resp in [
                ("search", "SearchRequest", "SearchResponse"),
                ("history", "HistoryRequest", "HistoryResponse"),
                ("summary", "SummaryRequest", "SummaryResponse"),
            ]:
                openapi["paths"][f"/{market}/{ep_name}"] = {
                    "post": {
                        "summary": f"{ep_name.capitalize()} {market}",
                        "operationId": f"{cap}{ep_name.capitalize()}",
                        "x-openai-isConsequential": False,
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{cap}{req}"
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{cap}{resp}"
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Bad Request"},
                            "500": {"description": "Server Error"},
                        },
                    }
                }

            self._add_metainfo_path(openapi, market, cap)

            if len(fields) > 64:
                parts = []
                for idx in range(0, len(fields), 64):
                    part_num = idx // 64 + 1
                    part_name = f"{cap}FieldsPart{part_num:02d}"
                    props = {
                        name: schema
                        for name, schema in fields[idx : idx + 64]  # noqa: E203
                    }
                    openapi["components"]["schemas"][part_name] = {
                        "type": "object",
                        "properties": props,
                    }
                    parts.append({"$ref": f"#/components/schemas/{part_name}"})
                openapi["components"]["schemas"][f"{cap}Fields"] = {
                    "allOf": parts,
                    "additionalProperties": False,
                }
            else:
                openapi["components"]["schemas"][f"{cap}Fields"] = {
                    "type": "object",
                    "properties": {name: schema for name, schema in fields},
                    "additionalProperties": False,
                }
            openapi["components"]["schemas"][f"{cap}ScanRequest"] = {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "object",
                        "properties": {
                            "tickers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "query": {
                                "type": "object",
                                "properties": {
                                    "types": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                },
                            },
                        },
                    },
                    "columns": {"type": "array", "items": {"type": "string"}},
                    "filter": {"type": "object"},
                    "filter2": {"type": "object"},
                    "sort": {"type": "object"},
                    "range": {"type": "object"},
                },
                "required": ["symbols", "columns"],
            }
            openapi["components"]["schemas"][f"{cap}ScanResponse"] = {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"$ref": f"#/components/schemas/{cap}Fields"},
                    }
                },
            }

            for req in ["SearchRequest", "HistoryRequest", "SummaryRequest"]:
                openapi["components"]["schemas"][f"{cap}{req}"] = {
                    "type": "object",
                }
            for resp in ["SearchResponse", "HistoryResponse", "SummaryResponse"]:
                openapi["components"]["schemas"][f"{cap}{resp}"] = {
                    "type": "object",
                }

        yaml_str = yaml.dump(
            openapi,
            sort_keys=False,
            indent=2,
            explicit_start=False,
            Dumper=_IndentedDumper,
        )
        if len(yaml_str.encode()) > max_size:
            raise RuntimeError("YAML size exceeds limit")
        return yaml_str

    def generate(
        self, output: Path, market: str | None = None, max_size: int = 1_048_576
    ) -> None:
        """Render the specification and write it to ``output``."""

        yaml_str = self.render(market=market, max_size=max_size)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_str, encoding="utf-8")
        logger.info("OpenAPI spec saved to %s", output)
