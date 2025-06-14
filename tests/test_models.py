import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import MetaInfoResponse, ScanResponse

ASSETS = Path(__file__).parent / "assets"


def test_metainfo_asset_validation() -> None:
    data = json.loads((ASSETS / "coin_metainfo.json").read_text())
    model = MetaInfoResponse.parse_obj(data)
    assert model.fields[0].n == "close"


def test_scan_asset_validation() -> None:
    data = json.loads((ASSETS / "coin_scan.json").read_text())
    model = ScanResponse.parse_obj(data)
    assert model.count == 2
    assert model.data[0].s.startswith("BINANCE")


def test_scan_invalid() -> None:
    with pytest.raises(ValidationError):
        ScanResponse.parse_obj({"data": [{"d": []}]})


def test_unknown_field_type_fallback() -> None:
    data = {"fields": [{"name": "foo", "type": "mystery"}]}
    model = MetaInfoResponse.parse_obj(data)
    assert model.fields[0].t == "mystery"
