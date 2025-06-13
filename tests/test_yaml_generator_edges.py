import pandas as pd
import yaml
import pytest

from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField


def test_generate_yaml_unknown_field_type() -> None:
    field = TVField(name="foo", type="integer")
    object.__setattr__(field, "t", "unknown")
    meta = MetaInfoResponse(data=[field])
    tsv = pd.DataFrame()
    with pytest.raises(KeyError):
        generate_yaml("crypto", meta, tsv, None)


def test_generate_yaml_empty_and_none_scan() -> None:
    meta = MetaInfoResponse(data=[TVField(name="close", type="integer")])
    tsv = pd.DataFrame()
    for scan in [None, {"data": []}]:
        yaml_str = generate_yaml("crypto", meta, tsv, scan)
        data = yaml.safe_load(yaml_str)
        assert "CryptoFields" in data["components"]["schemas"]


def test_numeric_field_with_custom_timeframe() -> None:
    field = TVField(name="ADX+DI[1]|90", type="number")
    meta = MetaInfoResponse(data=[field])
    tsv = pd.DataFrame()
    yaml_str = generate_yaml("crypto", meta, tsv, None)
    data = yaml.safe_load(yaml_str)
    props = data["components"]["schemas"]["CryptoFields"]["properties"]
    assert "90-minute" in props["ADX+DI[1]|90"]["description"]
    assert "NumericFieldWithTimeframe" in data["components"]["schemas"]
