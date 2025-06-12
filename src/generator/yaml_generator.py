from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
import toml
import yaml

from src.models import MetaInfoResponse
from src.utils import tv2ref


class _IndentedDumper(yaml.SafeDumper):
    """YAML dumper that indents sequences properly."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, False)


def generate_yaml(
    scope: str,
    meta: MetaInfoResponse,
    tsv: pd.DataFrame,
    server_url: str = "https://scanner.tradingview.com",
    max_size: int = 1_048_576,
) -> str:
    """Return OpenAPI YAML specification for a scope."""

    cap = scope.capitalize()
    root = Path(__file__).resolve().parents[2]
    version = toml.load(root / "pyproject.toml")["project"]["version"]

    fields: list[tuple[str, Dict[str, Any]]] = []
    for field in meta.fields:
        flags = set(field.flags or [])
        if {"deprecated", "private"} & flags:
            continue
        fields.append((field.n, {"$ref": tv2ref(field.t)}))

    fields.sort(key=lambda x: x[0])

    openapi: Dict[str, Any] = {
        "openapi": "3.1.0",
        "x-oai-custom-action-schema-version": "v1",
        "info": {
            "title": f"Unofficial TradingView {cap} API",
            "version": version,
        },
        "servers": [{"url": server_url}],
        "paths": {},
        "components": {"schemas": {}},
    }

    base = {
        "Num": {"type": "number"},
        "Str": {"type": "string"},
        "Bool": {"type": "boolean"},
        "Time": {"type": "string", "format": "date-time"},
    }
    for name, schema in base.items():
        openapi["components"]["schemas"].setdefault(name, schema)

    if len(fields) > 64:
        parts = []
        for idx in range(0, len(fields), 64):
            part_num = idx // 64 + 1
            part_name = f"{cap}FieldsPart{part_num:02d}"
            props = {name: schema for name, schema in fields[idx : idx + 64]}
            openapi["components"]["schemas"][part_name] = {
                "type": "object",
                "properties": props,
            }
            parts.append({"$ref": f"#/components/schemas/{part_name}"})
        openapi["components"]["schemas"][f"{cap}Fields"] = {"allOf": parts}
    else:
        openapi["components"]["schemas"][f"{cap}Fields"] = {
            "type": "object",
            "properties": {name: schema for name, schema in fields},
        }

    openapi["components"]["schemas"][f"{cap}ScanRequest"] = {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "query": {
                        "type": "object",
                        "properties": {
                            "types": {"type": "array", "items": {"type": "string"}}
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
        openapi["components"]["schemas"][f"{cap}{req}"] = {"type": "object"}
    for resp in ["SearchResponse", "HistoryResponse", "SummaryResponse"]:
        openapi["components"]["schemas"][f"{cap}{resp}"] = {"type": "object"}
    openapi["components"]["schemas"][f"{cap}MetainfoResponse"] = {
        "type": "object",
        "properties": {"fields": {"type": "array", "items": {"type": "string"}}},
    }

    def _add(path: str, req: str, resp: str) -> None:
        openapi["paths"][f"/{scope}/{path}"] = {
            "post": {
                "summary": f"{path.capitalize()} {scope}",
                "description": f"{path.capitalize()} {scope}",
                "operationId": f"{cap}{path.capitalize()}",
                "x-openai-isConsequential": False,
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{cap}{req}"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{cap}{resp}"}
                            }
                        },
                    },
                    "400": {"description": "Bad Request"},
                    "500": {"description": "Server Error"},
                },
            }
        }

    _add("scan", "ScanRequest", "ScanResponse")
    _add("search", "SearchRequest", "SearchResponse")
    _add("history", "HistoryRequest", "HistoryResponse")
    _add("summary", "SummaryRequest", "SummaryResponse")

    openapi["paths"][f"/{scope}/metainfo"] = {
        "post": {
            "summary": f"Get {scope} metainfo",
            "description": f"Get {scope} metainfo",
            "operationId": f"{cap}Metainfo",
            "x-openai-isConsequential": False,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{cap}MetainfoResponse"
                            }
                        }
                    },
                },
                "400": {"description": "Bad Request"},
                "500": {"description": "Server Error"},
            },
        }
    }

    yaml_str = yaml.safe_dump(openapi, sort_keys=False, Dumper=_IndentedDumper)
    if len(yaml_str.encode()) > max_size:
        raise RuntimeError("YAML size exceeds limit")
    print(yaml_str)
    return yaml_str
