# Instructions for Codex Agents

## Project Structure
- Source code is located in `src/`.
- API helpers are under `src/api/`.
- OpenAPI generation utilities live in `src/generator/`.
- Common helpers are in `src/utils/`.
- Configuration files may appear in `config/`.
- Tests are under `tests/`.

## Development Workflow
1. Install dependencies: `pip install -r requirements.txt`.
2. Run tests with `pytest`.
3. Use `python -m src.cli generate-openapi <results_dir> <output>` to rebuild the OpenAPI specification after updating market data.
4. Commit changes with semantic versioning updates noted in `CHANGELOG.md`.

## CI
GitHub Actions in `.github/workflows/ci.yml` will lint with flake8, type-check with mypy, and run pytest. Ensure all checks pass before pushing.
