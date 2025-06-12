from pathlib import Path

import json
import yaml
from click.testing import CliRunner

from src.cli import cli


def _create_metainfo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "data": {
            "fields": [
                {"name": "close", "type": "integer"},
                {"name": "open", "type": "text"},
            ]
        }
    }
    path.write_text(json.dumps(data))
    scan = {"data": [{"d": [1, "a"]}]}
    (path.parent / "scan.json").write_text(json.dumps(scan))
    tsv = (
        "field\ttv_type\tstatus\tsample_value\n"
        "close\tinteger\tok\t1\n"
        "open\ttext\tok\ta\n"
    )
    (path.parent / "field_status.tsv").write_text(tsv)


def test_cli_scan(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get("https://scanner.tradingview.com/crypto/scan", json={"data": []})
    result = runner.invoke(
        cli,
        [
            "scan",
            "--symbols",
            "BTCUSD",
            "--columns",
            "close",
            "--scope",
            "crypto",
            "--filter",
            "{}",
        ],
    )
    assert result.exit_code == 0
    assert "data" in result.output


def test_cli_scan_full_payload(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        json={"data": []},
    )
    payload_args = [
        "scan",
        "--symbols",
        "BTCUSD",
        "--columns",
        "close",
        "--scope",
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


def test_cli_recommend(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/scan",
        json={"data": [{"d": ["buy"]}]},
    )
    result = runner.invoke(cli, ["recommend", "--symbol", "AAPL"])
    assert result.exit_code == 0
    assert "buy" in result.output


def test_cli_price(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/scan",
        json={"data": [{"d": [1.0]}]},
    )
    result = runner.invoke(cli, ["price", "--symbol", "AAPL"])
    assert result.exit_code == 0
    assert "1.0" in result.output


def test_cli_metainfo(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        json={"fields": []},
    )
    result = runner.invoke(
        cli,
        ["metainfo", "--query", "test", "--scope", "crypto"],
    )
    assert result.exit_code == 0
    assert "fields" in result.output


def test_cli_search(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/search",
        json={"result": []},
    )
    result = runner.invoke(
        cli,
        [
            "search",
            "--payload",
            "{}",
            "--scope",
            "crypto",
        ],
    )
    assert result.exit_code == 0
    assert "result" in result.output


def test_cli_history(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/stocks/history",
        json={"bars": []},
    )
    result = runner.invoke(
        cli,
        [
            "history",
            "--payload",
            "{}",
            "--scope",
            "stocks",
        ],
    )
    assert result.exit_code == 0
    assert "bars" in result.output


def test_cli_summary(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/forex/summary",
        json={"summary": []},
    )
    result = runner.invoke(
        cli,
        [
            "summary",
            "--payload",
            "{}",
            "--scope",
            "forex",
        ],
    )
    assert result.exit_code == 0
    assert "summary" in result.output


def test_cli_search_invalid_payload() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["search", "--payload", "{", "--scope", "crypto"],
    )
    assert result.exit_code != 0
    assert result.exception is not None


def test_cli_history_invalid_payload() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["history", "--payload", "{", "--scope", "crypto"],
    )
    assert result.exit_code != 0
    assert result.exception is not None


def test_cli_summary_invalid_payload() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["summary", "--payload", "{", "--scope", "crypto"],
    )
    assert result.exit_code != 0
    assert result.exception is not None


def test_scan_cli_missing_scope():
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--symbols", "AAPL", "--columns", "close"])
    assert result.exit_code != 0
    assert "Missing option '--scope'" in result.output


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
    assert "--scope" in result.output
    assert "--indir" in result.output


def test_cli_generate_and_validate(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        market_dir = Path("results") / "crypto"
        _create_metainfo(market_dir / "metainfo.json")

        out_file = Path("crypto.yaml")
        result = runner.invoke(
            cli,
            [
                "generate",
                "--scope",
                "crypto",
                "--indir",
                str(Path("results")),
                "--outdir",
                str(Path(".")),
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["validate", "--spec", str(out_file)])
        assert result.exit_code == 0
        data = yaml.safe_load(out_file.read_text())
        assert "/crypto/scan" in data["paths"]
        scan = data["paths"]["/crypto/scan"]["post"]
        assert (
            scan["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/CryptoScanRequest"
        )
        assert (
            scan["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/CryptoScanResponse"
        )


def test_cli_generate_missing_results(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        (Path("results") / "crypto").mkdir(parents=True)
        result = runner.invoke(
            cli,
            [
                "generate",
                "--scope",
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
    tv_api_mock.get(
        "https://scanner.tradingview.com/crypto/scan",
        status_code=500,
    )
    result = runner.invoke(
        cli,
        ["scan", "--symbols", "BTCUSD", "--columns", "close", "--scope", "crypto"],
    )
    assert result.exit_code != 0
    assert result.exception is not None
    assert "500" in result.output


def test_cli_recommend_error(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/scan",
        json={},
    )
    result = runner.invoke(cli, ["recommend", "--symbol", "AAPL"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "unavailable" in result.output


def test_cli_price_error(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.get(
        "https://scanner.tradingview.com/stocks/scan",
        json={},
    )
    result = runner.invoke(cli, ["price", "--symbol", "AAPL"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "unavailable" in result.output


def test_cli_metainfo_error(tv_api_mock) -> None:
    runner = CliRunner()
    tv_api_mock.post(
        "https://scanner.tradingview.com/crypto/metainfo",
        status_code=500,
    )
    result = runner.invoke(cli, ["metainfo", "--query", "t", "--scope", "crypto"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "500" in result.output


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
        return {"data": [{"d": [1, "a"]}, {"d": [2, "b"]}]}

    monkeypatch.setattr("src.cli.fetch_metainfo", fake_meta)
    monkeypatch.setattr("src.cli.full_scan", fake_scan)


def test_collect_full_success(monkeypatch):
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect-full", "--scope", "crypto"])
        assert result.exit_code == 0
        base = Path("results/crypto")
        assert (base / "metainfo.json").exists()
        assert (base / "scan.json").exists()
        status_lines = (base / "field_status.tsv").read_text().splitlines()
        assert status_lines[0] == "field\ttv_type\tstatus\tsample_value"
        assert "close\tinteger\tok\t1" in status_lines[1]
        assert "open\tstring\tok\ta" in status_lines[2]


def test_collect_full_alias(monkeypatch):
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--scope", "crypto"])
        assert result.exit_code == 0


def test_collect_full_error(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "src.cli.fetch_metainfo",
        lambda scope: (_ for _ in ()).throw(FileNotFoundError("boom")),
    )
    monkeypatch.setattr("src.cli.full_scan", lambda scope, tickers, columns: {})
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect-full", "--scope", "crypto"])
        assert result.exit_code != 0
        log = Path("results/crypto/error.log").read_text()
        assert log
