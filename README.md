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
- `refresh` - Update metainfo, scan.json and field_status.tsv for markets.
- `diff` - Compare results with cached versions.
- `debug` - Diagnose TradingView connectivity for the given market.
- `changelog` - Generate `CHANGELOG.md` from git history.
- `generate` - Generate OpenAPI YAML using collected JSON and TSV.
- `version` - Print current project version.
- `bump-version` - Increment version in `pyproject.toml`.
- `history` - Call /{market}/history with the given payload.
- `metainfo` - Fetch metainfo for given market via /{market}/metainfo.
- `preview` - Show table with fields, type, enum and description.
- `price` - Fetch last close price for a symbol.
- `recommend` - Fetch trading recommendation for a symbol.
- `scan` - Perform a basic scan request and print JSON.
- `search` - Call /{market}/search with the given payload.
- `summary` - Call /{market}/summary with the given payload.
- `validate` - Validate an OpenAPI specification file.

Use `refresh` to ensure the latest TradingView data is saved before running
`generate`. It overwrites existing JSON files for the chosen markets.

## 📁 Структура проекта

- `src/` — исходный код CLI и генератора
- `results/` — сохранённые ответы TradingView
- `specs/` — итоговые спецификации OpenAPI

CI автоматически добавляет `CHANGELOG.md` в артефакты релиза и вызывает
`tvgen changelog` перед загрузкой спецификаций.

## 🎯 Цель

Генерация OpenAPI 3.1 спецификаций на основе TradingView.


## Timeframe codes
```
1, 5, 15, 30, 60, 120, 240   -> minutes
1D                          -> 1 day
1W                          -> 1 week
```

## Отслеживание изменений (`tvgen diff`)

Команда `tvgen diff` сравнивает файлы в каталоге `results/` с предыдущими
копиями из `cache/`. Это позволяет увидеть новые или удалённые поля после
обновления данных.

```bash
tvgen diff --market crypto
```

Отчёт можно сохранить в файл:

```bash
tvgen diff --market all --output diff.md
```
