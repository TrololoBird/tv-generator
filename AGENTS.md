# Codex Agent Guide

Welcome! This document explains how to work with this repository when acting as a Codex agent.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [CLI Examples](#cli-examples)
5. [CI/CD Integration](#cicd-integration)
6. [Codex Rules](#codex-rules)
7. [Available Codex Actions](#available-codex-actions)
8. [Glossary](#glossary)

## Getting Started

The typical workflow is:

```
tvgen collect-full --market crypto
 tvgen generate --market crypto --outdir specs
 tvgen validate --spec specs/crypto.yaml
```

After validating the spec, commit your changes with an updated `CHANGELOG.md`.

## Project Structure

- Source code in `src/`
  - `api/` – TradingView API wrappers
  - `generator/` – OpenAPI 3.1.0 spec generation logic
  - `utils/` – shared utilities and type inference
- CLI entry point: `src/cli.py`
- Tests live in `tests/`
- OpenAPI specs are stored in `specs/`

### Common CLI Flags

- `--market` – TradingView market name
- `--filter2`, `--sort`, `--range` – optional JSON for `scan`

⚠️ **Note**: `tvgen generate` requires `results/<market>/field_status.tsv`. Create a minimal file if it doesn't exist.

## Development Workflow

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install types-requests types-PyYAML types-toml
   ```
2. **Format code** (run before every commit)
   ```bash
   black .
   ```
3. **Lint**
   ```bash
   flake8 .
   ```
4. **Type-check**
   ```bash
   mypy src/
   ```
5. **Run tests**
   ```bash
   PYTHONPATH=$PWD pytest -q
   ```
6. **Generate OpenAPI spec**
   ```bash
   tvgen generate --market crypto --outdir specs
   ```
7. **Validate spec**
   ```bash
   tvgen validate --spec specs/crypto.yaml
   ```
8. **Commit changes**
   - Update `CHANGELOG.md` with a semantic version bump
   - Commit updated `specs/*.yaml`

## CLI Examples

```bash
$ tvgen price --symbol AAPL
1.0

$ tvgen scan --symbols BTCUSD,ETHUSD --columns close --market crypto
{
  "count": 2,
  "data": [
    {"s": "BINANCE:BTCUSD", "d": [50000.0]},
    {"s": "COINBASE:ETHUSD", "d": [48000.0]}
  ]
}
```

## CI/CD Integration

GitHub Actions (see [ci.yml](.github/workflows/ci.yml)) automatically run:
- `black --check .`
- `flake8 .`
- `mypy src/`
- `pytest -q`
- `tvgen generate`
- `openapi-spec-validator specs/*.yaml`

Check the Actions tab on GitHub for run status. A scheduled workflow keeps specs up to date.

## Codex Rules

- All changes **must** be submitted via pull request.
- **Must** actions:
  - `generate_openapi_spec()` – runs `tvgen generate --market crypto --outdir specs`
  - `validate_spec()` – runs `tvgen validate --spec specs/crypto.yaml`
  - `run_tests()`
- **Should** actions:
  - `format_code()`
  - `bump_version()` – updates `pyproject.toml` and `CHANGELOG.md`
  - `create_pull_request()` if specs changed

`Must` means the agent always executes the action. `Should` means it is recommended when relevant.

## Available Codex Actions

| Action | Description |
| ------ | ----------- |
| `generate_openapi_spec()` | Build `specs/crypto.yaml`. |
| `run_tests()` | Execute the unit tests. |
| `format_code()` | Run `black .` to format files. |
| `validate_spec()` | Validate YAML with `openapi-spec-validator`. |
| `bump_version()` | Increment version in `pyproject.toml` and add a note to `CHANGELOG.md`. |
| `create_pull_request()` | Use the GitHub CLI to open a PR with updated specs. |

## Glossary

- **Codex** – automation tooling that executes actions like generating specs or opening pull requests.
- **OpenAPI spec** – YAML file describing the TradingView API.
- **TradingView API** – endpoints that supply market data used by `tvgen`.
