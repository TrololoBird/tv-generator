from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING, Iterable

import toml
import yaml

if TYPE_CHECKING:  # pragma: no cover - type checking only
    import pandas as pd

from src.models import MetaInfoResponse
from src.utils import tv2ref


class _IndentedDumper(yaml.SafeDumper):
    """YAML dumper that indents sequences properly."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, False)


def _timeframe_desc(value: str | int) -> str:
    """Return a human friendly timeframe description."""
    try:
        minutes = int(value)
    except Exception:
        return str(value)
    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days}-day" if days > 1 else "1-day"
    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours}-hour" if hours > 1 else "1-hour"
    return f"{minutes}-minute"


_INDICATOR_NAMES = {
    "RSI": "Relative Strength Index",
    "EMA": "Exponential Moving Average",
    "ADX+DI": "Average Directional Index + Directional Indicator",
}


def _indicator_name(raw: str) -> str:
    for key, val in _INDICATOR_NAMES.items():
        if raw.startswith(key):
            if key == "EMA" and raw != "EMA":
                period = raw[len("EMA") :]
                if period.isdigit():
                    return f"{val} ({period})"
            return val
    return raw.replace("_", " ").title()


def _describe_field(name: str) -> str:
    if "|" in name:
        base, tf = name.split("|", 1)
        return f"{_indicator_name(base)} on {_timeframe_desc(tf)} timeframe"
    return _indicator_name(name)


def generate_yaml(
    scope: str,
    meta: MetaInfoResponse,
    _tsv: "pd.DataFrame",
    scan: dict | None = None,
    server_url: str = "https://scanner.tradingview.com",
    max_size: int = 1_048_576,
) -> str:
    """Return OpenAPI YAML specification for a scope."""

    cap = scope.capitalize()
    root = Path(__file__).resolve().parents[2]
    version = toml.load(root / "pyproject.toml")["project"]["version"]

    fields: list[tuple[str, Dict[str, Any]]] = []
    scan_rows = scan.get("data", []) if isinstance(scan, dict) else []
    no_tf_enum: set[str] = set()
    for idx, field in enumerate(meta.fields):
        flags = set(field.flags or [])
        if {"deprecated", "private"} & flags:
            continue
        schema: Dict[str, Any] = {"$ref": tv2ref(field.t)}
        schema["description"] = _describe_field(field.n)

        base_name, _, tf = field.n.partition("|")
        if "|" in field.n and base_name in {"RSI", "EMA20"}:
            no_tf_enum.add(base_name)

        values: list[Any] = []
        for row in scan_rows:
            dval = row.get("d") if isinstance(row, dict) else None
            if isinstance(dval, list) and idx < len(dval):
                val = dval[idx]
                if val not in (None, ""):
                    values.append(val)
        unique_vals = sorted({v for v in values})
        if 1 < len(unique_vals) <= 10:
            schema["enum"] = unique_vals

        base_name = field.n.split("|", 1)[0]
        examples = {
            "RSI": 55,
            "EMA20": 50,
            "ADX+DI": 25,
        }
        for key, example in examples.items():
            if base_name.startswith(key):
                schema["example"] = example
                break

        fields.append((field.n, schema))

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
        "Array": {"type": "array", "items": {}},
    }
    for name, base_schema in base.items():
        openapi["components"]["schemas"].setdefault(name, base_schema)

    openapi["components"]["schemas"]["NumericFieldNoTimeframe"] = {
        "type": "string",
        "enum": sorted(no_tf_enum),
    }
    openapi["components"]["schemas"]["NumericFieldWithTimeframe"] = {
        "type": "string",
        "pattern": r"^[A-Z0-9_+\[\]]+\|(1|5|15|30|60|120|240|1D|1W)$",
    }

    if len(fields) > 64:
        parts = []
        for idx in range(0, len(fields), 64):
            part_num = idx // 64 + 1
            part_name = f"{cap}FieldsPart{part_num:02d}"
            props = {
                name: schema for name, schema in fields[idx : idx + 64]  # noqa: E203
            }
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
                "summary": f"{path.capitalize()} {scope} market data",
                "description": (
                    f"Send a {cap}{req} payload and receive a {cap}{resp}. "
                    f"The response contains fields defined in "
                    + f"#/components/schemas/{cap}Fields."
                ),
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
            "description": f"Returns the list of available fields for {scope}.",
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

    yaml_str = yaml.dump(openapi, sort_keys=False, Dumper=_IndentedDumper)
    if len(yaml_str.encode()) > max_size:
        raise RuntimeError("YAML size exceeds limit")
    return yaml_str
