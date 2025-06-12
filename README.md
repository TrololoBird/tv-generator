# tv-generator


## Overview
tv-generator ежедневно тянет TradingView metainfo/scan и генерирует OpenAPI 3.1 YAML для GPT Builder Custom Action.

## Quick Start
### Poetry
poetry install    
poetry run tvgen collect-full --scope all      
poetry run tvgen generate     --scope all      
  
### Docker
docker run --rm ghcr.io/<owner>/tvgen:latest \  
  tvgen collect-full --scope all && \    
  tvgen generate     --scope all    
  
## CLI Guide
| Command      | Purpose                                   | Key Flags                        |
|--------------|-------------------------------------------|----------------------------------|
| collect-full | download metainfo+scan, build TSV         | --scope • --outdir • --tickers   |
| generate     | build OpenAPI spec                        | --scope • --indir • --max-size   |

## Daily CI Flow
collect-full → generate → size-validate → commit

## Import into GPT Builder
1. Add Action → Upload YAML  
2. Выберите файл specs/<market>.yaml  
3. Нажмите Validate — ошибок быть не должно

## Badges
[Build] (link to GitHub Action badge) [Coverage] (позже заменим процент) [Docker] (latest tag)
