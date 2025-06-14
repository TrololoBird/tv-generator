import pandas as pd
from src.api.data_manager import build_field_status
from src.models import MetaInfoResponse, TVField


def _meta(fields):
    return MetaInfoResponse(data=[TVField(name=f[0], type=f[1]) for f in fields])


def test_build_field_status_basic():
    meta = _meta(
        [
            ("f1", "integer"),
            ("f2", "string"),
            ("f3", "float"),
        ]
    )
    scan = {"data": [{"d": [1, "", None]}, {"d": [2, "", None]}]}
    df = build_field_status(meta, scan)
    expected = pd.DataFrame(
        {
            "field": ["f1", "f2", "f3"],
            "tv_type": ["integer", "string", "float"],
            "status": ["ok", "empty", "null"],
            "sample_value": [1, "", ""],
        }
    )
    pd.testing.assert_frame_equal(df.reset_index(drop=True), expected)


def test_build_field_status_missing():
    meta = _meta([("f1", "integer"), ("f2", "string")])
    scan = {"data": [{"d": [1]}, {"d": [2]}]}
    df = build_field_status(meta, scan)
    assert list(df["status"]) == ["ok", "error"]


def test_build_field_status_full_ok():
    meta = _meta([("f1", "integer"), ("f2", "string")])
    scan = {"data": [{"d": [1, "a"]}, {"d": [2, "b"]}]}
    df = build_field_status(meta, scan)
    assert list(df["status"]) == ["ok", "ok"]
    assert list(df["sample_value"]) == [1, "a"]


def test_build_field_status_empty_row_error():
    meta = _meta([("f1", "integer")])
    scan = {"data": [{"d": []}]}
    df = build_field_status(meta, scan)
    assert df.loc[0, "status"] == "error"


def test_build_field_status_all_null():
    meta = _meta([("f1", "integer")])
    scan = {"data": [{"d": [None]}, {"d": [None]}]}
    df = build_field_status(meta, scan)
    assert df.loc[0, "status"] == "null"


def test_build_field_status_no_rows():
    meta = _meta([("f1", "integer")])
    scan = {"data": []}
    df = build_field_status(meta, scan)
    assert df.loc[0, "status"] == "null"


def test_build_field_status_mixed_empty():
    meta = _meta([("f1", "integer")])
    scan = {"data": [{"d": [None]}, {"d": [""]}]}
    df = build_field_status(meta, scan)
    assert df.loc[0, "status"] == "empty"
