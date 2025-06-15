import json
from pathlib import Path
from click.testing import CliRunner
from pydantic import ValidationError

from src.cli import cli
from src.api.tradingview_api import TradingViewAPI


def test_metainfo_invalid_schema(monkeypatch):
    runner = CliRunner()

    def fake_request(self, scope: str, endpoint: str, method: str, payload: dict):
        data = {"foo": "bar"}
        path = Path("results") / scope / "metainfo.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return data

    monkeypatch.setattr(TradingViewAPI, "_request", fake_request)

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli, ["metainfo", "--query", "crypto", "--market", "crypto"]
        )
        assert result.exit_code != 0
        assert "1 validation error for MetaInfoResponse" in result.output
        saved = Path("results/crypto/metainfo.json")
        assert saved.exists()
        assert json.loads(saved.read_text()) == {"foo": "bar"}
