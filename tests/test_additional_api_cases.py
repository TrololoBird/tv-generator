import pytest
import requests
import yaml

from src.api.tradingview_api import TradingViewAPI
from src.api import data_fetcher
from src.api.data_fetcher import fetch_metainfo, full_scan
from src.api.data_manager import build_field_status
from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField


def test_scan_request_exception(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        exc=requests.exceptions.ConnectTimeout,
    )
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        exc=requests.exceptions.ConnectTimeout,
    )
    api = TradingViewAPI()
    with pytest.raises(requests.exceptions.RequestException):
        api.scan("crypto", {})


def test_fetch_metainfo_invalid_structure(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        json=[1, 2, 3],
    )
    with pytest.raises(ValueError):
        fetch_metainfo("stocks")


def test_full_scan_auto_tickers(tv_api_mock, monkeypatch):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        json={"fields": [{"name": "symbol", "type": "string"}]},
    )
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={"count": 1, "data": [{"s": "AAA", "d": [1]}]},
    )
    monkeypatch.setattr(data_fetcher, "choose_tickers", lambda meta, limit=10: ["AAA"])
    result = full_scan("stocks", ["AUTO"], ["c1"])
    assert result == {"count": 1, "data": [{"s": "AAA", "d": [1]}]}


def test_full_scan_invalid_json(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        text="oops",
    )
    with pytest.raises(ValueError):
        full_scan("stocks", ["AAA"], ["c1"])


def test_build_field_status_with_columns():
    meta = MetaInfoResponse(
        data=[TVField(name="a", type="integer"), TVField(name="b", type="integer")]
    )
    scan = {"columns": ["b", "a"], "data": [{"s": "AAA", "d": [1, 2]}]}
    df = build_field_status(meta, scan)
    assert list(df["sample_value"]) == [2, 1]


def test_generate_yaml_server_url():
    meta = MetaInfoResponse(data=[TVField(name="close", type="integer")])
    yaml_str = generate_yaml("crypto", meta, None, server_url="http://example.com")
    data = yaml.safe_load(yaml_str)
    assert data["servers"][0]["url"] == "http://example.com"
