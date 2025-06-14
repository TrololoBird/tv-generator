# tv-generator

## Overview

`tv-generator` fetches TradingView metainfo and scan results and generates an OpenAPI 3.1 YAML specification suitable for GPT Builder custom actions.

## Quick Start

### Using Poetry
```bash
poetry install
poetry run tvgen collect --market crypto
poetry run tvgen generate --market crypto
poetry run tvgen validate --spec specs/crypto.yaml
```
You can also build the full set of markets:
```bash
poetry run tvgen build --indir results --outdir specs
poetry run tvgen preview --spec specs/crypto.yaml
```

## Network Requirements
The generation commands contact TradingView's public API. Ensure that `scanner.tradingview.com` is reachable from your environment. GitHub-hosted runners may block this traffic; use a self-hosted runner or run the generator locally if needed.

### Docker
```bash
docker run --rm ghcr.io/<owner>/tv-generator:latest \
  tvgen collect --market crypto && \
  tvgen generate --market crypto
```

## CLI Overview
| Command      | Purpose                                   | Key Flags |
|--------------|-------------------------------------------|-----------|
| build        | collect+generate specs for all markets    | --indir • --outdir |
| collect | download metainfo+scan, build TSV         | --market • --outdir • --tickers |
| generate     | build OpenAPI spec                        | --market • --indir • --outdir • --max-size |
| validate     | validate spec file                        | --spec |
| preview      | show fields summary from spec             | --spec |

### Short Examples
```bash
# Collect metainfo and scan results
tvgen collect --market crypto --outdir results

# Generate specification from collected data
tvgen generate --market crypto --indir results --outdir specs

# Validate generated YAML
tvgen validate --spec specs/crypto.yaml
```

## Daily CI Flow
`collect` → `generate` → size-validate → commit

## Field Name Format
Indicators can include a timeframe suffix separated by `|`. For example `RSI|60` means the RSI value on a 60‑minute timeframe. `ADX+DI[1]|1D` refers to the `ADX+DI[1]` indicator on daily candles.

Timeframe codes map to minutes unless otherwise noted:
```
1, 5, 15, 30, 60, 120, 240   -> minutes
1D                          -> 1 day
1W                          -> 1 week
```

## Type Inference
The :func:`infer_type` utility guesses the OpenAPI scalar type from example
values. Strings equal to ``"true"`` or ``"false"`` in any case are treated as
boolean; other strings default to ``string``.

## OpenAPI File Structure
The generated YAML contains:
- `openapi` and `info` – version and title.
- `servers` – base TradingView endpoint.
- `paths` – endpoints such as `/crypto/scan` or `/stocks/history`, each referencing request and response schemas.
- `components/schemas` – base scalar types (`Num`, `Str`, `Bool`, `Time`, `Array`) and market specific objects. `<Scope>Fields` defines available fields. `<Scope>ScanRequest` describes the `/scan` payload and similar structures exist for `search`, `history` and `summary`.
- `NumericFieldNoTimeframe`/`NumericFieldWithTimeframe` specify whether a field name includes a timeframe suffix.

Example snippet:
```yaml
components:
  schemas:
    NumericFieldNoTimeframe:
      type: string
      # enum is built from the available numeric fields such as [close, volume, ...]
    NumericFieldWithTimeframe:
      type: string
      # pattern uses the timeframe codes parsed from this README
      pattern: "^[A-Z0-9_+\\[\\]]+\\|(1|5|15|30|60|120|240|1D|1W)$"
```

## Import into GPT Builder
1. Choose **Add Action** → **Upload YAML**.
2. Select `specs/<market>.yaml`.
3. Click **Validate** – the file should pass without errors.

## Badges
[![CI](https://github.com/<owner>/tv-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/tv-generator/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ghcr.io/<owner>/tv-generator-blue)](https://github.com/<owner>/tv-generator/pkgs/container/tv-generator)
