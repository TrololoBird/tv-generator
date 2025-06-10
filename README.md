# tv-generator

[![CI](https://github.com/your-org/tv-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/tv-generator/actions/workflows/ci.yml)

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Running

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

Run the full test suite:

```bash
pytest -q
```
The tests rely on the package being installed in editable mode so that modules
can be imported correctly.

To add tests, place new files under the `tests/` directory. Each test file should start with `test_` and use `pytest` assertions. Command line behaviour can be tested with `click.testing.CliRunner`.

## CI/CD

The GitHub Actions workflow runs on every push and pull request. It performs formatting, linting, type checking, tests, spec generation and validation. If any step fails the workflow fails.

```text
black --check .
flake8 .
mypy src/
pytest -q
tvgen generate --market crypto --output specs/openapi_crypto.yaml
openapi-spec-validator specs/openapi_crypto.yaml
```

If tests fail locally ensure that dependencies are installed with `pip install -r requirements.txt`.
