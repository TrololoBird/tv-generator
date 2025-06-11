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
    raise NotImplementedError("Version bump must be done manually")


def create_pull_request():
    raise NotImplementedError("PR creation is handled externally")
