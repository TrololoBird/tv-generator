"""Command line interface for TradingView utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

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

logger = logging.getLogger(__name__)

SCOPES = [
    "crypto",
    "forex",
    "futures",
    "america",
    "bond",
    "cfd",
    "coin",
    "stocks",
]


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
