# tv-generator

Utilities for interacting with the TradingView Screener API and generating an OpenAPI specification.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Generate an OpenAPI spec from collected field data:

```bash
python -m src.cli generate-openapi results_dir openapi.yaml
```

## Tests

```bash
pytest
```
