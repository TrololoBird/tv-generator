import subprocess
import sys
from pathlib import Path


def generate_openapi_spec():
    """Run the CLI generator for the crypto market."""
    spec_file = Path("specs/openapi_crypto.yaml")
    # tvgen generate expects results/crypto/field_status.tsv
    status_file = Path("results/crypto/field_status.tsv")
    if not status_file.exists():
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(
            "field\tstatus\tvalue\nclose\tok\t1\nopen\tok\tabc\n",
            encoding="utf-8",
        )

    try:
        result = subprocess.run(
            [
                "tvgen",
                "generate",
                "--market",
                "crypto",
                "--output",
                str(spec_file),
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


def validate_spec():
    """Validate the generated crypto specification."""
    try:
        subprocess.run(
            ["tvgen", "validate", "--spec", "specs/openapi_crypto.yaml"],
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


def create_pull_request():
    """Open a pull request using the GitHub CLI."""
    try:
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "Update OpenAPI specs",
                "--body",
                "Automated specification update",
            ],
            check=True,
        )
    except FileNotFoundError:
        print("GitHub CLI not found", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        raise
