"""
Утилиты для генерации примеров и обработки enum для OpenAPI схем.
"""

from typing import Any, Dict, List


def generate_field_example(field: dict[str, Any]) -> Any:
    field_type = field.get("t", "string")
    if field_type in ("number", "price", "percent"):
        return 123.45
    elif field_type == "integer":
        return 123
    elif field_type == "boolean":
        return True
    elif field_type == "time":
        return "2023-01-01T00:00:00Z"
    elif field_type == "set":
        return ["item1", "item2"]
    elif field_type == "map":
        return {"key": "value"}
    else:
        return "example_value"


def extract_enum_values(field: dict[str, Any]) -> list[Any]:
    """Извлекает значения enum из поля TradingView."""
    enum_values = []
    for ref in field.get("r", []) or []:
        if isinstance(ref, dict) and "id" in ref:
            enum_values.append(ref["id"])
        elif isinstance(ref, str):
            enum_values.append(ref)
    return enum_values
