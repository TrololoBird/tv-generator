"""Mappings between TradingView types and OpenAPI schema references."""

# TradingView type to OpenAPI component reference mapping
TV_TYPE_TO_REF: dict[str, str] = {
    "number": "#/components/schemas/Num",
    "price": "#/components/schemas/Num",
    "fundamental_price": "#/components/schemas/Num",
    "percent": "#/components/schemas/Num",
    "integer": "#/components/schemas/Num",
    "float": "#/components/schemas/Num",
    "string": "#/components/schemas/Str",
    "bool": "#/components/schemas/Bool",
    "boolean": "#/components/schemas/Bool",
    "text": "#/components/schemas/Str",
    "map": "#/components/schemas/Str",
    "set": "#/components/schemas/Str",
    "interface": "#/components/schemas/Str",
    "time": "#/components/schemas/Time",
    "time-yyyymmdd": "#/components/schemas/Time",
}


def tv2ref(tv_type: str) -> str:
    """Return an OpenAPI schema reference for a TradingView type."""
    try:
        return TV_TYPE_TO_REF[tv_type]
    except KeyError:
        raise KeyError(tv_type) from None


__all__ = ["TV_TYPE_TO_REF", "tv2ref"]
