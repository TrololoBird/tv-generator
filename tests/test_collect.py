from click.testing import CliRunner

from src.cli import cli
from src.api.tradingview_api import TradingViewAPI


def test_collect_no_tickers(monkeypatch):
    runner = CliRunner()

    def fake_meta(self, scope, payload):
        return {"data": {"fields": [], "index": {"names": []}}}

    def fake_scan(self, scope, payload):
        return {"data": []}

    monkeypatch.setattr(TradingViewAPI, "metainfo", fake_meta)
    monkeypatch.setattr(TradingViewAPI, "scan", fake_scan)

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["collect-full", "--scope", "crypto", "--tickers", ""],
        )
        assert result.exit_code == 2
        assert "No tickers" in result.output


def test_collect_custom_tickers(monkeypatch):
    runner = CliRunner()
    payload_holder = {}

    def fake_meta(self, scope, payload):
        return {"data": {"fields": [], "index": {"names": []}}}

    def fake_scan(self, scope, payload):
        payload_holder["payload"] = payload
        return {"data": []}

    monkeypatch.setattr(TradingViewAPI, "metainfo", fake_meta)
    monkeypatch.setattr(TradingViewAPI, "scan", fake_scan)

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["collect-full", "--scope", "crypto", "--tickers", "A,B"],
        )
        assert result.exit_code == 0
        assert payload_holder["payload"]["symbols"]["tickers"] == ["A", "B"]
