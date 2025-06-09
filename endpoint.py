import pandas as pd
import yaml
import requests
import json
from pathlib import Path

# === CONFIG ===
RESULTS_DIR = Path("C:/Users/undea/Downloads/results")  # папка с результатами сканов
OUTPUT_YAML = Path("C:/Users/undea/Downloads/openapi_generated.yaml")  # итоговый OpenAPI
OUTPUT_STATS = Path("C:/Users/undea/Downloads/market_stats.json")  # статистика по рынкам

# === HELPERS ===
def infer_type(value):
    """Определяет тип поля на основе примера значения."""
    if pd.isna(value):
        return "string"
    try:
        float(value)
        return "number"
    except ValueError:
        return "string"


def collect_market_fields(market_dir: Path):
    """Читает field_status.tsv и возвращает список полей и их типы."""
    df = pd.read_csv(market_dir / "field_status.tsv", sep="\t")
    df_ok = df[df["status"] == "ok"]
    fields = sorted(df_ok["field"].unique())
    types = {}
    for field in fields:
        vals = df_ok[df_ok["field"] == field]["value"].dropna()
        types[field] = infer_type(vals.iloc[0]) if not vals.empty else "string"
    return fields, types


def get_symbols_for_market(market: str):
    """Отправляет минимальный scan-запрос, возвращает список символов (s)."""
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {"symbols": {"query": {"types": []}}, "columns": ["s"], "range": [0, 1]}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.ok:
            return [row.get("s") for row in r.json().get("data", [])]
    except requests.RequestException:
        pass
    return []


def get_metainfo_for_market(market: str):
    """Запрашивает /metainfo для получения доступных полей и операторов."""
    url = f"https://scanner.tradingview.com/{market}/metainfo"
    try:
        r = requests.post(url, json={}, timeout=10)
        if r.ok:
            return r.json()
    except requests.RequestException:
        pass
    return {}

# === INITIALIZE OPENAPI ===
openapi = {
    "openapi": "3.1.0",
    "info": {
        "title": "Unofficial TradingView Scanner API",
        "version": "1.0.0",
        "description": "Auto-generated from live scan and metainfo endpoints."
    },
    "servers": [{"url": "https://scanner.tradingview.com"}],
    "paths": {},
    "components": {
        "securitySchemes": {
            "CookieAuth": {"type": "apiKey", "in": "cookie", "name": "auth_token"}
        },
        "requestBodies": {
            "ScanRequest": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ScanRequest"}}}
            }
        },
        "responses": {
            "ScanResponse": {"$ref": "#/components/responses/ScanResponse"},
            "ErrorResponse": {"$ref": "#/components/responses/ErrorResponse"}
        },
        "schemas": {
            "ScanRequest": {
                "type": "object",
                "properties": {
                    "symbols": {"type": "object", "properties": {"tickers": {"type": "array", "items": {"type": "string"}}, "query": {"type": "object", "properties": {"types": {"type": "array", "items": {"type": "string"}}}}}},
                    "filter": {"type": "array", "items": {"$ref": "#/components/schemas/Filter"}},
                    "columns": {"type": "array", "items": {"type": "string"}},
                    "sort": {"$ref": "#/components/schemas/Sort"},
                    "range": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer"}}
                },
                "required": ["columns"]
            },
            "ScanResponse": {
                "type": "object",
                "properties": {"totalCount": {"type": "integer"}, "data": {"type": "array", "items": {"type": "object", "properties": {"s": {"type": "string"}, "d": {"type": "array", "items": {"type": ["number","string"]}}}}}},
                "required": ["totalCount","data"]
            },
            "ErrorResponse": {"type": "object","properties": {"error": {"type": "string"},"totalCount": {"type": "integer"},"data": {"type": "null"}},"required": ["error","totalCount","data"]},
            "MetainfoResponse": {"type": "object","properties": {"columns": {"type": "array","items": {"type": "string"}},"filterFields": {"type": "array","items": {"type": "string"}},"operators": {"type": "array","items": {"type": "string"}}},"required": ["columns","filterFields"],}
        }
    }
}

# === PROCESS MARKETS ===
stats = []
for market_path in RESULTS_DIR.iterdir():
    if not market_path.is_dir():
        continue
    market = market_path.name
    field_file = market_path / "field_status.tsv"
    if not field_file.exists():
        print(f"Пропущено: {market}, нет field_status.tsv")
        continue

    # Собираем поля и типы
    fields, types = collect_market_fields(market_path)
    # Получаем тикеры
    symbols = get_symbols_for_market(market)
    # Запрашиваем метаинфо
    meta = get_metainfo_for_market(market)
    cols_meta = meta.get("columns", fields)
    filt_meta = meta.get("filterFields", fields)
    ops_meta = meta.get("operators", [">","<","=","!=","empty","nempty","contains"])

    # Генерируем пути
    scan_path = f"/{market}/scan"
    meta_path = f"/{market}/metainfo"
    openapi["paths"][scan_path] = {
        "post": {
            "summary": f"Scan {market.capitalize()} Market",
            "operationId": f"scan{market.capitalize()}",
            "requestBody": {"$ref": "#/components/requestBodies/ScanRequest"},
            "responses": {"200": {"$ref": "#/components/responses/ScanResponse"}, "400": {"$ref": "#/components/responses/ErrorResponse"}, "404": {"$ref": "#/components/responses/ErrorResponse"}, "500": {"$ref": "#/components/responses/ErrorResponse"}},
            "tags": [market]
        }
    }
    openapi["paths"][meta_path] = {
        "post": {
            "summary": f"Get {market.capitalize()} Metadata",
            "operationId": f"get{market.capitalize()}Metainfo",
            "responses": {
                "200": {"description": "Market metadata","content": {"application/json": {"schema": {"$ref": "#/components/schemas/MetainfoResponse"},"example": {"columns": cols_meta, "filterFields": filt_meta, "operators": ops_meta}}}},
                "400": {"$ref": "#/components/responses/ErrorResponse"},
                "404": {"$ref": "#/components/responses/ErrorResponse"},
                "500": {"$ref": "#/components/responses/ErrorResponse"}
            },
            "tags": [market]
        }
    }

    stats.append({"market": market, "fields": len(fields), "symbols": len(symbols)})
    print(f"{market}: fields={len(fields)}, symbols={len(symbols)}")

# === SAVE OUTPUTS ===
with open(OUTPUT_YAML, "w", encoding="utf-8") as f:
    yaml.dump(openapi, f, sort_keys=False, allow_unicode=True)

with open(OUTPUT_STATS, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(f"OpenAPI сгенерировано в {OUTPUT_YAML}")
print(f"Статистика сохранена в {OUTPUT_STATS}")
