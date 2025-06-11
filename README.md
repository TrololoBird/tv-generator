# tv-generator

[![CI](https://github.com/your-org/tv-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/tv-generator/actions/workflows/ci.yml)

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

Install runtime requirements and the package in editable mode:

```bash
pip install -r requirements.txt
pip install -e .
```

Optionally install `requests-cache` to enable persistent HTTP caching:

```bash
pip install requests-cache
```

For development and running the test suite you will also need some tooling:

```bash
pip install black flake8 mypy pytest openapi-spec-validator requests_mock pre-commit
```
Then install the git hooks:

```bash
pre-commit install
```

Strict type checking requires Python type stubs for third-party libraries:

```bash
pip install types-requests types-PyYAML types-toml
```

## Running

Scan a market:

```bash
tvgen scan --scope crypto --symbols BTCUSD --columns close
```

Additional scan options are available:

```bash
tvgen scan --scope crypto \
  --symbols BTCUSD --columns close \
  --filter "{}" --filter2 "{}" --sort "{}" --range "{}"
```

Fetch market metadata:

```bash
tvgen metainfo --scope crypto --query btc
```

Generate an OpenAPI spec and save it to `specs/`:

```bash
tvgen generate --market crypto --output specs/openapi_crypto.yaml
```

Validate a spec file:

```bash
tvgen validate --spec specs/openapi_crypto.yaml
```

Fetch recommendation or price for a symbol:

```bash
tvgen recommend --symbol AAPL
tvgen price --symbol AAPL
```

Set `TV_CACHE=1` to cache HTTP responses locally:

```bash
TV_CACHE=1 tvgen scan --scope crypto --symbols BTCUSD --columns close
```

Check the installed version:

```bash
tvgen --version
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

### Automated spec updates

The [`spec-update.yml`](.github/workflows/spec-update.yml) workflow runs weekly to generate and validate the OpenAPI spec. If the specification file changes, a pull request is opened automatically with the updated YAML.
## Troubleshooting CI failures

Most CI issues are caused by formatting, lint or type errors. Before pushing run:

```bash
pre-commit run --all-files
black .
flake8 .
mypy src/
pytest -q
tvgen generate --market crypto --output specs/openapi_crypto.yaml
openapi-spec-validator specs/openapi_crypto.yaml
```

Ensure all commands succeed locally to avoid pipeline failures.
