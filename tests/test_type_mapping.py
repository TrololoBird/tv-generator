from src.utils.type_mapping import tv2ref
import pytest


def test_tv2ref_known_types():
    for t in [
        "number",
        "price",
        "fundamental_price",
        "percent",
        "integer",
        "float",
    ]:
        assert tv2ref(t) == "#/components/schemas/Num"

    for t in ["bool", "boolean"]:
        assert tv2ref(t) == "#/components/schemas/Bool"

    for t in ["text", "map", "set", "interface", "string"]:
        assert tv2ref(t) == "#/components/schemas/Str"

    for t in ["time", "time-yyyymmdd"]:
        assert tv2ref(t) == "#/components/schemas/Time"


def test_tv2ref_unknown_type():
    with pytest.raises(KeyError):
        tv2ref("unknown")
