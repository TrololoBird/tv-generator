import json
from pathlib import Path

import pytest
import requests

from src.api.data_fetcher import (
    fetch_metainfo,
    full_scan,
    save_json,
    choose_tickers,
    MAX_COLUMNS_PER_SCAN,
)


def test_fetch_metainfo(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        json={"fields": []},
    )
    assert fetch_metainfo("stocks") == {"fields": []}


def test_fetch_metainfo_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        status_code=500,
    )
    with pytest.raises(ValueError):
        fetch_metainfo("stocks")


def test_fetch_metainfo_invalid_json(tv_api_mock):
    tv_api_mock.post(
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
    first = {"count": 1, "data": [{"s": "AAA", "d": list(range(MAX_COLUMNS_PER_SCAN))}]}
    second = {"count": 1, "data": [{"s": "AAA", "d": [99]}]}
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        [{"json": first}, {"json": second}],
    )
    columns = [f"c{i}" for i in range(MAX_COLUMNS_PER_SCAN + 1)]
    result = full_scan("stocks", ["AAA"], columns)
    assert result["data"][0]["d"] == list(range(MAX_COLUMNS_PER_SCAN)) + [99]


def test_full_scan_batch_reorder(tv_api_mock):
    first = {
        "count": 2,
        "data": [
            {"s": "AAA", "d": [1]},
            {"s": "BBB", "d": [3]},
        ],
    }
    second = {
        "count": 2,
        "data": [
            {"s": "BBB", "d": [4]},
            {"s": "AAA", "d": [2]},
        ],
    }
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        [{"json": first}, {"json": second}],
    )
    columns = [f"c{i}" for i in range(MAX_COLUMNS_PER_SCAN + 1)]
    result = full_scan("stocks", ["AAA", "BBB"], columns)
    assert [row["s"] for row in result["data"]] == ["AAA", "BBB"]
    assert result["data"][0]["d"] == [1, 2]
    assert result["data"][1]["d"] == [3, 4]


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


def test_choose_tickers_from_index_names() -> None:
    meta = {
        "data": {
            "fields": [{"name": "s", "type": "string"}],
            "index": {"names": ["AAA", "BBB", "CCC"]},
        }
    }
    assert choose_tickers(meta, limit=2) == ["AAA", "BBB"]


def test_choose_tickers_error() -> None:
    meta = {"fields": [{"name": "close", "type": "number"}]}
    with pytest.raises(ValueError):
        choose_tickers(meta)
