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
from src.generator.openapi_generator import OpenAPIGenerator
from src.constants import SCOPES

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


@cli.command(name="collect-full")
@click.option(
    "--scope", "scopes", multiple=True, type=click.Choice(SCOPES), help="Market scope"
)
@click.option("--tickers", default="", help="Comma-separated tickers to scan")
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Directory to store results",
)
@click.option("--server-url", default=None, help="Override TradingView API host")
def collect_full(
    scopes: tuple[str, ...], tickers: str, outdir: Path, server_url: str | None
) -> None:
    """Fetch metainfo and full scan results for given scopes."""

    if not scopes:
        scopes = tuple(SCOPES)

    api = TradingViewAPI(base_url=server_url)
    exit_code = 0
    for scope in scopes:
        market_dir = outdir / scope
        market_dir.mkdir(parents=True, exist_ok=True)
        error_log = market_dir / "error.log"
        try:
            meta = api.metainfo(scope, {"query": ""})
            (market_dir / "metainfo.json").write_text(json.dumps(meta, indent=2))

            data_section = meta.get("data", {})
            fields_data: list[dict[str, Any]] = []
            if isinstance(data_section, dict) and isinstance(
                data_section.get("fields"), list
            ):
                fields_data = list(data_section.get("fields", []))
            elif isinstance(meta.get("fields"), list):
                fields_data = list(meta.get("fields", []))

            field_list: list[tuple[str, str]] = []
            for item in fields_data:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id")
                    ftype = str(item.get("type", "string")).lower()
                    if name:
                        field_list.append((str(name), ftype))

            index_obj = (
                data_section.get("index", {}) if isinstance(data_section, dict) else {}
            )
            names = index_obj.get("names", []) if isinstance(index_obj, dict) else []
            ticker_list = [s for s in tickers.split(",") if s]
            if not ticker_list:
                if isinstance(names, list) and names:
                    ticker_list = [str(n) for n in names[:10]]
                else:
                    ticker_list = ["BTCUSD", "ETHUSD"]
            payload = {
                "symbols": {"tickers": ticker_list[:10], "query": {"types": []}},
                "columns": [f[0] for f in field_list],
            }
            scan_res = api.scan(scope, payload)
            (market_dir / "scan.json").write_text(json.dumps(scan_res, indent=2))

            rows = scan_res.get("data", []) if isinstance(scan_res, dict) else []
            with open(market_dir / "field_status.tsv", "w", encoding="utf-8") as fh:
                fh.write("field\ttype\tstatus\tsample_value\n")
                for idx, (fname, ftype) in enumerate(field_list):
                    values = []
                    for row in rows:
                        dval = row.get("d") if isinstance(row, dict) else None
                        if isinstance(dval, list) and idx < len(dval):
                            values.append(dval[idx])
                        else:
                            values.append(None)
                    non_null = [v for v in values if v not in (None, "", [])]
                    status = "ok" if non_null and len(non_null) == len(values) else "na"
                    sample = non_null[0] if non_null else ""
                    fh.write(f"{fname}\t{ftype}\t{status}\t{sample}\n")
        except Exception as exc:  # pragma: no cover - click handles output
            exit_code = 1
            with open(error_log, "a", encoding="utf-8") as efh:
                efh.write(f"{exc}\n")
            logger.error("Failed to collect %s: %s", scope, exc)
    if exit_code:
        raise click.ClickException("Collection failed")


cli.add_command(collect_full, name="collect")


@cli.command()
@click.option("--market", required=True, help="Market directory to use")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file",
)
@click.option(
    "--results-dir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Directory with scan results",
)
def generate(market: str, output: Path, results_dir: Path) -> None:
    """Generate OpenAPI spec for a market from collected results."""

    genr = OpenAPIGenerator(results_dir)
    try:
        genr.generate(output, market=market)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        logger.error("Spec generation failed: %s", exc)
        raise click.ClickException(f"Failed to generate spec: {exc}")
    click.echo(f"Specification written to {output}")


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
