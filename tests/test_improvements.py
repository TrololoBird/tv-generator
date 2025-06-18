import importlib
import logging
from importlib import reload

import pytest
import requests

import src.config as config
import src.api.tradingview_api as api_module
from src.data import collector
from src.exceptions import TVDataError, TVConnectionError


def test_request_logging_sanitized(tv_api_mock, caplog):
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/search",
        status_code=500,
        text="secret-body",
        reason="Server Error",
    )
    api = api_module.TradingViewAPI()
    with caplog.at_level(logging.INFO):
        with pytest.raises(TVConnectionError):
            api.search("crypto", {})
    assert not any("secret-body" in r.getMessage() for r in caplog.records)


def test_api_rejects_short_token(monkeypatch):
    monkeypatch.setenv("TV_API_TOKEN", "x" * 20)
    reload(config)
    importlib.reload(api_module)
    monkeypatch.setattr(api_module.settings, "tv_api_token", "short")
    with pytest.raises(ValueError):
        api_module.TradingViewAPI()


def test_refresh_market_error(monkeypatch, tmp_path):
    def fail_fetch(*_args, **_kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(collector, "fetch_metainfo", fail_fetch)
    with pytest.raises(TVDataError):
        collector.refresh_market("crypto", tmp_path)
