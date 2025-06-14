"""Mappings between TradingView types and OpenAPI schema references."""

# TradingView type to OpenAPI component reference mapping
TV_TYPE_TO_REF: dict[str, str] = {
    "number": "#/components/schemas/Num",
    "price": "#/components/schemas/Num",
    "fundamental_price": "#/components/schemas/Num",
    "percent": "#/components/schemas/Num",
    "integer": "#/components/schemas/Num",
    "float": "#/components/schemas/Num",
    "bool": "#/components/schemas/Bool",
    "boolean": "#/components/schemas/Bool",
    "string": "#/components/schemas/Str",
    "text": "#/components/schemas/Str",
    "map": "#/components/schemas/Str",
    "set": "#/components/schemas/Str",
    "interface": "#/components/schemas/Str",
    "time": "#/components/schemas/Time",
    "time-yyyymmdd": "#/components/schemas/Time",
    "array": "#/components/schemas/Array",
    "duration": "#/components/schemas/Num",
    "percentage": "#/components/schemas/Num",
}


def tv2ref(tv_type: str) -> str:
    """Return an OpenAPI schema reference for a TradingView type."""
    try:
        return TV_TYPE_TO_REF[tv_type]
    except KeyError:
        import warnings

        warnings.warn(
            f"Unknown TradingView field type '{tv_type}', falling back to string",
            RuntimeWarning,
        )
        return "#/components/schemas/Str"


__all__ = ["TV_TYPE_TO_REF", "tv2ref"]
