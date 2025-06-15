from pathlib import Path
from click.testing import CliRunner
from src.cli import cli


def test_cli_docs() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["docs"])
        assert result.exit_code == 0, result.output
        out = Path("README.generated.md")
        assert out.exists()
        text = out.read_text()
        assert "generate" in text
