from click.testing import CliRunner
from pathlib import Path
import pandas as pd

from src.cli import cli


def test_update_command(tv_api_mock):
    runner = CliRunner()
    meta = {
        "fields": [{"name": "close", "type": "integer"}],
        "index": {"names": ["AAA"]},
    }
    scan = {"count": 1, "data": [{"s": "AAA", "d": [1]}], "columns": ["close"]}
    tv_api_mock.post("https://scanner.tradingview.com/crypto/metainfo", json=meta)
    tv_api_mock.post("https://scanner.tradingview.com/crypto/scan", json=scan)

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["update", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        market_dir = Path("results/crypto")
        assert (market_dir / "metainfo.json").exists()
        assert (market_dir / "scan.json").exists()
        status = market_dir / "field_status.tsv"
        assert status.exists()
        df = pd.read_csv(status, sep="\t")
        assert list(df.columns) == ["field", "tv_type", "status", "sample_value"]
        assert df.iloc[0].tolist() == ["close", "integer", "ok", 1]
