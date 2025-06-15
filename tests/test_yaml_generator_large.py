import pandas as pd
import yaml
from src.generator.yaml_generator import generate_yaml
from src.models import MetaInfoResponse, TVField


def test_generate_yaml_large() -> None:
    fields = []
    types = ["number", "text", "bool", "time", "array"]
    for i in range(120):
        fields.append(TVField(name=f"f{i}", type=types[i % len(types)]))
    meta = MetaInfoResponse(data=fields)
    yaml_str = generate_yaml("coin", meta, None)
    data = yaml.safe_load(yaml_str)

    schemas = data["components"]["schemas"]
    assert all(ref in schemas for ref in ["Num", "Str", "Bool", "Time", "Array"])

    fields_schema = data["components"]["schemas"]["CoinFields"]
    if "properties" in fields_schema:
        props = fields_schema["properties"]
    else:
        props = {}
        for part in fields_schema.get("allOf", []):
            ref = part["$ref"].split("/")[-1]
            props.update(schemas[ref]["properties"])
    assert len(props) >= 100
    assert len(props) == len(set(props))
    for v in props.values():
        assert "$ref" in v
