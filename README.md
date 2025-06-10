# tv-generator

[![CI](https://github.com/your-org/tv-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/tv-generator/actions/workflows/ci.yml)

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

```bash
pip install -r requirements.txt
pip install -e .  # installs the `tvgen` command
```

## Usage

Scan a market:

```bash
tvgen scan --market crypto
```

Generate an OpenAPI spec:

```bash
tvgen generate --market crypto --output specs/openapi_crypto.yaml
```

Validate a spec file:

```bash
tvgen validate --spec specs/openapi_crypto.yaml
```

## Tests

Run the full suite:

```bash
pytest -q
```

To add new tests create a `test_*.py` file under `tests/`. Use `pytest` assertions and `click.testing.CliRunner` for CLI behaviour.

If tests fail locally ensure dependencies are installed with `pip install -r requirements.txt` and the package installed in editable mode with `pip install -e .`.

## CI/CD

The GitHub Actions workflow runs formatting, linting, type checking, tests, spec generation and validation on every push and PR. It fails immediately if any step fails.

```text
black --check .
flake8 .
mypy src/
pytest -q
tvgen generate --market crypto --output specs/openapi_crypto.yaml
openapi-spec-validator specs/openapi_crypto.yaml
```
