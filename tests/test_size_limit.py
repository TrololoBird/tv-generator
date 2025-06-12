from pathlib import Path
import json
from click.testing import CliRunner
from src.cli import cli

ASSETS = Path(__file__).parent / "assets"


def _prepare(tmp_dir: Path) -> dict:
    meta = json.loads((ASSETS / "coin_metainfo.json").read_text())
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "metainfo.json").write_text(json.dumps(meta))
    scan = json.loads((ASSETS / "coin_scan.json").read_text())
    (tmp_dir / "scan.json").write_text(json.dumps(scan))
    lines = ["field\ttv_type\tstatus\tsample_value"]
    for field in meta["data"]["fields"]:
        lines.append(f"{field['name']}\t{field['type']}\tok\t0")
    (tmp_dir / "field_status.tsv").write_text("\n".join(lines))
    return meta


def test_size_limit() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        market_dir = Path("results") / "coin"
        _prepare(market_dir)
        result = runner.invoke(
            cli,
            [
                "generate",
                "--scope",
                "coin",
                "--indir",
                str(Path("results")),
                "--outdir",
                str(Path(".")),
            ],
        )
        assert result.exit_code == 0, result.output
        spec_file = Path("coin.yaml")
        assert spec_file.exists()
        assert spec_file.stat().st_size < 1_048_576
