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
                "--market",
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


def test_generate_to_specs_dir() -> None:
    """CLI 'generate' creates specs/coin.yaml under 1 MB using fixture data."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        market_dir = Path("results") / "coin"
        _prepare(market_dir)
        result = runner.invoke(
            cli,
            [
                "generate",
                "--market",
                "coin",
                "--indir",
                str(Path("results")),
            ],
        )
        assert result.exit_code == 0, result.output
        spec_file = Path("specs/coin.yaml")
        assert spec_file.exists()
        assert spec_file.stat().st_size < 1_048_576


def test_collect_full_auto_tickers(monkeypatch) -> None:
    runner = CliRunner()

    meta = json.loads((ASSETS / "coin_metainfo.json").read_text())
    sent: dict[str, list[str]] = {}

    monkeypatch.setattr("src.cli.fetch_metainfo", lambda scope: meta)

    def fake_scan(scope: str, tickers: list[str], columns: list[str]) -> dict:
        sent["tickers"] = tickers
        return {"data": []}

    monkeypatch.setattr("src.cli.full_scan", fake_scan)
    monkeypatch.setattr("src.cli.save_json", lambda d, p: Path(p).write_text("{}"))

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--market", "coin"])
        assert result.exit_code == 0, result.output
        assert len(sent["tickers"]) <= 10


def test_repo_specs_size() -> None:
    """All repository YAML specs should be under 1 MB."""
    specs_dir = Path(__file__).resolve().parents[1] / "specs"
    for spec in specs_dir.glob("*.yaml"):
        assert (
            spec.stat().st_size < 1_048_576
        ), f"{spec.name} is {spec.stat().st_size} bytes, exceeds 1 MB"
