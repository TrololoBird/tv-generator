from pathlib import Path
import json
import yaml
import pandas as pd
from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField

ASSETS = Path(__file__).parent / "assets"


def _load_meta() -> MetaInfoResponse:
    data = json.loads((ASSETS / "coin_metainfo.json").read_text())
    fields = [
        TVField(name=f["name"], type=f.get("type", "string"), flags=f.get("flags"))
        for f in data["data"]["fields"]
    ]
    return MetaInfoResponse(data=fields)


def test_field_coverage() -> None:
    meta = _load_meta()
    tsv = pd.DataFrame(columns=["field", "tv_type", "status", "sample_value"])
    yaml_str = generate_yaml("coin", meta, tsv, None)
    spec = yaml.safe_load(yaml_str)
    props = spec["components"]["schemas"]["CoinFields"]["properties"]
    yaml_fields = set(props.keys())
    expected = {
        f.n for f in meta.data if not {"deprecated", "private"} & set(f.flags or [])
    }
    assert yaml_fields == expected
