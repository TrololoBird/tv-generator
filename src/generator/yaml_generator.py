from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING
import json
import re
import logging

import yaml

if TYPE_CHECKING:  # pragma: no cover - type checking only
    pass

from src.models import MetaInfoResponse, TVField, ScanResponse
from src.api.tradingview_api import TradingViewAPI
from src.utils.type_mapping import tv2ref
from src.meta.versioning import get_current_version
from src.utils.custom_patterns import _is_custom
from src.constants import GenerationMode
from src.utils.pathlib_ext import ensure_file, market_paths

logger = logging.getLogger(__name__)


def get_project_version() -> str:
    """Return project version from pyproject.toml."""

    return get_current_version()


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


_NUMERIC_TYPES = {
    "number",
    "price",
    "fundamental_price",
    "percent",
    "integer",
    "float",
    "duration",
    "percentage",
}


def classify_fields(columns: Dict[str, Dict[str, Any]]) -> Dict[str, list[str]]:
    """Return field classification mapping."""

    result: Dict[str, list[str]] = {
        "numeric": [],
        "string": [],
        "custom": [],
        "supports_timeframes": [],
        "daily_only": [],
        "discovered": [],
    }

    supports_tf: set[str] = set()

    for name, info in columns.items():
        base = name.split("|", 1)[0]
        ftype = str(info.get("tv_type") or info.get("type") or "")
        if ftype in _NUMERIC_TYPES:
            result["numeric"].append(base)
        else:
            result["string"].append(base)

        if _is_custom(base):
            result["custom"].append(base)

        if "|" in name:
            supports_tf.add(base)

        if str(info.get("source")) == "scan":
            result["discovered"].append(base)

    for base in result["numeric"]:
        if base in supports_tf:
            continue
        if re.fullmatch(r"[A-Z]+[A-Z0-9\[\]]*", base):
            result["daily_only"].append(base)

    result["supports_timeframes"] = sorted(supports_tf)
    for key in result:
        result[key] = sorted(set(result[key]))
    return result


def collect_field_schemas(
    meta: MetaInfoResponse, scan: dict[str, Any] | None
) -> tuple[list[tuple[str, Dict[str, Any]]], set[str], set[str]]:
    """Return field schemas and numeric field enums."""

    fields: list[tuple[str, Dict[str, Any]]] = []
    scan_rows = scan.get("data", []) if isinstance(scan, dict) else []
    no_tf_enum: set[str] = set()
    with_tf_enum: set[str] = set()
    for idx, field in enumerate(meta.fields):
        flags = set(field.flags or [])
        if {"deprecated", "private"} & flags:
            continue
        if field.n.lower() in {"symbol", "s"}:
            continue
        schema: Dict[str, Any] = {"$ref": tv2ref(field.t)}
        schema["description"] = _describe_field(field.n)

        base_name, _, _ = field.n.partition("|")
        if tv2ref(field.t).endswith("/Num"):
            if "|" in field.n:
                with_tf_enum.add(field.n)
            else:
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
    return fields, no_tf_enum, with_tf_enum


def build_components_schemas(
    cap: str,
    fields: list[tuple[str, Dict[str, Any]]],
    no_tf_enum: set[str],
    with_tf_enum: set[str],
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
        "enum": sorted(with_tf_enum),
        "pattern": rf"^[A-Za-z0-9_.\[\]]+\|({tf_pattern})$",
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

    paths[f"/{scope}/numeric"] = {
        "get": {
            "summary": f"Get numeric field for {scope}",
            "operationId": f"{cap}Numeric",
            "x-openai-isConsequential": False,
            "parameters": [
                {
                    "name": "symbol",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                },
                {
                    "name": "field",
                    "in": "query",
                    "required": True,
                    "schema": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/NumericFieldWithTimeframe"},
                            {"$ref": "#/components/schemas/NumericFieldNoTimeframe"},
                        ]
                    },
                },
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Num"}
                        }
                    },
                },
                "400": {"description": "Bad Request"},
                "500": {"description": "Server Error"},
            },
        }
    }

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
    api: TradingViewAPI | None = None,
    missing_fields: list[dict[str, str]] | None = None,
    description: str | None = None,
) -> str:
    """Return OpenAPI YAML specification for a scope."""

    cap = scope.capitalize()
    try:
        version = get_project_version()
    except RuntimeError as exc:  # pragma: no cover - fallback for installed package
        logger.warning("pyproject.toml missing: %s", exc)
        if not Path("pyproject.toml").exists():
            logger.warning("pyproject.toml file not found")
        try:
            from importlib.metadata import PackageNotFoundError, version as pkg_version

            version = pkg_version("tv-generator")
        except PackageNotFoundError:
            logger.warning("Package metadata not found; using default version")
            version = "0.0.0"

    fields, no_tf_enum, with_tf_enum = collect_field_schemas(meta, scan)
    components = build_components_schemas(cap, fields, no_tf_enum, with_tf_enum)
    if missing_fields:
        props = {}
        for item in missing_fields:
            t = item.get("type") or "string"
            tmap = {"numeric": "number", "boolean": "boolean", "string": "string"}
            props[item["name"]] = {
                "type": tmap.get(t, "string"),
                "description": "Auto-discovered field from TradingView scan.json",
            }
        components["MissingFields"] = {"type": "object", "properties": props}
    paths = build_paths_section(scope, cap)

    openapi: Dict[str, Any] = {
        "openapi": "3.1.0",
        "x-oai-custom-action-schema-version": "v1",
        "info": {
            "title": f"Unofficial TradingView {cap} API",
            "version": version,
            **({"description": description} if description else {}),
        },
        "servers": [{"url": server_url}],
        "paths": paths,
        "components": {"schemas": components},
    }

    yaml_str = yaml.dump(openapi, sort_keys=False, Dumper=_IndentedDumper)
    if len(yaml_str.encode()) > max_size:
        raise RuntimeError("YAML size exceeds limit")
    return yaml_str


def _load_market_data(
    meta_file: Path, scan_file: Path, status_file: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load TradingView JSON files for a market."""

    ensure_file(meta_file)
    ensure_file(scan_file)
    ensure_file(status_file)
    meta_data = json.loads(meta_file.read_text())
    scan_data = json.loads(scan_file.read_text())
    return meta_data, scan_data


def _parse_tv_fields(meta_data: dict[str, Any]) -> list[TVField]:
    """Convert metainfo JSON to a list of :class:`TVField`."""

    fields_json = (
        meta_data.get("fields") or meta_data.get("data", {}).get("fields") or []
    )
    tv_fields: list[TVField] = []
    for item in fields_json:
        if isinstance(item, dict):
            name = item.get("name") or item.get("id")
            if name is not None:
                tv_fields.append(
                    TVField.model_validate(
                        {"name": name, "type": item.get("type", "string")}
                    )
                )
    return tv_fields


def _extract_symbols(meta_data: dict[str, Any]) -> list[str]:
    """Return list of symbols from TradingView metadata."""

    symbols: list[str] = []
    body = meta_data.get("body") or meta_data.get("data", {})
    if isinstance(meta_data.get("symbols"), list):
        symbols = meta_data["symbols"]
    elif isinstance(body, dict):
        if isinstance(body.get("symbols"), list):
            symbols = body["symbols"]
        elif isinstance(body.get("index"), dict) and isinstance(
            body["index"].get("names"), list
        ):
            symbols = body["index"]["names"]
    if not symbols and isinstance(meta_data.get("index"), dict):
        names = meta_data["index"].get("names")
        if isinstance(names, list):
            symbols = names
    return symbols


def generate_for_market(
    market: str,
    indir: Path,
    outdir: Path,
    max_size: int = 1_048_576,
    api: TradingViewAPI | None = None,
    *,
    generation: GenerationMode = "default",
    include_missing: bool = False,
    include_types: tuple[str, ...] = (),
    exclude_types: tuple[str, ...] = (),
    only_timeframe_supported: bool = False,
    only_daily: bool = False,
) -> Path | None:
    """Generate YAML spec for ``market`` using data from ``indir``.

    Parameters
    ----------
    generation:
        Select generation behaviour. ``"include_missing"`` also processes
        missing fields.
    """

    indir.mkdir(parents=True, exist_ok=True)
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    include_missing = include_missing or generation == "include_missing"

    meta_file, scan_file, status_file = market_paths(indir, market)

    if not meta_file.exists():
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(json.dumps({"symbols": {}, "version": "mock"}))

    if not scan_file.exists():
        scan_file.write_text(json.dumps({"data": []}))

    if not status_file.exists():
        status_file.write_text("field\ttv_type\tstatus\tsample_value\n")

    meta_data, scan_data = _load_market_data(meta_file, scan_file, status_file)

    symbols = _extract_symbols(meta_data)

    if not symbols:
        logger.warning(
            "No symbols found in metainfo. Generation skipped for %s.", market
        )
        return None

    # Validate TradingView JSON
    MetaInfoResponse.parse_obj(meta_data)
    ScanResponse.parse_obj(scan_data)

    tv_fields = _parse_tv_fields(meta_data)

    meta = MetaInfoResponse(data=tv_fields)

    if api is None:
        api = TradingViewAPI()

    missing_fields = None
    if include_missing:
        from src.analyzer.scan_audit import find_missing_fields

        missing_fields = find_missing_fields(meta_file, scan_file, status_file)

    columns: dict[str, dict[str, Any]] = {f.n: {"type": f.t} for f in tv_fields}
    if missing_fields:
        for item in missing_fields:
            columns[item["name"]] = {
                "type": item.get("type", "string"),
                "source": item.get("source", "scan"),
            }

    classes = classify_fields(columns)

    def _keep(name: str) -> bool:
        base = name.split("|", 1)[0]
        if include_types and not any(base in classes.get(t, []) for t in include_types):
            return False
        if exclude_types and any(base in classes.get(t, []) for t in exclude_types):
            return False
        if only_timeframe_supported and base not in classes.get(
            "supports_timeframes", []
        ):
            return False
        if only_daily and base not in classes.get("daily_only", []):
            return False
        return True

    tv_fields = [f for f in tv_fields if _keep(f.n)]
    if missing_fields:
        missing_fields = [m for m in missing_fields if _keep(m["name"])]
    meta = MetaInfoResponse(data=tv_fields)

    desc_parts: list[str] = []
    if include_types:
        desc_parts.append("include=" + ",".join(include_types))
    if exclude_types:
        desc_parts.append("exclude=" + ",".join(exclude_types))
    if only_timeframe_supported:
        desc_parts.append("timeframe")
    if only_daily:
        desc_parts.append("daily")
    desc = "; ".join(desc_parts) if desc_parts else None

    yaml_str = generate_yaml(
        market,
        meta,
        scan_data,
        max_size=max_size,
        api=api,
        missing_fields=missing_fields,
        description=desc,
    )

    outdir.mkdir(parents=True, exist_ok=True)
    out_file = outdir / f"{market}.yaml"
    out_file.write_text(yaml_str)
    return out_file
