# tv-generator

🧠 **tv-generator** — это CLI-инструмент для автоматической генерации OpenAPI 3.1 спецификаций на основе TradingView API `/scan` и `/metainfo`.

🔗 Онлайн OpenAPI: [crypto.yaml](https://trololobird.github.io/tv-generator/specs/crypto.yaml)

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

If `results/<market>/metainfo.json` is missing, a mock file will be created and
generation will be skipped with a warning.

Однострочный пример: `tvgen generate --market crypto --outdir specs`

## 🛠️ CLI команды

- `build` - Collect data and generate specs for all markets.
- `bump-version` - Increment project version.
- `bundle` - Bundle all specifications under ``specs/`` directory.
- `changelog` - Generate CHANGELOG from git history.
- `collect` - Fetch metainfo and scan results saving JSON and TSV.
- `generate` - Generate OpenAPI YAML using collected JSON and TSV.
- `metainfo` - Fetch metainfo for given market via /{market}/metainfo.
- `preview` - Show table with fields, type, enum and description.
- `scan` - Perform a basic scan request and print JSON.
- `update` - Update data, optionally diff and generate specs.
- `validate` - Validate an OpenAPI specification file.
- `version` - Show current package version.

## Публикация спецификаций

```bash
python .github/scripts/publish_pages.py --branch gh-pages
```

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
