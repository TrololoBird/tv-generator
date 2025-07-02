"""
Validation module for OpenAPI specifications.
"""

import json
from pathlib import Path
from typing import List, Tuple

from loguru import logger
from openapi_spec_validator import validate_spec


def validate_spec_file(spec_path: Path) -> tuple[bool, list[str]]:
    """Валидирует один файл OpenAPI спецификации."""
    errors = []

    try:
        with open(spec_path, encoding="utf-8") as f:
            spec = json.load(f)

        # Валидация через openapi_spec_validator
        validate_spec(spec)
        return True, []

    except Exception as e:
        errors.append(str(e))
        return False, errors


def validate_all_specs(specs_dir: Path) -> None:
    """Validate all OpenAPI specifications in the given directory."""
    if not specs_dir.exists():
        logger.error(f"Specs directory not found: {specs_dir}")
        return

    logger.info(f"Validating OpenAPI specs in {specs_dir}")

    valid_count = 0
    invalid_count = 0

    for spec_file in specs_dir.glob("*_openapi.json"):
        market = spec_file.stem.replace("_openapi", "")
        try:
            with open(spec_file, encoding="utf-8") as f:
                spec = json.load(f)

            # Basic validation
            if "openapi" not in spec:
                raise ValueError("Missing openapi version")
            if "info" not in spec:
                raise ValueError("Missing info section")
            if "paths" not in spec:
                raise ValueError("Missing paths section")

            logger.info(f"{market}: Valid")
            valid_count += 1

        except Exception as e:
            logger.error(f"{market}: Invalid - {e}")
            invalid_count += 1

    logger.info(f"Validation Summary: {valid_count} valid, {invalid_count} invalid")
