from pathlib import Path
import json
import yaml
from click.testing import CliRunner

from src.generator.yaml_generator import classify_fields
from src.cli import cli


def test_classify_fields() -> None:
    columns = {
        "RSI": {"type": "number"},
        "EMA20": {"type": "number"},
        "ADX|60": {"type": "number"},
        "ADX+DI[1]|240": {"type": "number"},
        "24h_close_change": {"type": "number"},
        "sector": {"type": "text"},
        "exchange": {"type": "string"},
        "BTC_impact_score": {"type": "number", "source": "scan"},
        "TV_Custom.foo": {"type": "number", "source": "scan"},
    }
    info = classify_fields(columns)
    assert set(info["numeric"]) >= {
        "RSI",
        "EMA20",
        "ADX",
        "ADX+DI[1]",
        "24h_close_change",
    }
    assert "sector" in info["string"] and "exchange" in info["string"]
    assert "BTC_impact_score" in info["custom"]
    assert "BTC_impact_score" in info["discovered"]
    assert any(v.startswith("TV_Custom") for v in info["custom"])
    assert set(info["supports_timeframes"]) == {"ADX", "ADX+DI[1]"}
    assert {"RSI", "EMA20"} <= set(info["daily_only"])


def _prepare_files(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    meta = {
        "data": {
            "fields": [
                {"name": "RSI|1D", "type": "number"},
                {"name": "ADX|60", "type": "number"},
                {"name": "sector", "type": "text"},
            ]
        }
    }
    (base / "metainfo.json").write_text(json.dumps(meta))
    scan = {"count": 1, "data": [{"s": "AAA", "d": [55, 30, "x"]}]}
    (base / "scan.json").write_text(json.dumps(scan))
    tsv = (
        "field\ttv_type\tstatus\tsample_value\n"
        "RSI|1D\tnumber\tok\t55\n"
        "ADX|60\tnumber\tok\t30\n"
        "sector\ttext\tok\tx\n"
    )
    (base / "field_status.tsv").write_text(tsv)


def test_generate_filter_options(tmp_path: Path) -> None:
    runner = CliRunner()
    market_dir = tmp_path / "results" / "crypto"
    _prepare_files(market_dir)
    result = runner.invoke(
        cli,
        [
            "generate",
            "--market",
            "crypto",
            "--indir",
            str(tmp_path / "results"),
            "--outdir",
            str(tmp_path),
            "--include-type",
            "numeric",
            "--only-timeframe-supported",
        ],
    )
    assert result.exit_code == 0, result.output
    spec = yaml.safe_load((tmp_path / "crypto.yaml").read_text())
    props = spec["components"]["schemas"]["CryptoFields"]["properties"]
    assert "sector" not in props
    assert "ADX|60" in props
    assert "RSI|1D" in props
    assert "description" in spec["info"]
    assert "include=numeric" in spec["info"]["description"]
