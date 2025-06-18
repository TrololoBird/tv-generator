from importlib import reload

import pytest

import importlib

import src.config as config
import src.api.tradingview_api as api_module


def test_api_uses_token(monkeypatch) -> None:
    monkeypatch.setenv("TV_API_TOKEN", "x" * 20)
    reload(config)
    importlib.reload(api_module)
    api = api_module.TradingViewAPI()
    assert (
        api.session.headers.get("Authorization")
        == f"Bearer {api_module.settings.tv_api_token}"
    )


def test_token_validation(monkeypatch) -> None:
    monkeypatch.setenv("TV_API_TOKEN", "short")
    with pytest.raises(ValueError):
        reload(config)
