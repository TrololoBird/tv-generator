from click.testing import CliRunner
from pathlib import Path
import json

from src.cli import cli


def _create_market(path: Path, fields: list[tuple[str, str]]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    meta = {"fields": [{"name": f, "type": t} for f, t in fields]}
    (path / "metainfo.json").write_text(json.dumps(meta))
    scan = {"count": 1, "data": [{"s": "AAA", "d": [1 for _ in fields]}]}
    (path / "scan.json").write_text(json.dumps(scan))
    lines = ["field\ttv_type\tstatus\tsample_value"]
    for f, t in fields:
        lines.append(f"{f}\t{t}\tok\t1")
    (path / "field_status.tsv").write_text("\n".join(lines) + "\n")


def _write_spec(market: str, text: str) -> Path:
    spec = Path("specs") / f"{market}.yaml"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(text)
    return spec


def test_skip_generation_when_no_changes(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _create_market(Path("results/crypto"), [("close", "integer")])
        _create_market(Path("cache/crypto"), [("close", "integer")])
        spec = _write_spec("crypto", "old: 1")

        called = False

        def fake_generate(*_a, **_kw):
            nonlocal called
            called = True
            return spec

        monkeypatch.setattr("src.cli.generate_spec_for_market", fake_generate)
        result = runner.invoke(cli, ["generate-if-needed", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        assert "No changes detected" in result.output
        assert not called
        assert spec.read_text() == "old: 1"


def test_generation_when_changed(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _create_market(Path("results/crypto"), [("close", "integer"), ("open", "text")])
        _create_market(Path("cache/crypto"), [("close", "integer")])
        spec = _write_spec("crypto", "old: 1")

        def fake_generate(*_a, **_kw):
            spec.write_text("new: 1")
            return spec

        monkeypatch.setattr("src.cli.generate_spec_for_market", fake_generate)
        result = runner.invoke(cli, ["generate-if-needed", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        assert "regenerating" in result.output
        assert spec.read_text() == "new: 1"


def test_yaml_updated_only_when_changed(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _create_market(Path("results/crypto"), [("close", "integer"), ("open", "text")])
        _create_market(Path("cache/crypto"), [("close", "integer")])
        spec = _write_spec("crypto", "old: 1")

        def fake_generate(*_a, **_kw):
            spec.write_text("new: 1")
            return spec

        monkeypatch.setattr("src.cli.generate_spec_for_market", fake_generate)
        result = runner.invoke(cli, ["generate-if-needed", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        first_mtime = spec.stat().st_mtime

        # run again with no changes
        _create_market(Path("cache/crypto"), [("close", "integer"), ("open", "text")])
        result = runner.invoke(cli, ["generate-if-needed", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        assert "No changes detected" in result.output
        assert spec.stat().st_mtime == first_mtime
