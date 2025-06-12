import json
from pathlib import Path

import pytest
import requests

from src.api.data_fetcher import fetch_metainfo, full_scan, save_json


def test_fetch_metainfo(tv_api_mock):
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/metainfo",
        json={"fields": []},
    )
    assert fetch_metainfo("stocks") == {"fields": []}


def test_fetch_metainfo_error(tv_api_mock):
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/metainfo",
        status_code=500,
    )
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_metainfo("stocks")


def test_fetch_metainfo_invalid_json(tv_api_mock):
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/metainfo",
        text="not-json",
    )
    with pytest.raises(ValueError):
        fetch_metainfo("stocks")


def test_full_scan_single_batch(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={"count": 1, "data": [{"s": "AAA", "d": [1, 2]}]},
    )
    result = full_scan("stocks", ["AAA"], ["c1", "c2"])
    assert result["data"][0]["d"] == [1, 2]


def test_full_scan_multi_batch(tv_api_mock):
    first = {"count": 1, "data": [{"s": "AAA", "d": list(range(20))}]}
    second = {"count": 1, "data": [{"s": "AAA", "d": [99]}]}
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        [{"json": first}, {"json": second}],
    )
    columns = [f"c{i}" for i in range(21)]
    result = full_scan("stocks", ["AAA"], columns)
    assert result["data"][0]["d"] == list(range(20)) + [99]


def test_full_scan_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        status_code=404,
    )
    with pytest.raises(requests.exceptions.HTTPError):
        full_scan("stocks", ["AAA"], ["c1"])


def test_save_json(tmp_path: Path):
    data = {"a": 1}
    out = tmp_path / "out.json"
    save_json(data, out)
    assert json.loads(out.read_text()) == data
