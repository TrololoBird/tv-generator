# Changelog
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
