# tv-generator


## Overview
tv-generator ежедневно тянет TradingView metainfo/scan и генерирует OpenAPI 3.1 YAML для GPT Builder Custom Action.

## Quick Start
### Poetry
poetry install    
poetry run tvgen collect-full --market all
poetry run tvgen generate     --market all
poetry run tvgen build --indir results --outdir specs
poetry run tvgen preview --spec specs/crypto.yaml
  
### Docker
docker run --rm ghcr.io/<owner>/tvgen:latest \
  tvgen collect-full --market all && \
  tvgen generate     --market all
  
## CLI Guide
| Command      | Purpose                                   | Key Flags                        |
|--------------|-------------------------------------------|----------------------------------|
| build        | collect+generate specs for all markets    | --indir • --outdir |
| collect-full | download metainfo+scan, build TSV         | --market • --outdir • --tickers |
| generate     | build OpenAPI spec                        | --market • --indir • --outdir • --max-size |
| preview      | show fields summary from spec             | --spec |

## Daily CI Flow
collect-full → generate → size-validate → commit

## Field Name Format
Индикаторы могут иметь вид `NAME|TF`. Например, `RSI|60` означает значение
индекса RSI на 60‑минутном таймфрейме. Запись `ADX+DI[1]|1D` интерпретируется
как индикатор `ADX+DI[1]` на дневных свечах.

### Example Schema
```yaml
components:
  schemas:
    NumericFieldNoTimeframe:
      type: string
      enum: [RSI, EMA20]
      description: Дневные значения индикаторов
      example: RSI
    NumericFieldWithTimeframe:
      type: string
      pattern: "^[A-Z0-9_+\\[\\]]+\\|(1|5|15|30|60|120|240|1D|1W)$"
      description: Индикатор с таймфреймом
      example: ADX+DI[1]|1D
      x-openai-schema-title: Numeric Field
```

## Import into GPT Builder
1. Add Action → Upload YAML  
2. Выберите файл specs/<market>.yaml  
3. Нажмите Validate — ошибок быть не должно

## Badges
[Build] (link to GitHub Action badge) [Coverage] (позже заменим процент) [Docker] (latest tag)
