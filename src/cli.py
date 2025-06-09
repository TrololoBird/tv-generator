import argparse
import logging
from pathlib import Path

from src.generator.openapi_generator import OpenAPIGenerator

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingView tools")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate-openapi", help="Generate OpenAPI spec")
    gen.add_argument("results", type=Path, help="Directory with market results")
    gen.add_argument("output", type=Path, help="Output YAML path")

    args = parser.parse_args()

    if args.command == "generate-openapi":
        genr = OpenAPIGenerator(args.results)
        genr.generate(args.output)


if __name__ == "__main__":
    main()
