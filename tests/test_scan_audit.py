import json
from pathlib import Path

from src.analyzer.scan_audit import find_missing_fields


def test_find_missing_fields(tmp_path: Path) -> None:
    meta = {"data": {"fields": [{"name": "close", "type": "number"}]}}
    scan = {"columns": ["close", "Custom"], "data": [{"s": "AAA", "d": [1, 2]}]}
    meta_path = tmp_path / "metainfo.json"
    scan_path = tmp_path / "scan.json"
    meta_path.write_text(json.dumps(meta))
    scan_path.write_text(json.dumps(scan))

    missing = find_missing_fields(meta_path, scan_path)
    assert missing == [{"name": "Custom", "source": "scan", "type": "numeric"}]


def test_find_missing_fields_ignore_status(tmp_path: Path) -> None:
    meta = {"fields": [{"name": "a", "type": "number"}]}
    scan = {"columns": ["a", "b"], "data": [{"s": "A", "d": [1, 3]}]}
    status_path = tmp_path / "field_status.tsv"
    status_path.write_text("field\ttv_type\n b\tnumber\n")
    meta_path = tmp_path / "metainfo.json"
    scan_path = tmp_path / "scan.json"
    meta_path.write_text(json.dumps(meta))
    scan_path.write_text(json.dumps(scan))

    missing = find_missing_fields(meta_path, scan_path, status_path)
    assert missing == []
