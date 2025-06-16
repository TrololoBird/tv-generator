from pathlib import Path
import subprocess

import json
import yaml
from click.testing import CliRunner


from src.cli import cli


def test_cli_scan(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        json={"count": 0, "data": []},
    )
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--market",
            "crypto",
            "--filter",
            "{}",
        ],
    )
    assert result.exit_code == 0
    assert "data" in result.output


def test_cli_scan_invalid_filter(tv_api_mock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--market",
            "crypto",
            "--filter",
            "{",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid JSON in --filter" in result.output


def test_cli_scan_full_payload(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        json={"count": 0, "data": []},
    )
    payload_args = [
        "scan",
        "--symbols",
        "BTCUSD",
        "--columns",
        "close",
        "--market",
        "crypto",
        "--filter2",
        "{}",
        "--sort",
        "{}",
        "--range",
        "{}",
    ]
    result = runner.invoke(cli, payload_args)
    assert result.exit_code == 0
    assert "data" in result.output
    sent = tv_api_mock.request_history[0].json()
    assert sent["filter2"] == {}
    assert sent["sort"] == {}
    assert sent["range"] == {}


def test_cli_scan_invalid_sort(tv_api_mock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--market",
            "crypto",
            "--sort",
            "{",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid JSON in --sort" in result.output


def test_cli_scan_invalid_filter2(tv_api_mock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--market",
            "crypto",
            "--filter2",
            "{",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid JSON in --filter2" in result.output


def test_cli_scan_invalid_range(tv_api_mock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--market",
            "crypto",
            "--range",
            "{",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid JSON in --range" in result.output


def test_cli_metainfo(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        json={"fields": []},
    )
    result = runner.invoke(
        cli,
        ["metainfo", "--query", "test", "--market", "crypto"],
    )
    assert result.exit_code == 0
    assert "fields" in result.output


def test_scan_cli_missing_scope():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--symbols", "AAPL", "--columns", "close"])
    assert result.exit_code != 0
    assert "Missing option '--market'" in result.output


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "TradingView" in result.output


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"], prog_name="tvgen")
    assert result.exit_code == 0
    assert "tvgen, version" in result.output


def test_generate_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--market" in result.output
    assert "--indir" in result.output


def test_cli_generate_missing_results(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        (Path("results") / "crypto").mkdir(parents=True)
        result = runner.invoke(
            cli,
            [
                "generate",
                "--market",
                "crypto",
                "--indir",
                str(Path("results")),
                "--outdir",
                str(Path(".")),
            ],
        )
        assert result.exit_code != 0
        assert result.exception is not None
        assert "No such file" in result.output


def test_cli_scan_error(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/scan",
        status_code=500,
    )
    result = runner.invoke(
        cli,
        ["scan", "--symbols", "BTCUSD", "--columns", "close", "--market", "crypto"],
    )
    assert result.exit_code != 0
    assert result.exception is not None
    assert "TradingView request failed" in result.output


def test_cli_metainfo_error(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        status_code=500,
    )
    result = runner.invoke(cli, ["metainfo", "--query", "t", "--market", "crypto"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "TradingView request failed" in result.output


def test_cli_validate_missing_file() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--spec", "missing.yaml"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "No such file" in result.output


def test_cli_validate_invalid_yaml(tmp_path: Path) -> None:
    invalid = tmp_path / "spec.yaml"
    invalid.write_text(": bad")
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--spec", str(invalid)])
    assert result.exit_code != 0
    assert result.exception is not None


def _mock_collect_api(monkeypatch) -> None:
    meta = {
        "fields": [
            {"name": "close", "type": "integer"},
            {"name": "open", "type": "string"},
        ],
        "index": {"names": ["AAA", "BBB"]},
    }

    def fake_meta(scope: str) -> dict:
        return meta

    def fake_scan(scope: str, tickers: list[str], columns: list[str]) -> dict:
        return {
            "count": 2,
            "data": [
                {"s": tickers[0], "d": [1, "a"]},
                {"s": tickers[1] if len(tickers) > 1 else tickers[0], "d": [2, "b"]},
            ],
        }

    monkeypatch.setattr("src.cli.fetch_metainfo", fake_meta)
    monkeypatch.setattr("src.cli.full_scan", fake_scan)


def test_collect_success(monkeypatch):
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--market", "crypto"])
        assert result.exit_code == 0
        base = Path("results/crypto")
        assert (base / "metainfo.json").exists()
        assert (base / "scan.json").exists()
        status_lines = (base / "field_status.tsv").read_text().splitlines()
        assert status_lines[0] == "field\ttv_type\tstatus\tsample_value"
        assert "close\tinteger\tok\t1" in status_lines[1]
        assert "open\tstring\tok\ta" in status_lines[2]


def test_collect_error(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "src.cli.fetch_metainfo",
        lambda scope: (_ for _ in ()).throw(FileNotFoundError("boom")),
    )
    monkeypatch.setattr("src.cli.full_scan", lambda scope, tickers, columns: {})
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--market", "crypto"])
        assert result.exit_code != 0
        assert "File not found" in result.output
        log = Path("results/crypto/error.log").read_text()
        assert "FileNotFoundError: boom" in log


def test_cli_collect_crypto(monkeypatch) -> None:
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--market", "crypto"])
        assert result.exit_code == 0
        base = Path("results/crypto")
        assert (base / "field_status.tsv").exists()
        text = (base / "field_status.tsv").read_text()
        assert "close\tinteger\tok\t1" in text


def test_cli_validate_crypto_spec() -> None:
    runner = CliRunner()
    spec = Path("specs/crypto.yaml")
    result = runner.invoke(cli, ["validate", "--spec", str(spec)])
    assert result.exit_code == 0
    assert "Specification is valid" in result.output


def test_cli_version_command(monkeypatch) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        pyproject = Path("pyproject.toml")
        pyproject.write_text("[project]\nversion = '1.2.3'\n")
        from src import meta

        monkeypatch.setattr(meta.versioning, "DEFAULT_PYPROJECT_PATH", pyproject)
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "1.2.3" in result.output


def test_cli_bump_version(monkeypatch) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        pyproject = Path("pyproject.toml")
        pyproject.write_text("[project]\nversion = '0.1.0'\n")
        (Path("specs")).mkdir()
        (Path("specs") / "crypto.yaml").write_text("info:\n  version: 0.1.0\n")
        from src import meta

        monkeypatch.setattr(meta.versioning, "DEFAULT_PYPROJECT_PATH", pyproject)
        monkeypatch.setattr(meta.versioning, "DEFAULT_SPECS_DIR", Path("specs"))
        result = runner.invoke(cli, ["bump-version", "--type", "patch"])
        assert result.exit_code == 0
        assert "0.1.1" in result.output
        text = pyproject.read_text()
        assert "0.1.1" in text
        spec_text = (Path("specs") / "crypto.yaml").read_text()
        assert "0.1.1" in spec_text


def test_cli_changelog(monkeypatch) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        pyproject = Path("pyproject.toml")
        pyproject.write_text("[project]\nversion = '0.2.0'\n")
        from src import meta

        monkeypatch.setattr(meta.versioning, "DEFAULT_PYPROJECT_PATH", pyproject)
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.email", "a@b.com"], check=True)
        subprocess.run(["git", "config", "user.name", "a"], check=True)
        Path("file.txt").write_text("a")
        subprocess.run(["git", "add", "file.txt", "pyproject.toml"], check=True)
        subprocess.run(["git", "commit", "-m", "feat: start"], check=True)
        subprocess.run(["git", "tag", "v0.1.0"], check=True)
        Path("file.txt").write_text("b")
        subprocess.run(["git", "add", "file.txt"], check=True)
        subprocess.run(["git", "commit", "-m", "fix: update"], check=True)
        result = runner.invoke(cli, ["changelog"])
        assert result.exit_code == 0
        text = Path("CHANGELOG.md").read_text()
        assert "fix: update" in text
