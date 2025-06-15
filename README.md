# tv-generator

🧠 **tv-generator** — это CLI-инструмент для автоматической генерации OpenAPI 3.1 спецификаций на основе TradingView API `/scan` и `/metainfo`.

## 📦 Установка

```bash
git clone https://github.com/TrololoBird/tv-generator.git
cd tv-generator
pip install -e .[dev]
```

## 🚀 Быстрый старт

```bash
tvgen collect --market crypto
tvgen generate --market crypto --outdir specs
tvgen validate --spec specs/crypto.yaml
```

Однострочный пример: `tvgen generate --market crypto --outdir specs`

## 🛠️ CLI команды

- `build` - Collect data and generate specs for all markets.
- `build-all` - Collect data and generate specs for all markets.
- `bundle` - Bundle all specifications under ``specs/`` directory.
- `collect` - Fetch metainfo and scan results saving JSON and TSV.
- `debug` - Diagnose TradingView connectivity for the given market.
- `generate` - Generate OpenAPI YAML using collected JSON and TSV.
- `history` - Call /{market}/history with the given payload.
- `metainfo` - Fetch metainfo for given market via /{market}/metainfo.
- `preview` - Show table with fields, type, enum and description.
- `price` - Fetch last close price for a symbol.
- `recommend` - Fetch trading recommendation for a symbol.
- `scan` - Perform a basic scan request and print JSON.
- `search` - Call /{market}/search with the given payload.
- `summary` - Call /{market}/summary with the given payload.
- `validate` - Validate an OpenAPI specification file.

## 📁 Структура проекта

- `src/` — исходный код CLI и генератора
- `results/` — сохранённые ответы TradingView
- `specs/` — итоговые спецификации OpenAPI

## 🎯 Цель

Генерация OpenAPI 3.1 спецификаций на основе TradingView.


## Timeframe codes
```
1, 5, 15, 30, 60, 120, 240   -> minutes
1D                          -> 1 day
1W                          -> 1 week
```
