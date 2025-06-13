import subprocess
import sys
import json
from pathlib import Path
from src.constants import SCOPES


def generate_openapi_spec() -> None:
    """Run the CLI generator for all markets."""

    for market in SCOPES:
        meta_file = Path(f"results/{market}/metainfo.json")
        scan_file = Path(f"results/{market}/scan.json")
        status_file = Path(f"results/{market}/field_status.tsv")
        if not meta_file.exists():
            meta_file.parent.mkdir(parents=True, exist_ok=True)
            meta = {"data": {"fields": [{"name": "close", "type": "integer"}]}}
            meta_file.write_text(json.dumps(meta), encoding="utf-8")
        if not scan_file.exists():
            scan_file.write_text(json.dumps({"data": []}), encoding="utf-8")
        if not status_file.exists():
            status_file.write_text("field\ttv_type\tstatus\tsample_value\n")

    try:
        for market in SCOPES:
            result = subprocess.run(
                [
                    "tvgen",
                    "generate",
                    "--market",
                    market,
                    "--indir",
                    "results",
                    "--outdir",
                    "specs",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
    except FileNotFoundError:
        print("tvgen command not found", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise


def validate_spec() -> None:
    """Validate all generated specifications."""
    for market in SCOPES:
        spec = Path(f"specs/{market}.yaml")
        if not spec.exists():
            continue
        try:
            subprocess.run(
                ["tvgen", "validate", "--spec", str(spec)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print("tvgen command not found", file=sys.stderr)
            raise
        except subprocess.CalledProcessError as exc:
            print(exc.stderr, file=sys.stderr)
            raise


def run_tests():
    try:
        subprocess.run(["pytest", "-q"], check=True)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise


def format_code():
    try:
        subprocess.run(["black", "."], check=True)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise


def bump_version():
    """Bump patch version in pyproject.toml and update CHANGELOG."""
    import toml
    from pathlib import Path

    pyproject = Path("pyproject.toml")
    data = toml.load(pyproject)
    version = data["project"]["version"]
    major, minor, patch = map(int, version.split("."))
    new_version = f"{major}.{minor}.{patch + 1}"
    data["project"]["version"] = new_version
    with open(pyproject, "w", encoding="utf-8") as fh:
        toml.dump(data, fh)

    changelog = Path("CHANGELOG.md")
    if changelog.exists():
        lines = changelog.read_text().splitlines()
    else:
        lines = ["# Changelog"]
    header = f"## {new_version}"
    entry = "- Version bump"
    if header not in lines:
        lines.insert(1, header)
        lines.insert(2, entry)
    changelog.write_text("\n".join(lines) + "\n")
    print(f"Version bumped to {new_version}")


def create_pull_request(
    title: str = "Update OpenAPI specs",
    body: str = "Automated specification update",
):
    """Open a pull request using the GitHub CLI."""
    try:
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
            ],
            check=True,
        )
    except FileNotFoundError:
        print("GitHub CLI not found", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise
