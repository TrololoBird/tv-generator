# Changelog
## 0.8.17
- Version bump
## 0.8.16
- Version bump
## 0.8.15
- Version bump
## 0.8.14
- Version bump
## 0.8.13
- Version bump
## 0.8.12
- Version bump
## 0.8.11
- Version bump
## 0.8.10
- Version bump
## 0.8.9
- Fixed Slack notification action version in spec update workflow
- Version bump
## 0.8.8
* Raise `FileNotFoundError` when market directory missing
* Added unit test for missing market directory
* Fixed test linting issues and updated dependencies

* Version bump
## 0.8.7
* Refactored CLI exception handling for specific error types
* Added logging of CLI errors
* Version bump
## 0.8.6
* Enhanced API retries and JSON handling
* Expanded OpenAPI generator with additional endpoints
* Added optional filter fields to scan request schema
* Added `--debug` CLI option
* Removed unused dependency `tqdm`
* Version bump
## 0.8.5
- Optional HTTP caching via `requests-cache`
- Version bump
## 0.8.4
- Updated Slack notification action version in spec update workflow
- Bumped package version

## 0.8.3
- Fixed Slack notification action version in spec update workflow
- Bumped package version
## 0.8.2
- Added scan filtering options and new CLI commands `search`, `history`, `summary`
- Extended API client with corresponding endpoints
- Improved payload builder to support additional parameters
- Version bump and updated tests
## 0.8.1
- Support multiple API scopes and updated CLI options
- Tests expanded for new scopes

## 0.8.0
- Improved API client configuration and error handling
- Enhanced OpenAPI generator with dynamic version and stricter schemas
- Added verbose logging option to CLI
- Expanded tests for utilities and error cases

## 0.7.9
- New CLI commands `metainfo` and extended `scan` options
- Expanded OpenAPI spec with metainfo endpoint
- Added pre-commit and stricter CI checks

## 0.7.8
- Fix YAML indentation for generated specs
- Bumped version
## 0.7.7
- Fix spec update workflow
- Run daily spec generation
- Bumped version

## 0.7.6
- Improved OpenAPI generator to create output directories automatically
- Added CLI error handling tests
- Added fetch recommendation error test
- Bumped version
## 0.7.5
- Added request and response schemas to generated OpenAPI paths
- Updated tests
- Bumped version
## 0.7.4
- Added boolean type inference and tests
- Bumped version
## 0.7.3
- Improved stock data error test using `pytest.raises`
- Bumped version
## 0.7.2
- Added `--results-dir` option to `generate` command
- Updated tests for new option
- Bumped version
## 0.7.1
- Fixed `pyproject.toml` dependency format for editable installs

## 0.7.0
- Added commands for stock recommendations and prices
- Integrated external data helpers
- Added click to dependencies and bumped version


## 0.6.0
- Improved CLI error handling and messages
- Expanded unit tests with additional edge cases
- Updated CI workflow commands
- Documentation updates and version bump
## 0.5.0
- Fixed packaging configuration for editable installs
- Added editable install and spec validation to CI
- Expanded tests with shared HTTP mocking fixture

## 0.4.0
- Improved CLI tests and removed path hacks
- Cleaned repository and added CI badge
- Updated workflow to use `pytest -q`
- Documentation improvements

## 0.3.0
- Refactored CLI to use `click`
- Added CLI unit tests
- Updated documentation and CI workflow
## 0.2.0
- Removed legacy root scripts
- Added new `tvgen` CLI commands
- Added unit tests and updated CI workflow

## 0.1.0
- Initial modular structure under `src/`
- Basic OpenAPI generator
- GitHub Actions CI
