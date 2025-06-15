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

Однострочный пример: `tvgen generate --market crypto --outdir specs`

## 🛠️ CLI команды

- `audit-missing-fields` - Show fields present in scan.json but missing from metainfo.
- `build` - Collect data and generate specs for all markets.
- `build-all` - Collect data and generate specs for all markets.
- `bump-version` - Increment project version.
- `bundle` - Bundle all specifications under ``specs/`` directory.
- `changelog` - Generate CHANGELOG from git history.
- `collect` - Fetch metainfo and scan results saving JSON and TSV.
- `debug` - Diagnose TradingView connectivity for the given market.
- `diff` - Compare results with cached versions.
- `docs` - Generate README file with CLI command list.
- `generate` - Generate OpenAPI YAML using collected JSON and TSV.
- `generate-if-needed` - Generate specs only when diff finds changes.
- `history` - Call /{market}/history with the given payload.
- `list-fields` - List fields grouped by classification.
- `metainfo` - Fetch metainfo for given market via /{market}/metainfo.
- `preview` - Show table with fields, type, enum and description.
- `price` - Fetch last close price for a symbol.
- `publish-pages` - Publish YAML specs to GitHub Pages branch.
- `publish-release-assets` - Upload specs to GitHub release.
- `recommend` - Fetch trading recommendation for a symbol.
- `refresh` - Download latest data and update TSV files.
- `scan` - Perform a basic scan request and print JSON.
- `search` - Call /{market}/search with the given payload.
- `summary` - Call /{market}/summary with the given payload.
- `validate` - Validate an OpenAPI specification file.
- `version` - Show current package version.

## Публикация спецификаций

```bash
tvgen publish-pages --branch gh-pages
tvgen publish-release-assets --tag v1.0.48
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
