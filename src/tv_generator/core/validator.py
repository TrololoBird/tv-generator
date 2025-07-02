"""
Validator implementation for OpenAPI generator.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .base import BaseValidator


class Validator(BaseValidator):
    """Standard validator implementation."""

    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate_field(self, field: dict[str, Any]) -> bool:
        """Validate a field definition."""
        try:
            # Check required fields
            if "n" not in field:
                logger.warning("Field missing 'n' (name)")
                return False

            if "t" not in field:
                logger.warning(f"Field {field.get('n', 'unknown')} missing 't' (type)")
                return False

            # Validate field type
            valid_types = ["number", "price", "percent", "integer", "string", "text", "boolean", "time", "set", "map"]
            if field["t"] not in valid_types:
                logger.warning(f"Field {field['n']} has invalid type: {field['t']}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating field: {e}")
            return False

    def validate_schema(self, schema: dict[str, Any]) -> bool:
        """Validate an OpenAPI schema."""
        try:
            # Check required OpenAPI schema fields
            if "type" not in schema:
                logger.warning("Schema missing 'type' field")
                return False

            # Validate schema type
            valid_types = ["object", "array", "string", "number", "integer", "boolean", "null"]
            if schema["type"] not in valid_types:
                logger.warning(f"Schema has invalid type: {schema['type']}")
                return False

            # Validate enum values if present
            if "enum" in schema:
                if not isinstance(schema["enum"], list):
                    logger.warning("Schema enum must be a list")
                    return False

                if not schema["enum"]:
                    logger.warning("Schema enum cannot be empty")
                    return False

            # Validate properties if object type
            if schema["type"] == "object" and "properties" in schema:
                if not isinstance(schema["properties"], dict):
                    logger.warning("Schema properties must be a dictionary")
                    return False

            # Validate items if array type
            if schema["type"] == "array" and "items" in schema:
                if not isinstance(schema["items"], dict):
                    logger.warning("Schema items must be a dictionary")
                    return False

            return True
        except Exception as e:
            logger.error(f"Error validating schema: {e}")
            return False

    def validate_example(self, example: Any, schema_type: str) -> bool:
        """Validate an example against schema type."""
        try:
            if schema_type == "string":
                return isinstance(example, str)
            elif schema_type == "number":
                return isinstance(example, (int, float)) and not isinstance(example, bool)
            elif schema_type == "integer":
                return isinstance(example, int) and not isinstance(example, bool)
            elif schema_type == "boolean":
                return isinstance(example, bool)
            elif schema_type == "array":
                return isinstance(example, list)
            elif schema_type == "object":
                return isinstance(example, dict)
            else:
                logger.warning(f"Unknown schema type: {schema_type}")
                return True  # Allow unknown types in non-strict mode
        except Exception as e:
            logger.error(f"Error validating example: {e}")
            return False


class StrictValidator(Validator):
    """Strict validator with additional checks."""

    def __init__(self):
        super().__init__(strict=True)

    def validate_field(self, field: dict[str, Any]) -> bool:
        """Validate a field definition with strict rules."""
        if not super().validate_field(field):
            return False

        # Additional strict validations
        if "n" in field and not field["n"].strip():
            logger.warning("Field name cannot be empty")
            return False

        # Validate enum values if present
        if "r" in field and field["r"]:
            if not isinstance(field["r"], list):
                logger.warning("Field references must be a list")
                return False

            for ref in field["r"]:
                if isinstance(ref, dict):
                    if "id" not in ref:
                        logger.warning("Field reference missing 'id'")
                        return False
                elif not isinstance(ref, str):
                    logger.warning("Field reference must be string or dict")
                    return False

        return True

    def validate_schema(self, schema: dict[str, Any]) -> bool:
        """Validate an OpenAPI schema with strict rules."""
        if not super().validate_schema(schema):
            return False

        # Additional strict validations
        if "description" not in schema:
            logger.warning("Schema missing description")
            return False

        if "title" not in schema:
            logger.warning("Schema missing title")
            return False

        return True


class LenientValidator(Validator):
    """Lenient validator with minimal checks."""

    def __init__(self):
        super().__init__(strict=False)

    def validate_field(self, field: dict[str, Any]) -> bool:
        """Validate a field definition with minimal checks."""
        try:
            # Only check if field is a dictionary
            if not isinstance(field, dict):
                return False

            # Only check if it has a name
            if "n" not in field:
                return False

            return True
        except Exception:
            return False

    def validate_schema(self, schema: dict[str, Any]) -> bool:
        """Validate an OpenAPI schema with minimal checks."""
        try:
            # Only check if schema is a dictionary
            if not isinstance(schema, dict):
                return False

            return True
        except Exception:
            return False

    def validate_example(self, example: Any, schema_type: str) -> bool:
        """Validate an example with minimal checks."""
        # Accept any example in lenient mode
        return True
