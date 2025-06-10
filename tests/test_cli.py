from pathlib import Path

import yaml
from click.testing import CliRunner

from src.cli import cli


def _create_field_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("field\tstatus\tvalue\n")
        f.write("close\tok\t1\n")
        f.write("open\tok\tabc\n")


def test_cli_scan(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post("https://scanner.tradingview.com/crypto/scan", json={"data": []})
    result = runner.invoke(cli, ["scan", "--market", "crypto"])
    assert result.exit_code == 0
    assert "data" in result.output


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "TradingView" in result.output


def test_generate_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--market" in result.output


def test_cli_generate_and_validate(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        market_dir = Path("results") / "crypto"
        _create_field_status(market_dir / "field_status.tsv")

        out_file = Path("spec.yaml")
        result = runner.invoke(
            cli,
            [
                "generate",
                "--market",
                "crypto",
                "--output",
                str(out_file),
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["validate", "--spec", str(out_file)])
        assert result.exit_code == 0
        data = yaml.safe_load(out_file.read_text())
        assert "/crypto/scan" in data["paths"]
