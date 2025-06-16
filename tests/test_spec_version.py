import json
from pathlib import Path

import yaml

from src.spec.generator import generate_spec_for_market
from src.meta import versioning


def _create_metainfo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "data": {
            "fields": [{"name": "close", "type": "integer"}],
            "index": {"names": ["AAA"]},
        }
    }
    path.write_text(json.dumps(data))
    scan = {"count": 1, "data": [{"s": "AAA", "d": [1]}]}
    (path.parent / "scan.json").write_text(json.dumps(scan))
    tsv = "field\ttv_type\tstatus\tsample_value\nclose\tinteger\tok\t1\n"
    (path.parent / "field_status.tsv").write_text(tsv)


def test_spec_uses_current_version(tmp_path, monkeypatch) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nversion = '2.0.0'\n")
    monkeypatch.setattr(versioning, "DEFAULT_PYPROJECT_PATH", pyproject)

    indir = tmp_path / "results"
    _create_metainfo(indir / "crypto" / "metainfo.json")
    outdir = tmp_path / "specs"

    generate_spec_for_market("crypto", indir, outdir)

    spec = yaml.safe_load((outdir / "crypto.yaml").read_text())
    assert spec["info"]["version"] == versioning.get_current_version()
