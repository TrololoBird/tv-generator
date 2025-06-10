import pytest
from src.api.tradingview_api import TradingViewAPI


def test_scan_and_metainfo(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        json={"data": []},
    )
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        json={"fields": []},
    )

    api = TradingViewAPI()
    assert api.scan("crypto", {}) == {"data": []}
    assert api.metainfo("crypto") == {"fields": []}


def test_scan_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        status_code=404,
    )
    api = TradingViewAPI()
    with pytest.raises(Exception):
        api.scan("crypto", {})


def test_scan_invalid_json(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        text="not-json",
    )
    api = TradingViewAPI()
    with pytest.raises(ValueError):
        api.scan("crypto", {})


def test_metainfo_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        status_code=404,
    )
    api = TradingViewAPI()
    with pytest.raises(Exception):
        api.metainfo("crypto")
