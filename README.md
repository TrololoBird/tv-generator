# tv-generator

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Scan a market

```bash
python -m src.cli scan --market crypto
```

### Generate an OpenAPI spec

```bash
python -m src.cli generate --market crypto --output specs/openapi_crypto.yaml
```

### Validate a spec

```bash
python -m src.cli validate --spec specs/openapi_crypto.yaml
```

## Tests

```bash
pytest
```

## CI/CD

The GitHub Actions workflow formats code, lints, runs type checks and unit
tests, generates the crypto specification and validates it. Any changed files in
`specs/` are automatically committed back to the repository.
