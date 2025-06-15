"""Command line interface for TradingView utilities."""

from __future__ import annotations

import json
from json import JSONDecodeError
import logging
from pathlib import Path
from typing import Any, Callable, TypeVar

import click
import yaml
from importlib.metadata import PackageNotFoundError, version as pkg_version
import requests
from openapi_spec_validator import validate_spec
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError
from pydantic import ValidationError

from src.api.tradingview_api import TradingViewAPI
from src.api.stock_data import fetch_recommendation, fetch_stock_value
from src.utils.payload import build_scan_payload
from src.generator.yaml_generator import generate_yaml
from src.api.data_fetcher import fetch_metainfo, full_scan, save_json, choose_tickers
from src.api.data_manager import build_field_status
from src.models import TVField, MetaInfoResponse, ScanResponse
from src.constants import SCOPES
import pandas as pd

logger = logging.getLogger(__name__)

T = TypeVar("T")


try:
    _pkg_version = pkg_version("tv-generator")
except PackageNotFoundError:  # pragma: no cover - dev environment
    _pkg_version = "0.0.0"


def _with_error_handling(
    func: Callable[..., T],
    request_msg: str,
    error_msg: str,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute *func* converting common errors to ``ClickException``."""

    try:
        return func(*args, **kwargs)
    except requests.exceptions.RequestException as exc:
        logger.error("%s: %s", request_msg, exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            r = exc.response
            raise click.ClickException(f"HTTP {r.status_code}: {r.text}")
        raise click.ClickException(str(exc))
    except (ValueError, ValidationError) as exc:
        logger.error("%s: %s", error_msg, exc)
        raise click.ClickException(str(exc))


def _parse_json_option(value: str | None, name: str) -> Any:
    """Safely parse a JSON option or return ``None``."""

    if value is None:
        return None
    try:
        return json.loads(value)
    except JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in option: {name}")


@click.group()
@click.option(
    "--verbose",
    "--debug",
    "verbose",
    is_flag=True,
    help="Enable debug logging",
)
@click.version_option(_pkg_version)
def cli(verbose: bool) -> None:
    """TradingView command line utilities."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


@cli.command()
@click.option(
    "--symbols",
    required=True,
    help="Comma-separated tickers",
)
@click.option(
    "--columns",
    required=True,
    help="Comma-separated fields",
)
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES),
    help="Market name",
)
@click.option("--filter", "filter_", help="JSON filter")
@click.option("--filter2", help="Secondary JSON filter")
@click.option("--sort", help="Sort JSON")
@click.option("--range", "range_", help="Range JSON")
def scan(
    symbols: str,
    columns: str,
    market: str,
    filter_: str | None,
    filter2: str | None,
    sort: str | None,
    range_: str | None,
) -> None:
    """Perform a basic scan request and print JSON."""

    api = TradingViewAPI()
    payload = build_scan_payload(
        symbols.split(","),
        columns.split(","),
        _parse_json_option(filter_, "--filter"),
        _parse_json_option(filter2, "--filter2"),
        _parse_json_option(sort, "--sort"),
        _parse_json_option(range_, "--range"),
    )
    result = _with_error_handling(
        api.scan,
        "Scan request failed",
        "Scan failed",
        market,
        payload=payload,
    )
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option("--symbol", required=True, help="Ticker symbol")
@click.option("--market", default="stocks", show_default=True, help="Market name")
def recommend(symbol: str, market: str) -> None:
    """Fetch trading recommendation for a symbol."""

    try:
        value = fetch_recommendation(symbol, market)
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("Recommendation request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("Recommendation unavailable: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(value, indent=2))


@cli.command(name="price")
@click.option("--symbol", required=True, help="Ticker symbol")
@click.option("--market", default="stocks", show_default=True, help="Market name")
def price(symbol: str, market: str) -> None:
    """Fetch last close price for a symbol."""

    try:
        value = fetch_stock_value(symbol, market)
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("Price request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("Price unavailable: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(value, indent=2))


@cli.command()
@click.option("--query", required=True, help="Search query or market identifier")
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES),
    help="Market name",
)
def metainfo(query: str, market: str) -> None:
    """Fetch metainfo for given market via /{market}/metainfo."""

    api = TradingViewAPI()
    try:
        data = api.metainfo(market, {"query": query})
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("Metainfo request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("Metainfo error: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(data, indent=2))


@cli.command()
@click.option("--payload", required=True, help="JSON payload")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
def search(payload: str, market: str) -> None:
    """Call /{market}/search with the given payload."""

    api = TradingViewAPI()
    parsed = _parse_json_option(payload, "--payload")
    data = _with_error_handling(
        lambda: api.search(market, parsed),
        "Search request failed",
        "Search error",
    )
    click.echo(json.dumps(data, indent=2))


@cli.command()
@click.option("--payload", required=True, help="JSON payload")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
def history(payload: str, market: str) -> None:
    """Call /{market}/history with the given payload."""

    api = TradingViewAPI()
    parsed = _parse_json_option(payload, "--payload")
    data = _with_error_handling(
        lambda: api.history(market, parsed),
        "History request failed",
        "History error",
    )
    click.echo(json.dumps(data, indent=2))


@cli.command()
@click.option("--payload", required=True, help="JSON payload")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
def summary(payload: str, market: str) -> None:
    """Call /{market}/summary with the given payload."""

    api = TradingViewAPI()
    parsed = _parse_json_option(payload, "--payload")
    data = _with_error_handling(
        lambda: api.summary(market, parsed),
        "Summary request failed",
        "Summary error",
    )
    click.echo(json.dumps(data, indent=2))


@cli.command("collect")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
@click.option(
    "--tickers",
    default="AUTO",
    show_default=True,
    help='Comma-separated tickers or "AUTO"',
)
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Directory to store results",
)
@click.option(
    "--offline",
    is_flag=True,
    help="Use existing JSON files instead of network requests",
)
def collect(market: str, tickers: str, outdir: Path, offline: bool) -> None:
    """Fetch metainfo and scan results saving JSON and TSV."""

    market_dir = outdir / market
    market_dir.mkdir(parents=True, exist_ok=True)
    meta_path = market_dir / "metainfo.json"
    scan_path = market_dir / "scan.json"
    error_log = market_dir / "error.log"
    try:
        offline = offline or (meta_path.exists() and scan_path.exists())
        if offline:
            meta = json.loads(meta_path.read_text())
            scan = (
                json.loads(scan_path.read_text())
                if scan_path.exists()
                else {"data": []}
            )
            fields = meta.get("data", {}).get("fields") or meta.get("fields", [])
        else:
            meta = fetch_metainfo(market)

            fields_data: list[dict[str, Any]] = []
            if isinstance(meta.get("data"), dict) and isinstance(
                meta["data"].get("fields"), list
            ):
                fields_data = list(meta["data"].get("fields", []))
            elif isinstance(meta.get("fields"), list):
                fields_data = list(meta.get("fields", []))

            columns: list[str] = []
            for item in fields_data:
                name = item.get("name") or item.get("id")
                if name:
                    columns.append(str(name))

            if tickers == "AUTO":
                tickers_list = choose_tickers(meta)
            else:
                tickers_list = [t for t in tickers.split(",") if t]

            scan = full_scan(market, tickers_list, columns)

            save_json(meta, meta_path)
            save_json(scan, scan_path)

        fields = meta.get("data", {}).get("fields") or meta.get("fields", [])
        tv_fields = []
        columns = []
        for item in fields:
            name = item.get("name") or item.get("id")
            if name:
                columns.append(str(name))
                tv_fields.append(
                    TVField.model_validate(
                        {"name": name, "type": item.get("type", "string")}
                    )
                )
        meta_model = MetaInfoResponse(data=tv_fields)
        df = build_field_status(meta_model, scan)
        tsv_text = df.to_csv(sep="\t", index=False)
        (market_dir / "field_status.tsv").write_text(tsv_text.rstrip("\n"))
    except FileNotFoundError as exc:  # pragma: no cover - click handles output
        with error_log.open("a") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
        raise click.ClickException("File not found")
    except ValueError as exc:  # pragma: no cover - click handles output
        with error_log.open("a") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
        raise click.ClickException("Invalid data")
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        with error_log.open("a") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
        raise click.ClickException("Request failed")
    except Exception as exc:  # pragma: no cover - click handles output
        with error_log.open("a") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
        raise click.ClickException(str(exc))


@cli.command()
@click.option(
    "--indir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Directory to store intermediate data",
)
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    default="specs",
    show_default=True,
    help="Directory for YAML specs",
)
@click.option(
    "--workers",
    type=int,
    default=1,
    show_default=True,
    help="Number of parallel workers",
)
@click.option(
    "--offline",
    is_flag=True,
    help="Skip data collection if results exist",
)
def build(indir: Path, outdir: Path, workers: int, offline: bool) -> None:
    """Collect data and generate specs for all markets."""

    def _process(market: str) -> None:
        click.echo(f"* {market}")
        cb_collect = getattr(collect, "callback", None)
        if callable(cb_collect):
            offline_mode = offline or (indir / market / "metainfo.json").exists()
            cb_collect(market, "AUTO", indir, offline_mode)
        cb_generate = getattr(generate, "callback", None)
        if callable(cb_generate):
            cb_generate(market, indir, outdir, 1_048_576)

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_process, m) for m in SCOPES]
            for f in futures:
                try:
                    f.result()
                except Exception as exc:
                    raise click.ClickException(str(exc))
    else:
        for market in SCOPES:
            _process(market)


cli.add_command(build, name="build-all")


@cli.command("generate")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
@click.option(
    "--indir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Input directory",
)
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    default="specs",
    show_default=True,
    help="Directory for YAML specs",
)
@click.option(
    "--max-size",
    type=int,
    default=1_048_576,
    show_default=True,
    help="Maximum YAML size in bytes",
)
def generate(market: str, indir: Path, outdir: Path, max_size: int) -> None:
    """Generate OpenAPI YAML using collected JSON and TSV."""

    market_dir = indir / market
    meta_file = market_dir / "metainfo.json"
    scan_file = market_dir / "scan.json"
    status_file = market_dir / "field_status.tsv"

    try:
        meta_data = json.loads(meta_file.read_text())
        scan_data = json.loads(scan_file.read_text())
        tsv = pd.read_csv(status_file, sep="\t")
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

    # Validate TradingView JSON
    MetaInfoResponse.parse_obj(meta_data)
    ScanResponse.parse_obj(scan_data)

    fields_json = (
        meta_data.get("fields") or meta_data.get("data", {}).get("fields") or []
    )
    tv_fields = []
    for f in fields_json:
        if isinstance(f, dict):
            name = f.get("name") or f.get("id")
            if name is not None:
                data = {"name": name, "type": f.get("type", "string")}
                tv_fields.append(TVField.model_validate(data))
    meta = MetaInfoResponse(data=tv_fields)

    yaml_str = generate_yaml(market, meta, scan_data, max_size=max_size)

    outdir.mkdir(parents=True, exist_ok=True)
    out_file = outdir / f"{market}.yaml"
    out_file.write_text(yaml_str)
    size_kb = out_file.stat().st_size // 1024
    click.echo(f"\u2713 {out_file.name} {size_kb} KB")


@cli.command()
@click.option(
    "--spec",
    "spec_file",
    type=click.Path(path_type=Path),
    required=True,
    help="Spec file to validate",
)
def validate(spec_file: Path) -> None:
    """Validate an OpenAPI specification file."""

    try:
        with open(spec_file, "r", encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        validate_spec(spec)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))
    except (yaml.YAMLError, OpenAPISpecValidatorError, ValueError) as exc:
        logger.error("Specification validation failed: %s", exc)
        raise click.ClickException(f"Validation failed: {exc}")
    click.echo("Specification is valid")


@cli.command()
@click.option(
    "--spec",
    "spec_file",
    type=click.Path(path_type=Path),
    required=True,
    help="Spec file to preview",
)
def preview(spec_file: Path) -> None:
    """Show table with fields, type, enum and description."""

    try:
        data = yaml.safe_load(spec_file.read_text())
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))
    except yaml.YAMLError as exc:
        raise click.ClickException(str(exc))

    schemas = data.get("components", {}).get("schemas", {})
    fields_schema = None
    for key, val in schemas.items():
        if key.endswith("Fields") and isinstance(val, dict):
            fields_schema = val
            break
    if not fields_schema:
        raise click.ClickException("Fields schema not found")

    props = fields_schema.get("properties", {})
    rows = []
    for name, info in props.items():
        t = info.get("type")
        if not t and isinstance(info.get("$ref"), str):
            ref = info["$ref"].split("/")[-1]
            t = schemas.get(ref, {}).get("type", ref)
        enum = ",".join(str(v) for v in info.get("enum", [])) if "enum" in info else ""
        desc = info.get("description", "")
        rows.append({"field": name, "type": t or "", "enum": enum, "description": desc})
    if not rows:
        raise click.ClickException("No fields found")

    df = pd.DataFrame(rows, columns=["field", "type", "enum", "description"])
    click.echo(df.to_string(index=False))


if __name__ == "__main__":
    cli()
