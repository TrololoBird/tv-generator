import json
from pathlib import Path
import click
from click.testing import CliRunner

from src.cli import cli
from src.cli import collect as collect_cmd


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
    scan = {"count": 1, "data": [{"s": "AAA", "d": [1, "a"]}]}
    (path.parent / "scan.json").write_text(json.dumps(scan))
    tsv = (
        "field\ttv_type\tstatus\tsample_value\n"
        "close\tinteger\tok\t1\n"
        "open\ttext\tok\ta\n"
    )
    (path.parent / "field_status.tsv").write_text(tsv)


def _mock_collect_api(monkeypatch) -> None:
    meta = {
        "fields": [
            {"name": "close", "type": "integer"},
            {"name": "open", "type": "text"},
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
    monkeypatch.setattr(
        "src.cli.save_json", lambda d, p: Path(p).write_text(json.dumps(d))
    )


ASSETS = Path(__file__).parent / "assets"


def test_generate_no_placeholder() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        market_dir = Path("results") / "coin"
        _create_metainfo(market_dir / "metainfo.json")
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
        text = Path("coin.yaml").read_text()
        assert "PLACEHOLDER" not in text
        assert "TODO" not in text


def test_generate_invalid_market() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--market", "bad"])
    assert result.exit_code != 0
    assert "Invalid value for '--market'" in result.output


def test_collect_and_generate(monkeypatch) -> None:
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["collect", "--market", "crypto"])
        assert result.exit_code == 0, result.output
        result = runner.invoke(
            cli,
            ["generate", "--market", "crypto", "--indir", "results", "--outdir", "."],
        )
        assert result.exit_code == 0, result.output
        text = Path("crypto.yaml").read_text()
        assert "PLACEHOLDER" not in text
        assert "TODO" not in text


def test_collect_invalid_market() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["collect", "--market", "bad"])
    assert result.exit_code != 0
    assert "Invalid value for '--market'" in result.output


def test_build(monkeypatch) -> None:
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    monkeypatch.setattr("src.constants.SCOPES", ["coin"])
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["build"])
        assert result.exit_code == 0, result.output
        spec = Path("specs/coin.yaml")
        assert spec.exists()
        text = spec.read_text()
        assert "PLACEHOLDER" not in text
        assert "TODO" not in text


def test_build_error(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("src.constants.SCOPES", ["coin"])

    def boom(*_a, **_kw):
        raise click.ClickException("fail")

    monkeypatch.setattr(collect_cmd, "callback", boom)
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["build"])
        assert result.exit_code != 0


def test_build_parallel(monkeypatch) -> None:
    runner = CliRunner()
    _mock_collect_api(monkeypatch)
    monkeypatch.setattr("src.constants.SCOPES", ["coin", "stocks"])
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["build", "--workers", "2"])
        assert result.exit_code == 0, result.output
        assert Path("specs/coin.yaml").exists()
        assert Path("specs/stocks.yaml").exists()


def test_preview() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        spec = Path("spec.yaml")
        spec.write_text((ASSETS / "prefinal.yaml").read_text())
        result = runner.invoke(cli, ["preview", "--spec", str(spec)])
        assert result.exit_code == 0, result.output
        assert "field" in result.output
        assert "close" in result.output


def test_preview_missing() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["preview", "--spec", "missing.yaml"])
    assert result.exit_code != 0
    assert "No such file" in result.output
