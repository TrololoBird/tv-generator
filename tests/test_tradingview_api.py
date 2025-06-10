import pytest
from src.api.tradingview_api import TradingViewAPI


@pytest.mark.parametrize(
    "scope",
    [
        "crypto",
        "forex",
        "futures",
        "america",
        "bond",
        "cfd",
        "coin",
        "stocks",
    ],
)
def test_scan_and_metainfo(tv_api_mock, scope):
    tv_api_mock.get(
        f"https://scanner.tradingview.com/{scope}/scan",
        json={"data": []},
    )
    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/metainfo",
        json={"fields": []},
    )

    api = TradingViewAPI()
    assert api.scan(scope, {}) == {"data": []}
    assert api.metainfo(scope, {"query": ""}) == {"fields": []}


def test_scan_error(tv_api_mock):
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        status_code=404,
    )
    api = TradingViewAPI()
    with pytest.raises(Exception):
        api.scan("crypto", {})


def test_scan_invalid_json(tv_api_mock):
    tv_api_mock.get(
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
        api.metainfo("crypto", {"query": ""})


def test_scan_invalid_scope():
    api = TradingViewAPI()
    with pytest.raises(ValueError):
        api.scan("invalid", {})
