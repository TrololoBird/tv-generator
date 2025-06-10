import logging
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd
import yaml

from src.utils.infer import infer_type

logger = logging.getLogger(__name__)


class OpenAPIGenerator:
    """Generate a simple OpenAPI spec from collected field data."""

    def __init__(self, results_dir: Path) -> None:
        """Create generator using directory with scan results."""

        self.results_dir = results_dir

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

    def generate(self, output: Path, market: str | None = None) -> None:
        openapi: Dict[str, Any] = {
            "openapi": "3.1.0",
            "info": {
                "title": "Unofficial TradingView Scanner API",
                "version": "1.0.0",
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
                continue
            market = market_path.name
            field_file = market_path / "field_status.tsv"
            if not field_file.exists():
                logger.warning("Skip %s: missing field_status.tsv", market)
                continue
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
                        }
                    },
                }
            }
            openapi["components"]["schemas"][f"{cap}Fields"] = {
                "type": "object",
                "properties": {f: {"type": types[f]} for f in columns},
            }
            openapi["components"]["schemas"][f"{cap}ScanRequest"] = {
                "type": "object",
                "properties": {
                    "symbols": {"type": "object"},
                    "columns": {"type": "array", "items": {"type": "string"}},
                },
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

        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(openapi, f, sort_keys=False)
        logger.info("OpenAPI spec saved to %s", output)
