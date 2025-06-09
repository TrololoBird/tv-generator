# tv-generator

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Scan a market

```bash
tvgen scan --market crypto
```

### Generate an OpenAPI spec

```bash
tvgen generate --market crypto --output specs/openapi_crypto.yaml
```

### Validate a spec

```bash
tvgen validate --spec specs/openapi_crypto.yaml
```

## Tests

```bash
pytest
```

## CI/CD

The GitHub Actions workflow performs the following steps on every push and
weekly schedule:

1. `black --check .`
2. `flake8 .`
3. `mypy src/`
4. `pytest`
5. `tvgen generate --market crypto --output specs/openapi_crypto.yaml`
6. `openapi-spec-validator specs/openapi_crypto.yaml`

If the generated specification changes, the workflow automatically commits the
updated file back to the repository.
