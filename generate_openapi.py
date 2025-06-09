# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
generate_openapi.py

Production OpenAPI 3.1.0 generator for TradingView Screener API.

Key features:
- All CLI args for file paths and server URL.
- English-only descriptions, tags, summary, and logging.
- Expanded TYPE_MAPPING, including 'time-yyyymmdd' and 'interface'.
- Per-field x-category and x-timeframe.
- Correct enum: only primitives; all complex enums as x-choices and in description.
- Clear handling and documentation for generic schemas.
- All errors, unknown types exported to openapi_generation_errors.json.
- Exports categories and timeframes for UI/automation.
"""

import argparse
import json
import logging
import sys
import traceback
import subprocess
import re
from pathlib import Path
import yaml
from collections import Counter, defaultdict

TYPE_MAPPING = {
    'text': {'type': 'string'},
    'number': {'type': 'number'},
    'price': {'type': 'number'},
    'percent': {'type': 'number'},
    'fundamental_price': {'type': 'number'},
    'time': {'type': 'string', 'format': 'date-time'},
    'bool': {'type': 'boolean'},
    'map': {'type': 'object', 'additionalProperties': True},
    'set': {'type': 'array', 'items': {'type': 'string'}},
    'num_slice': {'type': 'array', 'items': {'type': 'number'}},
    'time-yyyymmdd': {'type': 'string', 'format': 'date'},
    'interface': {'type': 'object'}
}
TIMEFRAME_MAP = {
    "1": "1 minute", "3": "3 minutes", "5": "5 minutes", "15": "15 minutes", "30": "30 minutes",
    "45": "45 minutes", "60": "1 hour", "120": "2 hours", "180": "3 hours", "240": "4 hours", "360": "6 hours",
    "480": "8 hours", "720": "12 hours", "D": "1 day", "W": "1 week", "M": "1 month", "Q": "1 quarter", "Y": "1 year"
}

def to_dict(obj):
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(v) for v in obj]
    return obj

def setup_logging(level):
    logger = logging.getLogger('generate_openapi')
    logger.setLevel(level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.handlers.clear()
    logger.addHandler(ch)
    fh = logging.FileHandler('generate_openapi.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
    return logger

def load_json_file(path: Path, logger, required=True):
    if not path.exists():
        msg = f"File is required but not found: {path}" if required else f"Optional file not found: {path} — skipping"
        (logger.error if required else logger.warning)(msg)
        if required:
            raise FileNotFoundError(f"File not found: {path}")
        return None
    logger.info(f"Loading JSON file: {path.name}")
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"Failed to load JSON {path}: {e}")
        raise

def validate_metainfo_structure(mi, logger, scope, errors):
    if not isinstance(mi, dict) or 'body' not in mi or 'fields' not in mi.get('body', {}):
        msg = f"Metainfo for {scope} missing 'body.fields' structure"
        logger.error(msg)
        errors.append(msg)
        return False
    for i, fld in enumerate(mi['body']['fields']):
        if not all(k in fld for k in ('n', 't', 'r')):
            msg = f"Metainfo field {i} in {scope} missing required keys (n, t, r): {fld}"
            logger.error(msg)
            errors.append(msg)
    return True

def infer_request_body_schema(requests_data, url_substr, logger, scope, generic_scopes):
    if not requests_data:
        logger.warning(f"No scanner_requests.json found — using generic object schema for {scope}")
        generic_scopes.add(scope)
        return {'type': 'object', 'description': "Generic schema: No POST sample found for this market. See metainfo for field structure."}
    for entry in requests_data:
        if entry.get('method', '').upper() == 'POST' and url_substr in entry.get('url', ''):
            body = entry.get('body')
            if isinstance(body, dict):
                schema = {'type': 'object', 'properties': {}, 'required': []}
                for key, val in body.items():
                    if isinstance(val, bool):   typ = 'boolean'
                    elif isinstance(val, int):  typ = 'integer'
                    elif isinstance(val, float):typ = 'number'
                    elif isinstance(val, str):  typ = 'string'
                    elif isinstance(val, list): schema['properties'][key] = {'type': 'array'}; schema['required'].append(key); continue
                    elif isinstance(val, dict): schema['properties'][key] = {'type': 'object'}; schema['required'].append(key); continue
                    else: typ = 'string'
                    schema['properties'][key] = {'type': typ}
                    schema['required'].append(key)
                logger.info(f"Inferred requestBody schema for endpoint {url_substr}")
                return schema
    logger.warning(f"No matching POST entries for {url_substr} — using generic object schema for {scope}")
    generic_scopes.add(scope)
    return {'type': 'object', 'description': "Generic schema: No POST sample found for this market. See metainfo for field structure."}

def get_example_from_scan(scan_path, logger):
    if not scan_path.exists():
        logger.warning(f"Scan example for {scan_path.name} not found.")
        return {}
    try:
        data = json.loads(scan_path.read_text(encoding='utf-8'))
        if "body" in data and "data" in data["body"]:
            example = {
                "totalCount": data["body"].get("totalCount", 1),
                "data": data["body"]["data"][:1]
            }
        elif "data" in data:
            example = {
                "totalCount": data.get("totalCount", 1),
                "data": data["data"][:1]
            }
        else:
            example = {}
        if example:
            logger.info(f"Example found in scan data: {scan_path.name}")
        else:
            logger.warning(f"No data array in {scan_path.name}, example not included.")
        return example
    except Exception as e:
        logger.warning(f"Error parsing example from {scan_path.name}: {e}")
        return {}

def get_field_category(field_name):
    if field_name.startswith(('close', 'open', 'high', 'low', 'volume', 'value', 'VWAP')):
        return "Price/Volume"
    if field_name.startswith(('RSI', 'Stoch', 'CCI', 'UO', 'WilliamsR', 'AO', 'Momentum', 'StochRSI')):
        return "Oscillators"
    if field_name.startswith(('MACD', 'EMA', 'SMA', 'WMA', 'HullMA', 'Ichimoku', 'DMI', 'ADX')):
        return "Trend"
    if field_name.startswith(('Pivot', 'PivotHL', 'PivotsHL')):
        return "Pivots"
    if field_name.startswith(('Dividends', 'earnings_', 'dividend_', 'revenue_', 'profit_', 'pe_ratio', 'beta', 'market_cap')):
        return "Fundamentals"
    if "earnings" in field_name or "dividend" in field_name:
        return "Fundamentals"
    if 'candlestick' in field_name or field_name.startswith('Pattern.'):
        return "Patterns"
    return "Other"

def parse_field_timeframe(field_name):
    m = re.match(r"^([A-Za-z0-9_.]+)\|([A-Za-z0-9]+)$", field_name)
    if m:
        return m.group(1), m.group(2)
    else:
        return field_name, None

def get_timeframe_description(tf):
    if tf is None:
        return "daily timeframe (1D, default)"
    return TIMEFRAME_MAP.get(tf, f"{tf} timeframe")

def get_indicator_human_name(name):
    mapping = {
        "RSI": "Relative Strength Index (RSI)",
        "MACD.macd": "MACD (macd line)",
        "MACD.signal": "MACD (signal line)",
        "MACD.histogram": "MACD (histogram)",
        "SMA": "Simple Moving Average (SMA)",
        "EMA": "Exponential Moving Average (EMA)",
        "Stoch.K": "Stochastic Oscillator %K",
        "Stoch.D": "Stochastic Oscillator %D",
    }
    return mapping.get(name, name)

def validate_openapi_yaml(yaml_path, logger):
    try:
        subprocess.run(["swagger-cli", "validate", str(yaml_path)], check=True)
        logger.info("OpenAPI YAML validated successfully with swagger-cli.")
    except Exception as e:
        logger.warning("swagger-cli not found or validation failed. "
                       f"To validate manually, run: npx swagger-cli validate {yaml_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate OpenAPI 3.1.0 spec for TradingView Screener API")
    parser.add_argument('--discovered-all', type=Path, default=Path('discovered_all.json'), help="Path to discovered_all.json")
    parser.add_argument('--scanner-requests', type=Path, default=Path('scanner_requests.json'), help="Path to scanner_requests.json")
    parser.add_argument('--root-health', type=Path, default=Path('root_health.json'), help="Path to root_health.json")
    parser.add_argument('--output', '-o', type=Path, default=Path('tradingview_screener_openapi.yaml'), help="Output YAML file path")
    parser.add_argument('--server-url', default='https://scanner.tradingview.com', help="Server URL")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="Logging level")
    args = parser.parse_args()

    logger = setup_logging(getattr(logging, args.log_level))
    logger.info("=== Starting OpenAPI specification generation ===")

    errors = []
    metainfo_cache = {}
    def get_metainfo(scope):
        if scope in metainfo_cache:
            return metainfo_cache[scope]
        mi_path = Path(f"{scope}_metainfo.json")
        mi = load_json_file(mi_path, logger)
        metainfo_cache[scope] = mi
        return mi

    discovered = load_json_file(args.discovered_all, logger)
    scopes = sorted({e['scope'] for e in discovered if e['endpoint'] in ('scan', 'metainfo')})
    logger.info(f"Scopes: {scopes}")

    requests_data = load_json_file(args.scanner_requests, logger, required=False)
    health_data = load_json_file(args.root_health, logger, required=False)

    components_schemas = {}
    cat_counter = Counter()
    tf_counter = Counter()
    generic_scopes = set()
    fields_with_tf = 0
    fields_without_tf = 0
    categories_export = defaultdict(list)
    timeframes_export = defaultdict(list)
    unknown_types = set()

    components_schemas['MetaInfoResponse'] = {
        'type': 'object',
        'required': ['financial_currency', 'fields'],
        'properties': {
            'financial_currency': {'type': ['string', 'null']},
            'fields': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'required': ['n', 't', 'r'],
                    'properties': {
                        'n': {'type': 'string'},
                        't': {'type': 'string'},
                        'r': {'anyOf': [{'type': 'array', 'items': {}}, {'type': 'null'}]}
                    }
                }
            }
        }
    }
    components_schemas['ScanResponse'] = {
        'type': 'object',
        'required': ['totalCount', 'data'],
        'properties': {
            'totalCount': {'type': 'integer'},
            'data': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'required': ['s', 'd'],
                    'properties': {
                        's': {'type': 'string'},
                        'd': {'type': 'array', 'items': {}}
                    }
                }
            }
        }
    }
    components_schemas['ErrorResponse'] = {
        'type': 'object',
        'required': ['error'],
        'properties': {'error': {'type': 'string'}}
    }

    for scope in scopes:
        mi = get_metainfo(scope)
        if not validate_metainfo_structure(mi, logger, scope, errors):
            continue
        for fld in mi['body']['fields']:
            name = fld['n']
            if name in components_schemas:
                continue
            base_schema = TYPE_MAPPING.get(fld['t'])
            if not base_schema:
                msg = f"Unknown field type '{fld['t']}' for field '{name}'; defaulting to string"
                logger.warning(msg)
                errors.append(msg)
                base_schema = {'type': 'string', 'description': f"Original type: {fld['t']}"}
                unknown_types.add(fld['t'])
            else:
                base_schema = base_schema.copy()

            # --- ВАЖНО: исправленный блок для enum/complex r ---
            if fld.get('r') is not None:
                enum_vals = fld['r']
                # Enum only for primitives
                if all(isinstance(x, (str, int, float, bool, type(None))) for x in enum_vals):
                    base_schema['enum'] = enum_vals
                # List of dicts — only x-choices and description
                elif isinstance(enum_vals, list) and all(isinstance(x, dict) for x in enum_vals):
                    base_schema['x-choices'] = enum_vals
                    base_schema['description'] = base_schema.get('description', '')
                    base_schema['description'] += (
                        "\n\nPossible values (id-name pairs):\n" +
                        "\n".join([f"- {item.get('id', '')}: {item.get('name', '')}" for item in enum_vals])
                    )
                else:
                    base_schema['description'] = base_schema.get('description', '')
                    base_schema['description'] += "\n\nField allows multiple complex values. See metainfo."
            # --- END ВАЖНОГО блока ---

            base, tf = parse_field_timeframe(name)
            human_name = get_indicator_human_name(base)
            if tf:
                tf_str = get_timeframe_description(tf)
                base_schema['x-timeframe'] = tf
                desc = f"{human_name} for {tf_str}."
                fields_with_tf += 1
                tf_counter[tf_str] += 1
                timeframes_export[tf_str].append(name)
            else:
                base_schema['x-timeframe'] = '1D'
                desc = f"{human_name} for daily timeframe (1D, default)."
                fields_without_tf += 1
                tf_counter['1D'] += 1
                timeframes_export['1D'].append(name)
            base_schema['description'] = desc + (("\n" + base_schema['description']) if 'description' in base_schema and base_schema['description'] else "")
            category = get_field_category(base)
            base_schema['x-category'] = category
            cat_counter[category] += 1
            categories_export[category].append(name)

            if logger.level <= logging.DEBUG:
                logger.debug(f"[Field] {name}: x-category={category}, x-timeframe={base_schema['x-timeframe']}, desc={desc}")

            components_schemas[name] = base_schema

    common_responses = {
        'BadRequest': {
            'description': 'Malformed or invalid request',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                                             'examples': {'error': {'value': {'error': 'Invalid request'}}}}}
        },
        'Unauthorized': {
            'description': 'Authentication required or invalid credentials',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                                             'examples': {'error': {'value': {'error': 'Unauthorized'}}}}}
        },
        'NotFound': {
            'description': 'Resource not found',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                                             'examples': {'error': {'value': {'error': 'Not found'}}}}}
        },
        'TooManyRequests': {
            'description': 'Rate limit exceeded',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                                             'examples': {'error': {'value': {'error': 'Too many requests'}}}}}
        }
    }

    paths = {}
    if health_data is not None:
        paths['/health'] = {
            'post': {
                'tags': ['health'],
                'summary': 'API health check endpoint',
                'operationId': 'healthCheck',
                'responses': {'200': {'description': 'Service is available'}}
            }
        }

    for scope in scopes:
        scan_example = get_example_from_scan(Path(f"{scope}_scan.json"), logger)
        try:
            mi = get_metainfo(scope)
            metainfo_example = mi.get('body', {}) if mi else None
        except Exception:
            metainfo_example = None

        schema = infer_request_body_schema(requests_data, f"/{scope}/scan", logger, scope, generic_scopes)
        scan_path = f'/{scope}/scan'
        metainfo_path = f'/{scope}/metainfo'

        scan_resp = {
            'tags': ['scan'],
            'summary': f'Instrument scan for {scope}',
            'description': (
                f"Runs the TradingView scan operation for the {scope} market. "
                "If the requestBody schema is generic, no POST sample was found for this market. "
                "Refer to metainfo for full field details."
            ),
            'operationId': f'scan_{scope}',
            'parameters': [{
                'name': 'scope',
                'in': 'path',
                'required': True,
                'schema': {'type': 'string', 'enum': scopes},
                'description': 'Market scope'
            }],
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {
                        'schema': schema,
                        'examples': {'example': {'value': scan_example}} if scan_example else {}
                    }
                }
            },
            'responses': {
                '200': {
                    'description': 'Scan results',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ScanResponse'},
                            'examples': {'example': {'value': scan_example}} if scan_example else {}
                        }
                    }
                },
                **{code: {'$ref': f"#/components/responses/{code}"} for code in common_responses}
            }
        }
        paths[scan_path] = {'post': scan_resp}

        metainfo_resp = {
            'tags': ['metainfo'],
            'summary': f'Market metainfo for {scope}',
            'description': f'Returns all available fields and definitions for the {scope} market.',
            'operationId': f'metainfo_{scope}',
            'parameters': [{
                'name': 'scope',
                'in': 'path',
                'required': True,
                'schema': {'type': 'string', 'enum': scopes},
                'description': 'Market scope'
            }],
            'requestBody': {
                'required': True,
                'content': {'application/json': {'schema': {'type': 'object'}}}
            },
            'responses': {
                '200': {
                    'description': 'Field metadata',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/MetaInfoResponse'},
                            'examples': {'example': {'value': metainfo_example}} if metainfo_example else {}
                        }
                    }
                },
                **{code: {'$ref': f"#/components/responses/{code}"} for code in common_responses}
            }
        }
        paths[metainfo_path] = {'post': metainfo_resp}

    info_desc = (
        "Auto-generated OpenAPI 3.1.0 specification for all TradingView markets.\n"
        "Field names in the API follow this pattern:\n"
        "  - If the field name includes a suffix (e.g. 'RSI|5'), the suffix denotes the timeframe ('5' means '5-minute').\n"
        "  - If there is no suffix (e.g. 'RSI'), it is always daily timeframe (1D, default).\n"
        "  - Example: 'RSI|15' means RSI for 15-minute candles, 'RSI' means RSI for daily (1D) candles.\n"
        "  - All fields have an 'x-category' (custom grouping) and 'x-timeframe' for UI/automation.\n"
        "  - This documentation is fully English for maximum compatibility with Custom GPTs and Swagger tools."
    )

    spec = {
        'openapi': '3.1.0',
        'info': {
            'title': 'TradingView Screener API',
            'version': '1.0.0',
            'description': info_desc,
        },
        'servers': [{'url': args.server_url}],
        'tags': [
            {'name': 'scan', 'description': 'Retrieve instrument lists using market scan'},
            {'name': 'metainfo', 'description': 'Retrieve all available market fields and metadata'},
            {'name': 'health', 'description': 'API health check'}
        ],
        'paths': paths,
        'components': {
            'schemas': components_schemas,
            'responses': common_responses,
            'securitySchemes': {'CookieAuth': {'type': 'apiKey', 'in': 'cookie', 'name': 'sessionid'}}
        },
        'security': [{'CookieAuth': []}]
    }

    out_path = args.output
    try:
        with out_path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(to_dict(spec), f, sort_keys=False, allow_unicode=True)
        logger.info(f"OpenAPI spec generated: {out_path.resolve()}")
        print(f"\n✅ OpenAPI spec saved: {out_path.resolve()}\n")
    except Exception as e:
        logger.error(f"YAML serialization error: {e}")
        logger.error(traceback.format_exc())
        print("\n❌ YAML serialization error. This usually means the schema is too large or has invalid content. Check generate_openapi.log for details and try running with a smaller dataset or fixing the data structure.\n")

    validate_openapi_yaml(out_path, logger)

    # Export categories, timeframes, errors to JSON
    with open('field_categories.json', 'w', encoding='utf-8') as fc:
        json.dump({k: v for k, v in categories_export.items()}, fc, indent=2)
    logger.info("field_categories.json exported.")
    with open('field_timeframes.json', 'w', encoding='utf-8') as tf:
        json.dump({k: v for k, v in timeframes_export.items()}, tf, indent=2)
    logger.info("field_timeframes.json exported.")
    if errors or unknown_types:
        with open('openapi_generation_errors.json', 'w', encoding='utf-8') as ef:
            json.dump({"errors": errors, "unknown_types": sorted(list(unknown_types))}, ef, indent=2)
        logger.warning(f"openapi_generation_errors.json exported with {len(errors)} errors and {len(unknown_types)} unknown field types.")

    # Final summary statistics
    logger.info(f"--- Final Summary ---")
    logger.info(f"Total unique fields: {len(components_schemas)}")
    logger.info(f"Fields with timeframe: {fields_with_tf}")
    logger.info(f"Fields without timeframe (daily/1D): {fields_without_tf}")
    logger.info("Fields by category: " + ', '.join(f"{k}={v}" for k, v in cat_counter.items()))
    logger.info("Fields by timeframe: " + ', '.join(f"{k}={v}" for k, v in tf_counter.items()))
    if generic_scopes:
        logger.warning(f"Generic schemas used for scopes: {', '.join(sorted(generic_scopes))}")
    else:
        logger.info("No generic schemas used; POST samples were found for all scopes.")

    if logger.level <= logging.DEBUG:
        logger.debug("--- Top 10 categories ---")
        for k, v in cat_counter.most_common(10):
            logger.debug(f"Category {k}: {v}")
        logger.debug("--- Top 10 timeframes ---")
        for k, v in tf_counter.most_common(10):
            logger.debug(f"Timeframe {k}: {v}")

    print("\nSUMMARY:")
    print(f"  Total fields: {len(components_schemas)}")
    print(f"  Fields with timeframe: {fields_with_tf}")
    print(f"  Fields without timeframe (daily/1D): {fields_without_tf}")
    print("  By category: " + ', '.join(f"{k}={v}" for k, v in cat_counter.items()))
    print("  By timeframe: " + ', '.join(f"{k}={v}" for k, v in tf_counter.items()))
    if generic_scopes:
        print(f"  Generic schemas used for: {', '.join(sorted(generic_scopes))}")
        print("  See log and openapi_generation_errors.json for details.")
    if errors:
        print(f"  ERRORS detected: see openapi_generation_errors.json")

if __name__ == '__main__':
    main()
