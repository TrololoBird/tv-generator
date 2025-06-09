import pandas as pd
import yaml
from pathlib import Path

# === CONFIG ===
RESULTS_DIR = Path("C:/Users/undea/Downloads/results")
OUTPUT_YAML = Path("C:/Users/undea/Downloads/openapi_generated.yaml")

# === HELPER FUNCTIONS ===
def infer_type(value):
    if pd.isna(value):
        return "string"
    try:
        float(value)
        return "number"
    except ValueError:
        return "string"

def collect_market_fields(market_dir: Path):
    df = pd.read_csv(market_dir / "field_status.tsv", sep="\t")
    df_ok = df[df["status"] == "ok"]
    fields = sorted(set(df_ok["field"]))

    field_types = {}
    for field in fields:
        val_series = df_ok[df_ok["field"] == field]["value"].dropna()
        if not val_series.empty:
            field_types[field] = infer_type(val_series.iloc[0])
        else:
            field_types[field] = "string"
    return fields, field_types

def generate_path_entries(market):
    return {
        f"/{market}/scan": {
            "post": {
                "summary": f"Scan {market.capitalize()} Market",
                "operationId": f"scan{market.capitalize()}",
                "requestBody": {"$ref": "#/components/requestBodies/ScanRequest"},
                "responses": {
                    "200": {"$ref": "#/components/responses/ScanResponse"},
                    "400": {"$ref": "#/components/responses/ErrorResponse"},
                    "404": {"$ref": "#/components/responses/ErrorResponse"},
                    "500": {"$ref": "#/components/responses/ErrorResponse"}
                },
                "tags": [market]
            }
        },
        f"/{market}/metainfo": {
            "post": {
                "summary": f"Get {market.capitalize()} Metadata",
                "operationId": f"get{market.capitalize()}Metainfo",
                "responses": {
                    "200": {"$ref": "#/components/responses/MetainfoResponse"},
                    "400": {"$ref": "#/components/responses/ErrorResponse"},
                    "404": {"$ref": "#/components/responses/ErrorResponse"},
                    "500": {"$ref": "#/components/responses/ErrorResponse"}
                },
                "tags": [market]
            }
        }
    }

# === MAIN ===
openapi = {
    "openapi": "3.1.0",
    "info": {
        "title": "Unofficial TradingView Scanner API",
        "version": "1.0.0",
        "description": "Auto-generated from collected field data across markets."
    },
    "servers": [{"url": "https://scanner.tradingview.com"}],
    "paths": {},
    "components": {
        "securitySchemes": {
            "CookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "auth_token"
            }
        },
        "requestBodies": {
            "ScanRequest": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
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
                                            }
                                        }
                                    }
                                },
                                "filter": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Filter"}
                                },
                                "columns": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "sort": {"$ref": "#/components/schemas/Sort"},
                                "range": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {"type": "integer"}
                                }
                            },
                            "required": ["columns"]
                        },
                        "example": {
                            "columns": ["close", "volume", "RSI|14"],
                            "filter": [{"left": "RSI|14", "operation": ">", "right": 50}],
                            "sort": {"sortBy": "volume", "sortOrder": "desc"},
                            "range": [0, 10]
                        }
                    }
                }
            }
        },
        "responses": {
            "ScanResponse": {
                "description": "Successful scan result",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "totalCount": {"type": "integer"},
                                "data": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "s": {"type": "string"},
                                            "d": {"type": "array", "items": {"type": ["number", "string"]}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "ErrorResponse": {
                "description": "Error response",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "data": {"type": "null"},
                                "totalCount": {"type": "integer"}
                            }
                        }
                    }
                }
            },
            "MetainfoResponse": {
                "description": "Metadata about available fields",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "columns": {"type": "array", "items": {"type": "string"}},
                                "filterFields": {"type": "array", "items": {"type": "string"}},
                                "operators": {"type": "array", "items": {"type": "string"}}
                            },
                            "example": {
                                "columns": ["close", "volume", "RSI|14"],
                                "filterFields": ["close", "volume", "RSI|14"],
                                "operators": [">", "<", "=", "!=", "empty", "nempty", "contains"]
                            }
                        }
                    }
                }
            }
        },
        "schemas": {
            "Filter": {
                "type": "object",
                "properties": {
                    "left": {"type": "string"},
                    "operation": {"type": "string"},
                    "right": {"type": ["number", "string"]}
                },
                "required": ["left", "operation"]
            },
            "Sort": {
                "type": "object",
                "properties": {
                    "sortBy": {"type": "string"},
                    "sortOrder": {"type": "string", "enum": ["asc", "desc"]}
                },
                "required": ["sortBy", "sortOrder"]
            }
        }
    }
}

# Обход всех рынков и добавление путей и примеров в responses
for market_path in RESULTS_DIR.iterdir():
    if not market_path.is_dir():
        continue
    market = market_path.name
    field_file = market_path / "field_status.tsv"
    if not field_file.exists():
        print(f"Пропущено: {market} (нет field_status.tsv)")
        continue
    columns, types = collect_market_fields(market_path)
    openapi["paths"].update(generate_path_entries(market))
    openapi["components"]["responses"]["MetainfoResponse"]["content"]["application/json"]["schema"]["example"] = {
        "columns": columns[:10],
        "filterFields": columns[:10],
        "operators": [">", "<", "=", "!=", "empty", "nempty", "contains"]
    }

# Сохранение YAML
with open(OUTPUT_YAML, "w") as f:
    yaml.dump(openapi, f, sort_keys=False)

print(f"OpenAPI спецификация сгенерирована: {OUTPUT_YAML}")
