# Instructions for Codex Agents

## Project Structure
- Source code is located in `src/`.
- API helpers are under `src/api/`.
- OpenAPI generation utilities live in `src/generator/`.
- Common helpers are in `src/utils/`.
- Configuration files may appear in `config/`.
- Tests are under `tests/`.

## Development Workflow

1. Install dependencies: `pip install -r requirements.txt`
2. Format the code with `black .` and lint with `flake8`.
3. Type-check using `mypy src/`.
4. Run tests with `pytest`.
5. Use `python -m src.cli generate --market crypto --output specs/openapi_crypto.yaml` (adjust market as needed).
6. Validate the spec with `openapi-spec-validator specs/openapi_crypto.yaml`
7. Commit changes with semantic versioning updates noted in `CHANGELOG.md`.


## CI
GitHub Actions in `.github/workflows/ci.yml` will lint with flake8, type-check with mypy, and run pytest. Ensure all checks pass before pushing.

## Codex Rules
- All changes must be submitted through a pull request.
- Run the OpenAPI generator and tests before committing.
- Validate YAML files with `openapi-spec-validator`.

### Available Actions
- `analyze_tradingview_api()`
- `generate_openapi_spec()`
- `run_tests()`
- `format_code()`
- `create_pull_request()` (use when specifications in `specs/` are modified)
