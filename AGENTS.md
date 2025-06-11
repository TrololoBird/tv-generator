# Instructions for Codex Agents

## 📁 Project Structure

* Source code is in `src/`

  * `api/` — TradingView API wrappers
  * `generator/` — OpenAPI 3.1.0 spec generation logic
  * `utils/` — shared utilities and type inference
* CLI interface: `src/cli.py`
  * `tvgen scan --scope <market>` - perform a basic scan
  * `tvgen recommend --symbol <symbol> [--market stocks]` - fetch recommendation
  * `tvgen price --symbol <symbol> [--market stocks]` - fetch last close price
  * `tvgen search --payload <json> --scope <market>` - call /{scope}/search
  * `tvgen history --payload <json> --scope <market>` - call /{scope}/history
  * `tvgen summary --payload <json> --scope <market>` - call /{scope}/summary
  * `tvgen generate --market <market> --output specs/<market>.yaml` - create spec
  * `tvgen validate --spec <file>` - validate a spec file
* Tests: `tests/`
* OpenAPI specs: `specs/`

Common flags:

* `--scope` - TradingView market name for scan-like commands
* `--filter2`, `--sort`, `--range` - optional JSON objects passed to `scan`

---

## 🛠 Development Workflow

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Format code**

   ```bash
   black .
   ```

3. **Lint**

   ```bash
   flake8 .
   ```

4. **Type-check**

   ```bash
   mypy src/
   ```

5. **Run tests**

   ```bash
   pytest -q
   ```

6. **Generate OpenAPI spec**

   ```bash
   tvgen generate --market crypto --output specs/openapi_crypto.yaml
   ```

7. **Validate spec**

   ```bash
   tvgen validate --spec specs/openapi_crypto.yaml
   ```

8. **Commit changes**

   * Update `CHANGELOG.md` with semantic version bump
   * Commit updated `specs/*.yaml`

---

## ⚙️ CI/CD Integration

GitHub Actions in `.github/workflows/ci.yml` will:

* Check formatting (`black --check .`)
* Lint (`flake8 .`)
* Type-check (`mypy src/`)
* Run tests (`pytest -q`)
* Generate spec (`tvgen generate`)
* Validate spec (`openapi-spec-validator specs/*.yaml`)
* Optionally auto-commit or open a PR if `specs/*.yaml` changed

A nightly or weekly scheduled job can re-run the same steps to keep specs up-to-date.

---

## 🤖 Codex Rules

* **All changes must be submitted via pull request**
* **Codex must** always:

  * run the OpenAPI generator (`generate_openapi_spec()`) – runs `tvgen generate --market crypto --output specs/openapi_crypto.yaml`
  * validate the YAML (`validate_spec()`) – runs `tvgen validate --spec specs/openapi_crypto.yaml`
  * run the tests (`run_tests()`)
* **Codex should**:

  * format code (`format_code()`)
  * bump the version and update `CHANGELOG.md` (`bump_version()`)
  * create a pull request if any `specs/*.yaml` changed (`create_pull_request()`)

---

## ✅ Available Codex Actions

* `generate_openapi_spec()`
* `run_tests()`
* `format_code()`
* `validate_spec()`
* `bump_version()`
* `create_pull_request()`

`bump_version()` updates `pyproject.toml` and `CHANGELOG.md`. `create_pull_request()`
uses the GitHub CLI to open a PR with updated specs.
