"""Command line interface for TradingView utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click
import yaml
from openapi_spec_validator import validate_spec

from src.api.tradingview_api import TradingViewAPI
from src.api.stock_data import fetch_recommendation, fetch_stock_value
from src.generator.openapi_generator import OpenAPIGenerator

logging.basicConfig(level=logging.INFO)


@click.group()
def cli() -> None:
    """TradingView command line utilities."""


@cli.command()
@click.option("--market", required=True, help="Market to scan")
def scan(market: str) -> None:
    """Perform a basic scan request and print JSON."""

    api = TradingViewAPI()
    try:
        result = api.scan(market, payload={})
    except Exception as exc:  # requests errors etc.
        raise click.ClickException(str(exc))
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option("--symbol", required=True, help="Ticker symbol")
@click.option("--market", default="stocks", show_default=True, help="Market name")
def recommend(symbol: str, market: str) -> None:
    """Fetch trading recommendation for a symbol."""

    try:
        value = fetch_recommendation(symbol, market)
    except Exception as exc:  # pragma: no cover - click handles output
        raise click.ClickException(str(exc))
    click.echo(json.dumps(value))


@cli.command(name="price")
@click.option("--symbol", required=True, help="Ticker symbol")
@click.option("--market", default="stocks", show_default=True, help="Market name")
def price(symbol: str, market: str) -> None:
    """Fetch last close price for a symbol."""

    try:
        value = fetch_stock_value(symbol, market)
    except Exception as exc:  # pragma: no cover - click handles output
        raise click.ClickException(str(exc))
    click.echo(json.dumps(value))


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
    except Exception as exc:
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
    except Exception as exc:
        raise click.ClickException(f"Validation failed: {exc}")
    click.echo("Specification is valid")


if __name__ == "__main__":
    cli()
