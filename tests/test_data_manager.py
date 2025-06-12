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
