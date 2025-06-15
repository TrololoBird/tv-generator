import pandas as pd
import yaml

from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField


def test_generate_yaml_unknown_field_type() -> None:
    field = TVField(name="foo", type="integer")
    object.__setattr__(field, "t", "unknown")
    meta = MetaInfoResponse(data=[field])
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    props = data["components"]["schemas"]["CryptoFields"]["properties"]
    assert props["foo"]["$ref"] == "#/components/schemas/Str"


def test_generate_yaml_empty_and_none_scan() -> None:
    meta = MetaInfoResponse(data=[TVField(name="close", type="integer")])
    for scan in [None, {"data": []}]:
        yaml_str = generate_yaml("crypto", meta, scan)
        data = yaml.safe_load(yaml_str)
        assert "CryptoFields" in data["components"]["schemas"]


def test_numeric_field_with_custom_timeframe() -> None:
    field = TVField(name="ADX+DI[1]|90", type="number")
    meta = MetaInfoResponse(data=[field])
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    props = data["components"]["schemas"]["CryptoFields"]["properties"]
    assert "90-minute" in props["ADX+DI[1]|90"]["description"]
    assert "NumericFieldWithTimeframe" in data["components"]["schemas"]
