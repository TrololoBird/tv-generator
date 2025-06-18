import logging
import pytest
from pydantic import ValidationError
from src.api.tradingview_api import TradingViewAPI
from src.exceptions import TVConnectionError


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
    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/scan",
        json={"count": 0, "data": []},
    )
    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/metainfo",
        json={"fields": []},
    )

    api = TradingViewAPI()
    scan = api.scan(scope, {})
    assert scan.count == 0
    assert scan.data == []
    assert api.metainfo(scope, {"query": ""}) == {"fields": []}

    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/search",
        json={"items": []},
    )
    assert api.search(scope, {}) == {"items": []}

    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/history",
        json={"bars": []},
    )
    assert api.history(scope, {}) == {"bars": []}

    tv_api_mock.post(
        f"https://scanner.tradingview.com/{scope}/summary",
        json={"summary": []},
    )
    assert api.summary(scope, {}) == {"summary": []}


def test_scan_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        status_code=404,
    )
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        json={"count": 0, "data": []},
    )
    api = TradingViewAPI()
    result = api.scan("crypto", {})
    assert result.count == 0


def test_scan_invalid_json(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        text="not-json",
    )
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        json={"count": 0, "data": []},
    )
    api = TradingViewAPI()
    result = api.scan("crypto", {})
    assert result.count == 0


def test_scan_invalid_schema(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        json={"foo": "bar"},
    )
    api = TradingViewAPI()
    with pytest.raises(ValidationError):
        api.scan("crypto", {})


@pytest.mark.parametrize("endpoint", ["search", "history", "summary"])
def test_endpoint_error(tv_api_mock, endpoint):
    tv_api_mock.post(
        f"https://scanner.tradingview.com/crypto/{endpoint}",
        status_code=500,
    )
    api = TradingViewAPI()
    method = getattr(api, endpoint)
    with pytest.raises(TVConnectionError):
        method("crypto", {})


@pytest.mark.parametrize("endpoint", ["search", "history", "summary"])
def test_endpoint_invalid_json(tv_api_mock, endpoint):
    tv_api_mock.post(
        f"https://scanner.tradingview.com/crypto/{endpoint}",
        text="not-json",
    )
    api = TradingViewAPI()
    method = getattr(api, endpoint)
    with pytest.raises(ValueError):
        method("crypto", {})


@pytest.mark.parametrize("endpoint", ["search", "history", "summary"])
def test_endpoint_invalid_schema(tv_api_mock, endpoint):
    tv_api_mock.post(
        f"https://scanner.tradingview.com/crypto/{endpoint}",
        json=[1, 2, 3],
    )
    api = TradingViewAPI()
    method = getattr(api, endpoint)
    with pytest.raises(ValueError):
        method("crypto", {})


def test_metainfo_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        status_code=404,
    )
    api = TradingViewAPI()
    with pytest.raises(TVConnectionError) as exc:
        api.metainfo("crypto", {"query": ""})
    assert exc.value.status == 404


def test_metainfo_invalid_schema(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        json={"foo": "bar"},
    )
    api = TradingViewAPI()
    with pytest.raises(ValidationError):
        api.metainfo("crypto", {"query": ""})


def test_scan_invalid_scope():
    api = TradingViewAPI()
    with pytest.raises(ValueError):
        api.scan("invalid", {})


def test_invalid_json_logged(tv_api_mock, caplog):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/search",
        text="bad json",
    )
    api = TradingViewAPI()
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            api.search("crypto", {})
    assert any(
        "Invalid JSON" in r.getMessage() and "bad json" in r.getMessage()
        for r in caplog.records
    )
