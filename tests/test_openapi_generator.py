import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # noqa: E402

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
