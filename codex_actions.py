import subprocess


def generate_openapi_spec():
    """Run the CLI generator for the crypto market."""
    subprocess.run(
        [
            "tvgen",
            "generate",
            "--market",
            "crypto",
            "--output",
            "specs/openapi_crypto.yaml",
        ],
        check=True,
    )


def validate_spec():
    """Validate the generated crypto specification."""
    subprocess.run(
        ["tvgen", "validate", "--spec", "specs/openapi_crypto.yaml"],
        check=True,
    )


def run_tests():
    subprocess.run(["pytest", "-q"], check=True)


def format_code():
    subprocess.run(["black", "."], check=True)


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
