import pytest
from src.api.data_fetcher import full_scan


def test_full_scan_filters_invalid_fields(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        json={
            "fields": [{"name": "close", "type": "number"}],
            "filter": {"fields": [{"name": "open", "type": "number"}]},
        },
    )
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={"count": 1, "data": [{"s": "AAA", "d": [1, 2]}]},
    )
    result = full_scan("stocks", ["AAA"], ["close", "open", "bad"])
    assert tv_api_mock.request_history[-1].json()["columns"] == ["close", "open"]
    assert result["columns"] == ["close", "open"]


def test_full_scan_all_invalid(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/metainfo",
        json={"fields": [{"name": "close", "type": "number"}]},
    )
    with pytest.raises(ValueError):
        full_scan("stocks", ["AAA"], ["bad"])
    # ensure scan endpoint not called
    assert len(tv_api_mock.request_history) == 1
