from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from requests import Session
from requests.exceptions import RequestException

from src.api.data_fetcher import choose_tickers
from src.api.tradingview_api import TradingViewAPI
from src.cli import cli
from src.generator.yaml_generator import _timeframe_desc, _describe_field
from src.models import MetaInfoResponse, TVField


class FailingSession(Session):
    def request(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        raise RequestException("boom")


def test_timeframe_and_indicator_helpers() -> None:
    assert _timeframe_desc("1") == "1-minute"
    assert _timeframe_desc("60") == "1-hour"
    assert _timeframe_desc("120") == "2-hour"
    assert _timeframe_desc("1440") == "1-day"
    assert _describe_field("EMA20|60").startswith("Exponential Moving Average")


def test_choose_tickers_with_scan_and_model() -> None:
    fields = [TVField(name="s", type="string")]
    scan = {"data": [{"s": "AAA", "d": ["TICK"]}]}
    meta = MetaInfoResponse(data=fields)
    result = choose_tickers(
        {"fields": [f.model_dump(by_alias=True) for f in meta.data], "scan": scan}
    )
    assert result == ["TICK"]


def test_tradingview_request_error() -> None:
    api = TradingViewAPI(session=FailingSession())
    with pytest.raises(RequestException):
        api.scan("crypto", {})


def test_cli_scan_invalid_schema(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        json={"foo": "bar"},
    )
    result = runner.invoke(
        cli,
        ["scan", "--symbols", "BTCUSD", "--columns", "close", "--market", "crypto"],
    )
    assert result.exit_code != 0
    assert "validation error" in result.output


def test_cli_preview_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(": bad")
    runner = CliRunner()
    result = runner.invoke(cli, ["preview", "--spec", str(bad)])
    assert result.exit_code != 0


def test_cli_preview_no_fields(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text("openapi: 3.1.0\ncomponents: {schemas: {Foo: {}}}")
    runner = CliRunner()
    result = runner.invoke(cli, ["preview", "--spec", str(spec)])
    assert result.exit_code != 0
