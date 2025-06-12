from click.testing import CliRunner
from pathlib import Path

from src.cli import cli


def test_collect_full(monkeypatch):
    runner = CliRunner()

    meta = {
        "fields": [{"name": "c1", "type": "integer"}],
        "index": {"names": ["AAA", "BBB"]},
    }
    scan_args = {}

    monkeypatch.setattr("src.cli.fetch_metainfo", lambda scope: meta)

    def fake_scan(scope, tickers, columns):
        scan_args["tickers"] = tickers
        scan_args["columns"] = columns
        return {"data": []}

    monkeypatch.setattr("src.cli.full_scan", fake_scan)
    monkeypatch.setattr("src.cli.save_json", lambda d, p: Path(p).write_text("{}"))

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect-full", "--scope", "crypto"])
        assert result.exit_code == 0
        assert scan_args["tickers"] == ["AAA", "BBB"]
        assert scan_args["columns"] == ["c1"]
        market_dir = Path("results/crypto")
        assert (market_dir / "metainfo.json").exists()
        assert (market_dir / "scan.json").exists()
        assert (market_dir / "field_status.tsv").exists()
