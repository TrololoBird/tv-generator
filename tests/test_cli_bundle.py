from pathlib import Path
import json
import yaml
from click.testing import CliRunner

from src.cli import cli

ROOT_SPECS = Path(__file__).resolve().parents[1] / "specs"


def _copy_specs(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in ROOT_SPECS.glob("*.yaml"):
        dest.joinpath(f.name).write_text(f.read_text())


def test_cli_bundle_json() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _copy_specs(Path("specs"))
        result = runner.invoke(cli, ["bundle"])
        assert result.exit_code == 0, result.output
        out = Path("bundle.json")
        data = json.loads(out.read_text())
        assert "crypto" in data
        assert isinstance(data["crypto"], dict)


def test_cli_bundle_yaml() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _copy_specs(Path("specs"))
        out_dir = Path("output")
        result = runner.invoke(
            cli,
            ["bundle", "--format", "yaml", "--outfile", str(out_dir / "bundle.yaml")],
        )
        assert result.exit_code == 0, result.output
        out_file = out_dir / "bundle.yaml"
        data = yaml.safe_load(out_file.read_text())
        assert "stocks" in data
        assert isinstance(data["stocks"], dict)
