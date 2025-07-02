# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.0.0] — 2025-07-02

### ✅ Совместимость с OpenAPI 3.1.0 + GPT Builder
- Удалены все `"example"` → заменены на `"examples"`, затем полностью удалены.
- Добавлена safeguard-функция `remove_all_examples`.
- Удалены конструкции `oneOf`, `nullable`.
- Добавлены поля: `security`, `securitySchemes`, `operationId`.

### ⚙️ Архитектура и CLI
- Переименован `core.py` → `main.py` (устранён конфликт с `core/`).
- Добавлен метод `run()` и `save_spec()` в `OpenAPIPipeline`.
- CLI стабилен: `python -m src.tv_generator generate ...`.

### 🧹 Чистка проекта
- Удалены временные тесты и конфликты.
- Удалён установленный пакет `tv_generator` из окружения.

## [v2.0.0] — 2025-06-22

### 🚀 Основные изменения
- Реструктуризация проекта
- Улучшенная архитектура
- Поддержка множественных рынков

## [v1.0.0] — 2025-06-01

### 🎉 Первый релиз
- Базовая функциональность генерации OpenAPI спецификаций
- Поддержка TradingView API
- CLI интерфейс

## 1.0.53 - 2025-06-18
- Automated update
## 1.0.52 - 2025-06-18
- Automated update
## 1.0.51 - 2025-06-18
- Automated update
## 1.0.50
- Fix package configuration to exclude missing `src.constants` directory

## 1.0.49
- Pin package versions

## 1.0.48
- Version bump
## 1.0.47
- Add diff command and cache comparison

## 1.0.46
- Version bump
## 1.0.45
- Version bump
## 1.0.43
- Field classifier and advanced generate filters
## 1.0.42
- Scan audit feature

## 1.0.41
- Version bump
## 1.0.40
- Version bump
## 1.0.39
- Version bump
## 1.0.38
- Support alternate field keys in metainfo responses
## 1.0.37
- Version bump
## 1.0.36
- Version bump
## 1.0.35
- Version bump
## 1.0.34
- Version bump
## 1.0.33
- Version bump
## 1.0.32
- Version bump
## 1.0.31
- Version bump
## 1.0.30
- Version bump
## 1.0.29
- Version bump
## 1.0.28
- Version bump
## 1.0.27
- Version bump
## 1.0.26
- Version bump
## 1.0.25
- Version bump
## 1.0.24
- Version bump
## 1.0.23
- Version bump
## 1.0.22
- Version bump
## 1.0.21
- Version bump
## 1.0.20
- Version bump
## 1.0.19
- Version bump
## 1.0.18
- Version bump
## 1.0.17
- Version bump
## 1.0.16
- Version bump
## 1.0.15
- Version bump
## 1.0.14
- Version bump
## 1.0.13
- Version bump
## 1.0.12
- Version bump
## 1.0.11
- Version bump
## 1.0.10
- Version bump
## 1.0.9
- Version bump
## 1.0.8
- Version bump
## 1.0.7
- Version bump
## 1.0.6
- Version bump
## 1.0.5
- Version bump
## 1.0.4
- Version bump
## 1.0.3
- Version bump
## 1.0.2
- Version bump
## 1.0.1
- Version bump
## [1.0.0] – 2025-06-12
### Added
* Daily multi-market pipeline (`collect-full` / `generate`)
* OpenAPI 3.1 generation with GPT Builder extensions
### Fixed
* Size-limit guard (< 1 MB)
## 0.8.40
- Version bump
## 0.8.39
- Version bump
## 0.8.38
- Version bump
## 0.8.37
- Version bump
## 0.8.36
- Version bump
## 0.8.35
- Version bump
## 0.8.34
- Version bump
## 0.8.33
- Version bump
## 0.8.32
- Version bump
## 0.8.31
- Version bump
## 0.8.30
- Fixed artifact workflow to correctly upload generated specifications
## 0.8.29
- Version bump
## 0.8.28
- Added full-field generation, Pydantic validation, etc.
## 0.8.27
- Version bump
## 0.8.26
 - Version bump
## 0.8.24
- Version bump
## 0.8.23
- Version bump
## 0.8.22
- Version bump
## 0.8.21
- Version bump
## 0.8.20
- Version bump
## 0.8.19
- Version bump
## 0.8.18
- Version bump
## 0.8.17
- Version bump
## 0.8.16
- Version bump
## 0.8.15
- Version bump
## 0.8.14
- Version bump
## 0.8.13
- Version bump
## 0.8.12
- Version bump
## 0.8.11
- Version bump
## 0.8.10
- Version bump
## 0.8.9
- Fixed Slack notification action version in spec update workflow
- Version bump
## 0.8.8
* Raise `FileNotFoundError` when market directory missing
* Added unit test for missing market directory
* Fixed test linting issues and updated dependencies

* Version bump
## 0.8.7
* Refactored CLI exception handling for specific error types
* Added logging of CLI errors
* Version bump
## 0.8.6
* Enhanced API retries and JSON handling
* Expanded OpenAPI generator with additional endpoints
* Added optional filter fields to scan request schema
* Added `--debug` CLI option
* Removed unused dependency `tqdm`
* Version bump
## 0.8.5
- Optional HTTP caching via `requests-cache`
- Version bump
## 0.8.4
- Updated Slack notification action version in spec update workflow
- Bumped package version

## 0.8.3
- Fixed Slack notification action version in spec update workflow
- Bumped package version
## 0.8.2
- Added scan filtering options and new CLI commands `search`, `history`, `summary`
- Extended API client with corresponding endpoints
- Improved payload builder to support additional parameters
- Version bump and updated tests
## 0.8.1
- Support multiple API scopes and updated CLI options
- Tests expanded for new scopes

## 0.8.0
- Improved API client configuration and error handling
- Enhanced OpenAPI generator with dynamic version and stricter schemas
- Added verbose logging option to CLI
- Expanded tests for utilities and error cases

## 0.7.9
- New CLI commands `metainfo` and extended `scan` options
- Expanded OpenAPI spec with metainfo endpoint
- Added pre-commit and stricter CI checks

## 0.7.8
- Fix YAML indentation for generated specs
- Bumped version
## 0.7.7
- Fix spec update workflow
- Run daily spec generation
- Bumped version

## 0.7.6
- Improved OpenAPI generator to create output directories automatically
- Added CLI error handling tests
- Added fetch recommendation error test
- Bumped version
## 0.7.5
- Added request and response schemas to generated OpenAPI paths
- Updated tests
- Bumped version
## 0.7.4
- Added boolean type inference and tests
- Bumped version
## 0.7.3
- Improved stock data error test using `pytest.raises`
- Bumped version
## 0.7.2
- Added `--results-dir` option to `generate` command
- Updated tests for new option
- Bumped version
## 0.7.1
- Fixed `pyproject.toml` dependency format for editable installs

## 0.7.0
- Added commands for stock recommendations and prices
- Integrated external data helpers
- Added click to dependencies and bumped version


## 0.6.0
- Improved CLI error handling and messages
- Expanded unit tests with additional edge cases
- Updated CI workflow commands
- Documentation updates and version bump
## 0.5.0
- Fixed packaging configuration for editable installs
- Added editable install and spec validation to CI
- Expanded tests with shared HTTP mocking fixture

## 0.4.0
- Improved CLI tests and removed path hacks
- Cleaned repository and added CI badge
- Updated workflow to use `pytest -q`
- Documentation improvements

## 0.3.0
- Refactored CLI to use `click`
- Added CLI unit tests
- Updated documentation and CI workflow
## 0.2.0
- Removed legacy root scripts
- Added new `tvgen` CLI commands
- Added unit tests and updated CI workflow

## 0.1.0
- Initial modular structure under `src/`
- Basic OpenAPI generator
- GitHub Actions CI
