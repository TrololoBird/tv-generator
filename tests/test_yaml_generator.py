import yaml
import pandas as pd
import pytest
from unittest import mock
from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField


def _sample_meta() -> MetaInfoResponse:
    fields = [
        TVField(name="close", type="integer"),
        TVField(name="open", type="text"),
    ]
    return MetaInfoResponse(data=fields)


def test_generate_yaml() -> None:
    meta = _sample_meta()
    tsv = pd.DataFrame(columns=["field", "tv_type", "status", "sample_value"])
    with mock.patch("toml.load", return_value={"project": {"version": "1.2.3"}}):
        yaml_str = generate_yaml("crypto", meta, tsv)
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
    tsv = pd.DataFrame()
    with mock.patch("toml.load", return_value={"project": {"version": "1.0"}}):
        with pytest.raises(RuntimeError):
            generate_yaml("crypto", meta, tsv, max_size=10)
