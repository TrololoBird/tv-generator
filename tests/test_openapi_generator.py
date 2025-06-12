from pathlib import Path

import json
import pytest
import yaml
from unittest import mock
from src.generator.openapi_generator import OpenAPIGenerator


def _create_metainfo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "data": {
            "fields": [
                {"name": "close", "type": "integer", "description": ""},
                {"name": "open", "type": "string"},
            ]
        }
    }
    path.write_text(json.dumps(data))


def test_generate(tmp_path: Path):
    market_dir = tmp_path / "results" / "crypto"
    _create_metainfo(market_dir / "metainfo.json")

    with mock.patch("toml.load", return_value={"project": {"version": "1.2.3"}}):
        gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    gen.generate(out, market="crypto")

    data = yaml.safe_load(out.read_text())
    assert data["info"]["version"] == "1.2.3"
    assert "/crypto/scan" in data["paths"]
    scan_path = data["paths"]["/crypto/scan"]["post"]
    assert (
        scan_path["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CryptoScanRequest"
    )
    assert (
        scan_path["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CryptoScanResponse"
    )
    schemas = data["components"]["schemas"]
    assert "CryptoFields" in schemas
    assert "CryptoScanRequest" in schemas
    assert "CryptoScanResponse" in schemas
    assert "CryptoMetainfoResponse" in schemas
    props = schemas["CryptoScanRequest"]["properties"]
    for name in ["filter", "filter2", "sort", "range"]:
        assert name in props
    # new endpoints
    for ep in ["search", "history", "summary"]:
        assert f"/crypto/{ep}" in data["paths"]


def test_generate_missing_metainfo(tmp_path: Path) -> None:
    market_dir = tmp_path / "results" / "crypto"
    market_dir.mkdir(parents=True)

    gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    with pytest.raises(RuntimeError):
        gen.generate(out)


def test_generate_multiple_markets(tmp_path: Path) -> None:
    crypto_dir = tmp_path / "results" / "crypto"
    stocks_dir = tmp_path / "results" / "stocks"
    _create_metainfo(crypto_dir / "metainfo.json")
    _create_metainfo(stocks_dir / "metainfo.json")

    gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    gen.generate(out)

    data = yaml.safe_load(out.read_text())
    assert "/crypto/scan" in data["paths"]
    assert "/stocks/scan" in data["paths"]


def test_generate_missing_market_dir(tmp_path: Path) -> None:
    gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    with pytest.raises(FileNotFoundError):
        gen.generate(out, market="crypto")
