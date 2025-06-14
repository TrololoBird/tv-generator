from pathlib import Path

from click.testing import CliRunner
import yaml
from openapi_spec_validator import validate_spec

from src.cli import cli


def test_e2e_collect_and_generate(tmp_path, monkeypatch):
    meta = {
        "data": {
            "fields": [
                {"name": "field1", "type": "integer"},
                {"name": "field2", "type": "number"},
                {"name": "field3", "type": "text"},
                {"name": "field4", "type": "boolean"},
                {"name": "field5", "type": "time"},
            ],
            "index": {"names": ["AAA", "BBB"]},
        }
    }
    scan = {
        "count": 2,
        "data": [
            {"s": "AAA", "d": [1, 1.1, "a", True, "2024-01-01T00:00:00Z"]},
            {"s": "BBB", "d": [2, 2.2, "b", False, "2024-01-02T00:00:00Z"]},
        ],
    }

    monkeypatch.setattr("src.cli.fetch_metainfo", lambda scope: meta)
    monkeypatch.setattr("src.cli.full_scan", lambda scope, tickers, columns: scan)

    runner = CliRunner()
    with runner.isolated_filesystem():
        out_dir = Path("tmp_res")
        result = runner.invoke(
            cli,
            ["collect", "--market", "crypto", "--outdir", str(out_dir)],
        )
        assert result.exit_code == 0
        market_dir = out_dir / "crypto"
        assert (market_dir / "metainfo.json").exists()
        assert (market_dir / "scan.json").exists()
        assert (market_dir / "field_status.tsv").exists()

        spec_file = out_dir / "crypto.yaml"
        result = runner.invoke(
            cli,
            [
                "generate",
                "--market",
                "crypto",
                "--indir",
                str(out_dir),
                "--outdir",
                str(out_dir),
            ],
        )
        assert result.exit_code == 0

        spec = yaml.safe_load(spec_file.read_text())
        validate_spec(spec)
        fields = spec["components"]["schemas"]["CryptoFields"]["properties"]
        assert set(fields) == {
            "field1",
            "field2",
            "field3",
            "field4",
            "field5",
        }
