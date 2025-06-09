"""Command line interface for TradingView utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click
import yaml
from openapi_spec_validator import validate_spec

from src.api.tradingview_api import TradingViewAPI
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
    result = api.scan(market, payload={})
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option("--market", required=True, help="Market directory to use")
@click.option(
    "--output", type=click.Path(path_type=Path), required=True, help="Output YAML file"
)
def generate(market: str, output: Path) -> None:
    """Generate OpenAPI spec for a market from collected results."""

    genr = OpenAPIGenerator(Path("results"))
    genr.generate(output, market=market)


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

    with open(spec_file, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    validate_spec(spec)
    click.echo("Specification is valid")


if __name__ == "__main__":
    cli()
