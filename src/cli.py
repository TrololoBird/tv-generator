"""Command line interface for TradingView utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import click
import yaml
from importlib.metadata import version as pkg_version
import requests
from openapi_spec_validator import validate_spec
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError

from src.api.tradingview_api import TradingViewAPI
from src.api.stock_data import fetch_recommendation, fetch_stock_value
from src.utils.payload import build_scan_payload
from src.generator.yaml_generator import generate_yaml
from src.api.data_fetcher import fetch_metainfo, full_scan, save_json, choose_tickers
from src.api.data_manager import build_field_status
from src.models import TVField, MetaInfoResponse
from src.constants import SCOPES
import pandas as pd

logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--verbose",
    "--debug",
    "verbose",
    is_flag=True,
    help="Enable debug logging",
)
@click.version_option(pkg_version("tv-generator"))
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
    "--scope",
    required=True,
    type=click.Choice(SCOPES),
    help="Market scope",
)
@click.option("--filter", "filter_", help="JSON filter")
@click.option("--filter2", help="Secondary JSON filter")
@click.option("--sort", help="Sort JSON")
@click.option("--range", "range_", help="Range JSON")
def scan(
    symbols: str,
    columns: str,
    scope: str,
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
        json.loads(filter_) if filter_ else None,
        json.loads(filter2) if filter2 else None,
        json.loads(sort) if sort else None,
        json.loads(range_) if range_ else None,
    )
    try:
        result = api.scan(scope, payload=payload)
    except requests.exceptions.RequestException as exc:
        logger.error("Scan request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:
        logger.error("Scan failed: %s", exc)
        raise click.ClickException(str(exc))
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
    "--scope",
    required=True,
    type=click.Choice(SCOPES),
    help="Market scope",
)
def metainfo(query: str, scope: str) -> None:
    """Fetch metainfo for given scope via /{scope}/metainfo."""

    api = TradingViewAPI()
    try:
        data = api.metainfo(scope, {"query": query})
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
@click.option("--scope", required=True, type=click.Choice(SCOPES), help="Market scope")
def search(payload: str, scope: str) -> None:
    """Call /{scope}/search with the given payload."""

    api = TradingViewAPI()
    try:
        data = api.search(scope, json.loads(payload))
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("Search request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("Search error: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(data, indent=2))


@cli.command()
@click.option("--payload", required=True, help="JSON payload")
@click.option("--scope", required=True, type=click.Choice(SCOPES), help="Market scope")
def history(payload: str, scope: str) -> None:
    """Call /{scope}/history with the given payload."""

    api = TradingViewAPI()
    try:
        data = api.history(scope, json.loads(payload))
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("History request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("History error: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(data, indent=2))


@cli.command()
@click.option("--payload", required=True, help="JSON payload")
@click.option("--scope", required=True, type=click.Choice(SCOPES), help="Market scope")
def summary(payload: str, scope: str) -> None:
    """Call /{scope}/summary with the given payload."""

    api = TradingViewAPI()
    try:
        data = api.summary(scope, json.loads(payload))
    except (
        requests.exceptions.RequestException
    ) as exc:  # pragma: no cover - click handles output
        logger.error("Summary request failed: %s", exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:  # pragma: no cover - click handles output
        logger.error("Summary error: %s", exc)
        raise click.ClickException(str(exc))
    click.echo(json.dumps(data, indent=2))


@cli.command("collect-full")
@click.option("--scope", required=True, type=click.Choice(SCOPES), help="Market scope")
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
def collect_full(scope: str, tickers: str, outdir: Path) -> None:
    """Fetch metainfo and scan results saving JSON and TSV."""

    market_dir = outdir / scope
    market_dir.mkdir(parents=True, exist_ok=True)
    error_log = market_dir / "error.log"
    try:
        meta = fetch_metainfo(scope)

        fields: list[dict[str, Any]] = []
        if isinstance(meta.get("data"), dict) and isinstance(
            meta["data"].get("fields"), list
        ):
            fields = list(meta["data"].get("fields", []))
        elif isinstance(meta.get("fields"), list):
            fields = list(meta.get("fields", []))

        columns: list[str] = []
        for item in fields:
            name = item.get("name") or item.get("id")
            if name:
                columns.append(str(name))

        if tickers == "AUTO":
            tickers_list = choose_tickers(meta)
        else:
            tickers_list = [t for t in tickers.split(",") if t]

        scan = full_scan(scope, tickers_list, columns)

        save_json(meta, market_dir / "metainfo.json")
        save_json(scan, market_dir / "scan.json")

        tv_fields = [
            TVField(name=c, type=str(f.get("type", "string")))
            for c, f in zip(columns, fields)
        ]
        meta_model = MetaInfoResponse(data=tv_fields)
        df = build_field_status(meta_model, scan)
        df.to_csv(market_dir / "field_status.tsv", sep="\t", index=False)
    except Exception as exc:  # pragma: no cover - click handles output
        error_log.write_text(str(exc))
        raise click.ClickException(str(exc))


cli.add_command(collect_full, name="collect")


@cli.command("generate")
@click.option("--scope", required=True, type=click.Choice(SCOPES), help="Market scope")
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
def generate(scope: str, indir: Path, outdir: Path, max_size: int) -> None:
    """Generate OpenAPI YAML using collected JSON and TSV."""

    market_dir = indir / scope
    meta_file = market_dir / "metainfo.json"
    scan_file = market_dir / "scan.json"
    status_file = market_dir / "field_status.tsv"

    try:
        meta_data = json.loads(meta_file.read_text())
        scan_data = json.loads(scan_file.read_text())
        tsv = pd.read_csv(status_file, sep="\t")
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

    fields_json = (
        meta_data.get("fields") or meta_data.get("data", {}).get("fields") or []
    )
    tv_fields = []
    for f in fields_json:
        if isinstance(f, dict):
            name = f.get("name") or f.get("id")
            if name is not None:
                tv_fields.append(
                    TVField(name=str(name), type=str(f.get("type", "string")))
                )
    meta = MetaInfoResponse(data=tv_fields)

    yaml_str = generate_yaml(scope, meta, tsv, scan_data, max_size=max_size)

    outdir.mkdir(parents=True, exist_ok=True)
    out_file = outdir / f"{scope}.yaml"
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


if __name__ == "__main__":
    cli()
