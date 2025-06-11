import pytest
from src.utils.payload import build_scan_payload


def test_build_scan_payload_basic():
    payload = build_scan_payload(["A"], ["close"])
    assert payload["symbols"]["tickers"] == ["A"]
    assert payload["columns"] == ["close"]
    assert "filter" not in payload


def test_build_scan_payload_filters():
    payload = build_scan_payload(
        ["A"],
        ["close"],
        {"foo": "bar"},
        {"baz": 1},
        {"sortBy": "close"},
        {"from": 0},
    )
    assert payload["filter"] == {"foo": "bar"}
    assert payload["filter2"] == {"baz": 1}
    assert payload["sort"] == {"sortBy": "close"}
    assert payload["range"] == {"from": 0}


def test_build_scan_payload_invalid_filter_type():
    with pytest.raises(TypeError) as exc:
        build_scan_payload(["A"], ["close"], ["not", "a", "dict"])  # type: ignore[arg-type]
    assert "filter must be a dict" in str(exc.value)


def test_build_scan_payload_empty_symbols():
    with pytest.raises(ValueError) as exc:
        build_scan_payload([], ["close"])
    assert "symbols list cannot be empty" in str(exc.value)


def test_build_scan_payload_duplicate_columns():
    with pytest.raises(ValueError) as exc:
        build_scan_payload(["A"], ["close", "close"])
    assert "contains duplicates" in str(exc.value)
