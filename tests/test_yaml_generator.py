import yaml
import pytest
from unittest import mock
from src.generator.yaml_generator import (
    generate_yaml,
    collect_field_schemas,
    build_components_schemas,
    build_paths_section,
)
from src.models import MetaInfoResponse, TVField


def _sample_meta() -> MetaInfoResponse:
    fields = [
        TVField(name="close", type="integer"),
        TVField(name="open", type="text"),
    ]
    return MetaInfoResponse(data=fields)


def test_generate_yaml() -> None:
    meta = _sample_meta()
    with mock.patch("toml.load", return_value={"project": {"version": "1.2.3"}}):
        yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    assert data["info"]["version"] == "1.2.3"
    assert "/crypto/scan" in data["paths"]
    scan = data["paths"]["/crypto/scan"]["post"]
    assert (
        scan["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CryptoScanRequest"
    )
    assert (
        scan["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CryptoScanResponse"
    )
    schemas = data["components"]["schemas"]
    assert "CryptoFields" in schemas
    assert "CryptoMetainfoResponse" in schemas


def test_generate_yaml_size_limit() -> None:
    meta = _sample_meta()
    with mock.patch("toml.load", return_value={"project": {"version": "1.0"}}):
        with pytest.raises(RuntimeError):
            generate_yaml("crypto", meta, None, max_size=10)


def test_numeric_field_components() -> None:
    fields = [
        TVField(name="RSI|1D", type="number"),
        TVField(name="ADX+DI[1]|60", type="number"),
    ]
    meta = MetaInfoResponse(data=fields)
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    schemas = data["components"]["schemas"]
    assert schemas["NumericFieldNoTimeframe"]["enum"] == []
    assert "pattern" in schemas["NumericFieldWithTimeframe"]


def test_symbol_field_ignored() -> None:
    meta = MetaInfoResponse(
        data=[
            TVField(name="symbol", type="string"),
            TVField(name="close", type="integer"),
        ]
    )
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    props = data["components"]["schemas"]["CryptoFields"]["properties"]
    assert "symbol" not in props
    assert "close" in props


def test_collect_and_build_components() -> None:
    fields = [TVField(name="RSI|1D", type="number")]
    meta = MetaInfoResponse(data=fields)
    scan = {"data": [{"d": [55]}]}
    collected, no_tf = collect_field_schemas(meta, scan)
    assert collected[0][0] == "RSI|1D"
    assert "description" in collected[0][1]
    assert no_tf == set()

    components = build_components_schemas("Crypto", collected, no_tf)
    assert "CryptoFields" in components
    assert "NumericFieldNoTimeframe" in components


def test_build_paths_section() -> None:
    paths = build_paths_section("crypto", "Crypto")
    assert "/crypto/scan" in paths
    assert "/crypto/metainfo" in paths


def test_fields_split_into_parts() -> None:
    fields = [TVField(name=f"f{i}", type="number") for i in range(130)]
    meta = MetaInfoResponse(data=fields)
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    schemas = data["components"]["schemas"]
    assert "CryptoFieldsPart01" in schemas
    assert "CryptoFieldsPart02" in schemas
    parts = schemas["CryptoFields"]["allOf"]
    assert {"$ref": "#/components/schemas/CryptoFieldsPart01"} in parts
    assert {"$ref": "#/components/schemas/CryptoFieldsPart02"} in parts


def test_fields_split_into_two_parts_at_hundred() -> None:
    fields = [TVField(name=f"field{i}", type="number") for i in range(100)]
    meta = MetaInfoResponse(data=fields)
    yaml_str = generate_yaml("crypto", meta, None)
    data = yaml.safe_load(yaml_str)
    schemas = data["components"]["schemas"]
    assert "CryptoFieldsPart01" in schemas
    assert "CryptoFieldsPart02" in schemas
    parts = schemas["CryptoFields"]["allOf"]
    assert len(parts) == 2
    assert {"$ref": "#/components/schemas/CryptoFieldsPart01"} in parts
    assert {"$ref": "#/components/schemas/CryptoFieldsPart02"} in parts
