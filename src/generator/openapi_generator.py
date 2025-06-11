import logging
from pathlib import Path
from typing import Any, Dict, Iterable

import toml

import pandas as pd
import yaml
from src.utils.infer import infer_type


class _IndentedDumper(yaml.SafeDumper):
    """YAML dumper that indents sequences properly."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


logger = logging.getLogger(__name__)


class OpenAPIGenerator:
    """Generate a simple OpenAPI spec from collected field data."""

    def __init__(self, results_dir: Path) -> None:
        """Create generator using directory with scan results."""

        self.results_dir = results_dir
        root = Path(__file__).resolve().parents[2]
        self.version = toml.load(root / "pyproject.toml")["project"]["version"]

    def collect_market_fields(self, market_dir: Path):
        df = pd.read_csv(market_dir / "field_status.tsv", sep="\t")
        df_ok = df[df["status"] == "ok"]
        fields = sorted(set(df_ok["field"]))
        field_types: Dict[str, str] = {}
        for field in fields:
            val_series = df_ok[df_ok["field"] == field]["value"].dropna()
            if not val_series.empty:
                field_types[field] = infer_type(val_series.iloc[0])
            else:
                field_types[field] = "string"
        return fields, field_types

    def _add_metainfo_path(
        self, openapi: dict[str, Any], market: str, cap: str
    ) -> None:
        """Add /{market}/metainfo endpoint to OpenAPI spec."""

        openapi["paths"][f"/{market}/metainfo"] = {
            "post": {
                "summary": f"Get {market} metainfo",
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

    def generate(self, output: Path, market: str | None = None) -> None:
        openapi: Dict[str, Any] = {
            "openapi": "3.1.0",
            "info": {
                "title": "Unofficial TradingView Scanner API",
                "version": self.version,
                "description": "Auto-generated from collected field data.",
            },
            "servers": [{"url": "https://scanner.tradingview.com"}],
            "paths": {},
            "components": {"schemas": {}},
        }

        markets: Iterable[Path]
        if market:
            markets = [self.results_dir / market]
        else:
            markets = [p for p in self.results_dir.iterdir() if p.is_dir()]

        for market_path in markets:
            if not market_path.is_dir():
                raise FileNotFoundError(market_path.name)
            market = market_path.name
            field_file = market_path / "field_status.tsv"
            if not field_file.exists():
                raise RuntimeError(f"Missing field_status.tsv for market {market}")
            columns, types = self.collect_market_fields(market_path)
            cap = market.capitalize()
            openapi["paths"][f"/{market}/scan"] = {
                "post": {
                    "summary": f"Scan {market}",
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

            # additional endpoints
            for ep_name, req, resp in [
                ("search", "SearchRequest", "SearchResponse"),
                ("history", "HistoryRequest", "HistoryResponse"),
                ("summary", "SummaryRequest", "SummaryResponse"),
            ]:
                openapi["paths"][f"/{market}/{ep_name}"] = {
                    "post": {
                        "summary": f"{ep_name.capitalize()} {market}",
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

            openapi["components"]["schemas"][f"{cap}Fields"] = {
                "type": "object",
                "properties": {f: {"type": types[f]} for f in columns},
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

            # simple request/response schemas for other endpoints
            for req in ["SearchRequest", "HistoryRequest", "SummaryRequest"]:
                openapi["components"]["schemas"][f"{cap}{req}"] = {
                    "type": "object",
                }
            for resp in ["SearchResponse", "HistoryResponse", "SummaryResponse"]:
                openapi["components"]["schemas"][f"{cap}{resp}"] = {
                    "type": "object",
                }

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(
                openapi,
                f,
                sort_keys=False,
                indent=2,
                explicit_start=False,
                Dumper=_IndentedDumper,
            )
        logger.info("OpenAPI spec saved to %s", output)
