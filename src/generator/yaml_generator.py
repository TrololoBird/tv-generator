from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING
import re

import toml
import yaml

if TYPE_CHECKING:  # pragma: no cover - type checking only
    import pandas as pd

from src.models import MetaInfoResponse
from src.utils import tv2ref


def _supported_timeframes() -> list[str]:
    """Return list of supported timeframe codes parsed from README."""
    root = Path(__file__).resolve().parents[2]
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    match = re.search(r"Timeframe codes.*?```(.*?)```", text, re.S)
    frames: list[str] = []
    if match:
        block = match.group(1)
        for line in block.strip().splitlines():
            left = line.split("->", 1)[0].strip()
            for token in left.split(","):
                token = token.strip()
                if token:
                    frames.append(token)
    if not frames:
        frames = ["1", "5", "15", "30", "60", "120", "240", "1D", "1W"]
    return frames


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
                period = raw[len("EMA") :]  # noqa: E203
                if period.isdigit():
                    return f"{val} ({period})"
            return val
    return raw.replace("_", " ").title()


def _describe_field(name: str) -> str:
    if "|" in name:
        base, tf = name.split("|", 1)
        return f"{_indicator_name(base)} on {_timeframe_desc(tf)} timeframe"
    return _indicator_name(name)


def collect_field_schemas(
    meta: MetaInfoResponse, scan: dict[str, Any] | None
) -> tuple[list[tuple[str, Dict[str, Any]]], set[str]]:
    """Return field schemas and numeric fields without timeframe."""

    fields: list[tuple[str, Dict[str, Any]]] = []
    scan_rows = scan.get("data", []) if isinstance(scan, dict) else []
    no_tf_enum: set[str] = set()
    for idx, field in enumerate(meta.fields):
        flags = set(field.flags or [])
        if {"deprecated", "private"} & flags:
            continue
        if field.n.lower() in {"symbol", "s"}:
            continue
        schema: Dict[str, Any] = {"$ref": tv2ref(field.t)}
        schema["description"] = _describe_field(field.n)

        base_name, _, _ = field.n.partition("|")
        if "|" not in field.n and tv2ref(field.t).endswith("/Num"):
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
    return fields, no_tf_enum


def build_components_schemas(
    cap: str, fields: list[tuple[str, Dict[str, Any]]], no_tf_enum: set[str]
) -> Dict[str, Any]:
    """Return OpenAPI components schemas section."""

    components: Dict[str, Any] = {}

    base = {
        "Num": {"type": "number"},
        "Str": {"type": "string"},
        "Bool": {"type": "boolean"},
        "Time": {"type": "string", "format": "date-time"},
        "Array": {"type": "array", "items": {}},
    }
    for name, base_schema in base.items():
        components.setdefault(name, base_schema)

    components["NumericFieldNoTimeframe"] = {
        "type": "string",
        "enum": sorted(no_tf_enum),
    }
    timeframes = _supported_timeframes()
    tf_pattern = "|".join(map(re.escape, timeframes))
    components["NumericFieldWithTimeframe"] = {
        "type": "string",
        "pattern": rf"^[A-Z0-9_+\[\]]+\|({tf_pattern})$",
    }

    if len(fields) > 64:
        parts = []
        for idx in range(0, len(fields), 64):
            part_num = idx // 64 + 1
            part_name = f"{cap}FieldsPart{part_num:02d}"
            props = {
                name: schema for name, schema in fields[idx : idx + 64]  # noqa: E203
            }
            components[part_name] = {"type": "object", "properties": props}
            parts.append({"$ref": f"#/components/schemas/{part_name}"})
        components[f"{cap}Fields"] = {"allOf": parts}
    else:
        components[f"{cap}Fields"] = {
            "type": "object",
            "properties": {name: schema for name, schema in fields},
        }

    components[f"{cap}ScanRequest"] = {
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
    components[f"{cap}ScanResponse"] = {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{cap}Fields"},
            }
        },
    }

    for req in ["SearchRequest", "HistoryRequest", "SummaryRequest"]:
        components[f"{cap}{req}"] = {"type": "object"}
    for resp in ["SearchResponse", "HistoryResponse", "SummaryResponse"]:
        components[f"{cap}{resp}"] = {"type": "object"}
    components[f"{cap}MetainfoResponse"] = {
        "type": "object",
        "properties": {"fields": {"type": "array", "items": {"type": "string"}}},
    }

    return components


def build_paths_section(scope: str, cap: str) -> Dict[str, Any]:
    """Return OpenAPI paths section for the given scope."""

    paths: Dict[str, Any] = {}

    def _add(path: str, req: str, resp: str) -> None:
        paths[f"/{scope}/{path}"] = {
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

    paths[f"/{scope}/metainfo"] = {
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

    return paths


def generate_yaml(
    scope: str,
    meta: MetaInfoResponse,
    scan: dict[str, Any] | None = None,
    server_url: str = "https://scanner.tradingview.com",
    max_size: int = 1_048_576,
) -> str:
    """Return OpenAPI YAML specification for a scope."""

    cap = scope.capitalize()
    root = Path(__file__).resolve().parents[2]
    try:
        version = toml.load(root / "pyproject.toml")["project"]["version"]
    except FileNotFoundError:  # pragma: no cover - fallback for installed package
        try:
            from importlib.metadata import PackageNotFoundError, version as pkg_version

            version = pkg_version("tv-generator")
        except PackageNotFoundError:  # pragma: no cover - dev environment
            version = "0.0.0"

    fields, no_tf_enum = collect_field_schemas(meta, scan)
    components = build_components_schemas(cap, fields, no_tf_enum)
    paths = build_paths_section(scope, cap)

    openapi: Dict[str, Any] = {
        "openapi": "3.1.0",
        "x-oai-custom-action-schema-version": "v1",
        "info": {
            "title": f"Unofficial TradingView {cap} API",
            "version": version,
        },
        "servers": [{"url": server_url}],
        "paths": paths,
        "components": {"schemas": components},
    }

    yaml_str = yaml.dump(openapi, sort_keys=False, Dumper=_IndentedDumper)
    if len(yaml_str.encode()) > max_size:
        raise RuntimeError("YAML size exceeds limit")
    return yaml_str
