# tv-generator


## Overview
tv-generator ежедневно тянет TradingView metainfo/scan и генерирует OpenAPI 3.1 YAML для GPT Builder Custom Action.

## Quick Start
### Poetry
poetry install    
poetry run tvgen collect-full --market all
poetry run tvgen generate     --market all
  
### Docker
docker run --rm ghcr.io/<owner>/tvgen:latest \
  tvgen collect-full --market all && \
  tvgen generate     --market all
  
## CLI Guide
| Command      | Purpose                                   | Key Flags                        |
|--------------|-------------------------------------------|----------------------------------|
| build        | collect+generate specs for all markets    | --indir • --outdir |
| collect-full | download metainfo+scan, build TSV         | --market • --outdir • --tickers   |
| generate     | build OpenAPI spec                        | --market • --indir • --max-size   |
| preview      | show fields summary from spec             | --spec |

## Daily CI Flow
collect-full → generate → size-validate → commit

## Import into GPT Builder
1. Add Action → Upload YAML  
2. Выберите файл specs/<market>.yaml  
3. Нажмите Validate — ошибок быть не должно

## Badges
[Build] (link to GitHub Action badge) [Coverage] (позже заменим процент) [Docker] (latest tag)
