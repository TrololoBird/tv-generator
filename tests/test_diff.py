from click.testing import CliRunner
from pathlib import Path
import json

from src.cli import cli


def _create_market(dir_path: Path, fields: list[tuple[str, str]]) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    meta = {"fields": [{"name": f, "type": t} for f, t in fields]}
    (dir_path / "metainfo.json").write_text(json.dumps(meta))
    scan = {"count": 1, "data": [{"s": "AAA", "d": [1 for _ in fields]}]}
    (dir_path / "scan.json").write_text(json.dumps(scan))
    lines = ["field\ttv_type\tstatus\tsample_value"]
    for f, t in fields:
        lines.append(f"{f}\t{t}\tok\t1")
    (dir_path / "field_status.tsv").write_text("\n".join(lines) + "\n")


def test_diff_added_removed_changed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _create_market(Path("cache/crypto"), [("close", "integer"), ("open", "text")])
        _create_market(Path("results/crypto"), [("close", "text"), ("high", "integer")])
        result = runner.invoke(cli, ["update", "--market", "crypto", "--diff"])
        assert result.exit_code == 0, result.output
        assert "[+] Added field: high" in result.output
        assert "[-] Removed field: open" in result.output
        assert "[*] Changed: close" in result.output
