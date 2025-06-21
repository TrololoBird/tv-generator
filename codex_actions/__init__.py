import subprocess
import os
from pathlib import Path
import datetime
import toml


def _run(cmd, *, env=None) -> None:
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Command '{e.cmd}' failed with exit code {e.returncode}")
        if hasattr(e, "output") and e.output:
            print(e.output)
        raise


def generate_openapi_spec() -> None:
    _run(["tvgen", "generate", "--market", "crypto", "--outdir", "specs"])


def validate_spec() -> None:
    _run(["tvgen", "validate", "--spec", "specs/crypto.yaml"])


def run_tests() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    try:
        _run(["pytest", "-v", "--tb=short"], env=env)
    except subprocess.CalledProcessError as e:
        if e.returncode == 4:
            print("No tests were found or pytest configuration failed.")
            return
        print("Tests failed. Debugging required.")
        raise


def format_code() -> None:
    _run(["black", "."])


def bump_version() -> None:
    pyproject = Path("pyproject.toml")
    data = toml.loads(pyproject.read_text())
    version = data["project"]["version"]
    parts = version.split(".")
    if len(parts) == 3:
        parts[-1] = str(int(parts[-1]) + 1)
    else:
        parts.append("1")
    new_version = ".".join(parts)
    data["project"]["version"] = new_version
    pyproject.write_text(toml.dumps(data))

    changelog = Path("CHANGELOG.md")
    date = datetime.date.today().isoformat()
    changelog.write_text(
        f"\n## {new_version} - {date}\n- Automated update\n" + changelog.read_text()
    )


def create_pull_request(title: str, body: str) -> None:
    _run(["gh", "pr", "create", "--title", title, "--body", body])
