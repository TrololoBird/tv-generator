from pathlib import Path

import yaml
from src.generator.openapi_generator import OpenAPIGenerator


def _create_field_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("field\tstatus\tvalue\n")
        f.write("close\tok\t1\n")
        f.write("open\tok\tabc\n")


def test_generate(tmp_path: Path):
    market_dir = tmp_path / "results" / "crypto"
    _create_field_status(market_dir / "field_status.tsv")

    gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    gen.generate(out, market="crypto")

    data = yaml.safe_load(out.read_text())
    assert "/crypto/scan" in data["paths"]
    assert "CryptoFields" in data["components"]["schemas"]


def test_generate_missing_field_status(tmp_path: Path) -> None:
    market_dir = tmp_path / "results" / "crypto"
    market_dir.mkdir(parents=True)

    gen = OpenAPIGenerator(tmp_path / "results")
    out = tmp_path / "spec.yaml"
    gen.generate(out)

    data = yaml.safe_load(out.read_text())
    assert "/crypto/scan" not in data["paths"]
