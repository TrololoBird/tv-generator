import pytest

from src.utils.payload import build_scan_payload


def test_build_scan_payload_basic():
    payload = build_scan_payload(["A"], ["close"])
    assert payload["symbols"]["tickers"] == ["A"]
    assert payload["columns"] == ["close"]
    assert "filter" not in payload


def test_build_scan_payload_filters():
    payload = build_scan_payload(["A"], ["close"], {"foo": "bar"})
    assert payload["filter"] == {"foo": "bar"}
