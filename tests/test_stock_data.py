import pytest
from src.api.stock_data import fetch_recommendation, fetch_stock_value


def test_fetch_recommendation(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={"data": [{"d": ["strong_buy"]}]},
    )
    assert fetch_recommendation("AAPL") == "strong_buy"


def test_fetch_stock_value(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={"data": [{"d": [150.0]}]},
    )
    assert fetch_stock_value("AAPL") == 150.0


def test_fetch_stock_value_error(tv_api_mock):
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/scan",
        json={},
    )
    with pytest.raises(ValueError) as exc:
        fetch_stock_value("AAPL")
    assert "unavailable" in str(exc.value)
