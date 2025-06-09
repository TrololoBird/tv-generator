"""Command line interface for TradingView utilities."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import yaml
from openapi_spec_validator import validate_spec

from src.api.tradingview_api import TradingViewAPI
from src.generator.openapi_generator import OpenAPIGenerator

logging.basicConfig(level=logging.INFO)


def cmd_scan(market: str) -> None:
    """Perform a basic scan request and print JSON."""

    api = TradingViewAPI()
    result = api.scan(market, payload={})
    print(json.dumps(result, indent=2))


def cmd_generate(market: str, output: Path) -> None:
    """Generate OpenAPI spec for a market from collected results."""

    genr = OpenAPIGenerator(Path("results"))
    genr.generate(output, market=market)


def cmd_validate(spec_file: Path) -> None:
    """Validate an OpenAPI specification file."""

    with open(spec_file, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    validate_spec(spec)
    print("Specification is valid")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tvgen", description="TradingView tools")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan TradingView market")
    scan.add_argument("--market", required=True)

    gen = sub.add_parser("generate", help="Generate OpenAPI spec")
    gen.add_argument("--market", required=True)
    gen.add_argument("--output", type=Path, required=True)

    val = sub.add_parser("validate", help="Validate OpenAPI spec")
    val.add_argument("--spec", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args.market)
    elif args.command == "generate":
        cmd_generate(args.market, args.output)
    elif args.command == "validate":
        cmd_validate(args.spec)


if __name__ == "__main__":
    main()
