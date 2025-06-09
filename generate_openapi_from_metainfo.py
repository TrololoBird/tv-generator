import json
import yaml
from pathlib import Path

def parse_field(field):
    """
    Генерация OpenAPI-схемы для одного поля metainfo.json
    """
    name = field['n']
    ftype = field['t']
    enum_values = field.get('r')
    schema = {}

    if ftype in ("number", "percent"):
        schema = {"type": "number"}
    elif ftype in ("price", "fundamental_price"):
        schema = {"type": "number"}
    elif ftype == "time":
        schema = {"type": "string", "format": "date-time"}
    elif ftype == "text":
        schema = {"type": "string"}
        if enum_values:
            schema["enum"] = enum_values
    elif ftype == "set":
        schema = {"type": "array", "items": {"type": "string"}}
        if enum_values:
            schema["items"]["enum"] = enum_values
    elif ftype == "map":
        schema = {"type": "object", "additionalProperties": True}
    else:
        schema = {"type": "string"}

    schema['description'] = f"Type: {ftype}"
    return name, schema, ftype, enum_values

def generate_fields_schema(fields):
    """
    Генерирует object-схему всех полей для OpenAPI
    Возвращает: schema, fields_info (dict: name -> {"type":..., "enum":...})
    """
    properties = {}
    fields_info = {}
    for field in fields:
        name, schema, ftype, enum_values = parse_field(field)
        properties[name] = schema
        fields_info[name] = {"type": ftype}
        if enum_values:
            fields_info[name]["enum"] = enum_values
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False
    }, fields_info

def generate_filter_schema(fields_info):
    """
    Генерирует схему фильтрации с автоподстановкой enum для right, если поле поддерживает enum
    """
    # Основная версия - generic (universal) для всех полей
    filter_schema = {
        "type": "object",
        "properties": {
            "left": {
                "type": "string",
                "description": "Field name (см. OpenAPI:CryptoField)"
            },
            "operation": {
                "type": "string",
                "enum": [
                    "equal", "not_equal", "greater", "less",
                    "greater_or_equal", "less_or_equal",
                    "contains", "not_contains"
                ]
            },
            "right": {
                "oneOf": [
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            }
        },
        "required": ["left", "operation", "right"]
    }
    return filter_schema

def build_openapi(fields, scope="crypto"):
    """
    Основной генератор OpenAPI для одного рынка (crypto/coin)
    """
    fields_schema, fields_info = generate_fields_schema(fields)

    openapi = {
        "openapi": "3.1.0",
        "info": {
            "title": f"TradingView Screener API ({scope.capitalize()})",
            "version": "1.1.0",
            "description": (
                f"Автоматически сгенерировано на основании {scope}_metainfo.json.\n"
                f"Полностью покрывает все типы и значения TradingView для {scope}."
            )
        },
        "servers": [{"url": "https://scanner.tradingview.com"}],
        "components": {
            "schemas": {
                f"{scope.capitalize()}Field": fields_schema,
                "Filter": generate_filter_schema(fields_info),
                "Sort": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "order": {"type": "string", "enum": ["asc", "desc"]}
                    },
                    "required": ["field", "order"]
                },
                "ScanRequest": {
                    "type": "object",
                    "properties": {
                        "markets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Markets for filter (optional, e.g. ['BINANCE', 'BYBIT'])"
                        },
                        "symbols": {
                            "type": "object",
                            "properties": {
                                "tickers": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of tickers (e.g. ['BINANCE:BTCUSDT'])"
                                }
                            },
                            "description": "Filter by exact tickers (optional)"
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "lang": {"type": "string", "description": "Response language, e.g. 'en', 'ru'"}
                            },
                            "description": "Optional additional parameters"
                        },
                        "filter": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Filter"},
                            "description": "Array of filter objects"
                        },
                        "sort": {"$ref": "#/components/schemas/Sort"},
                        "range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of output fields"
                        }
                    },
                    "required": ["filter", "sort", "range", "columns"]
                },
                "ScanResponse": {
                    "type": "object",
                    "properties": {
                        "totalCount": {"type": "integer"},
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "s": {"type": "string"},
                                    "d": {"type": "array", "items": {}}
                                }
                            }
                        }
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"}
                    }
                }
            }
        },
        "paths": {
            f"/{scope}/scan": {
                "post": {
                    "summary": f"Скринер {scope}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ScanRequest"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Scan result",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ScanResponse"}
                                }
                            }
                        },
                        "400": {
                            "description": "Bad request",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "429": {
                            "description": "Too Many Requests",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "500": {
                            "description": "Internal Server Error",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            },
            f"/{scope}/metainfo": {
                "post": {
                    "summary": f"Метаданные {scope}",
                    "responses": {
                        "200": {
                            "description": "Metainfo",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{scope.capitalize()}Field"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return openapi

def main():
    for scope, path in [("crypto", "crypto_metainfo.json"), ("coin", "coin_metainfo.json")]:
        if Path(path).exists():
            with open(path, encoding="utf-8") as f:
                meta = json.load(f)
            fields = meta["body"]["fields"] if "body" in meta and "fields" in meta["body"] else meta["fields"]
            openapi_spec = build_openapi(fields, scope=scope)
            with open(f"openapi_{scope}.yaml", "w", encoding="utf-8") as yf:
                yaml.dump(openapi_spec, yf, sort_keys=False, allow_unicode=True)
            print(f"Сгенерирован: openapi_{scope}.yaml")

if __name__ == "__main__":
    main()
