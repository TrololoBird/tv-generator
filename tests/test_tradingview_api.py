import requests_mock

from src.api.tradingview_api import TradingViewAPI


def test_scan_and_metainfo():
    with requests_mock.Mocker() as m:
        m.post(
            "https://scanner.tradingview.com/crypto/scan",
            json={"data": []},
        )
        m.post(
            "https://scanner.tradingview.com/crypto/metainfo",
            json={"fields": []},
        )

        api = TradingViewAPI()
        assert api.scan("crypto", {}) == {"data": []}
        assert api.metainfo("crypto") == {"fields": []}
