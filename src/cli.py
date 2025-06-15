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
from src.generator.yaml_generator import generate_for_market
from src.spec.generator import (
    generate_spec_for_market,
    detect_all_markets,
)
from src.api.data_fetcher import fetch_metainfo, full_scan, save_json, choose_tickers
from src.api.data_manager import build_field_status
from src.models import TVField, MetaInfoResponse
from src.constants import SCOPES
from src.spec.bundler import bundle_all_specs
from src.meta.versioning import (
    get_version as _get_version,
    bump_version as _bump_version,
    generate_changelog as _generate_changelog,
)
from src.meta import classify_fields
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
        raise click.ClickException("TradingView request failed")
    except (ValidationError, KeyError) as exc:
        logger.error("%s: %s", error_msg, exc)
        raise click.ClickException(str(exc))
    except ValueError as exc:
        logger.error("%s: %s", error_msg, exc)
        msg = (
            "TradingView request failed"
            if str(exc).startswith("TradingView HTTP")
            else str(exc)
        )
        raise click.ClickException(msg)


def _parse_json_option(value: str | None, name: str) -> Any:
    """Safely parse a JSON option or return ``None``."""

    if value is None:
        return None
    try:
        return json.loads(value)
    except JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in {name}")


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
    click.echo(json.dumps(result.model_dump(by_alias=True), indent=2))


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
    data = _with_error_handling(
        lambda: api.metainfo(market, {"query": query}),
        "Metainfo request failed",
        "Metainfo error",
    )
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
                try:
                    tickers_list = choose_tickers(meta)
                except ValueError as exc:
                    with error_log.open("a") as fh:
                        fh.write(f"{type(exc).__name__}: {exc}\n")
                    raise click.ClickException("No symbols found in metainfo")
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
        raise click.ClickException("TradingView request failed")
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
        try:
            generate_for_market(market, indir, outdir, 1_048_576, include_missing=False)
        except FileNotFoundError as exc:
            raise click.ClickException(str(exc))

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


@cli.command()
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES + ["all"]),
    help="Market name or 'all'",
)
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Directory to store results",
)
@click.option("--generate", is_flag=True, help="Run generate after refresh")
@click.option("--diff", is_flag=True, help="Compare with cached results")
@click.option(
    "--fail-on-change",
    is_flag=True,
    help="Exit with code 1 if diff detects changes",
)
def refresh(
    market: str, outdir: Path, generate: bool, diff: bool, fail_on_change: bool
) -> None:
    """Download latest data and update TSV files."""

    from src.data.collector import refresh_market
    from src.spec.generator import generate_spec_for_market

    markets = SCOPES if market == "all" else [market]
    for m in markets:
        click.echo(f"* {m}")
        if diff:
            from src.compare.cache_diff import backup_results

            backup_results(m, outdir, Path("cache"))
        refresh_market(m, outdir)
        if diff:
            from src.compare.cache_diff import diff_market, update_cache

            text, changed = diff_market(m, outdir, Path("cache"))
            if text:
                click.echo(text)
            update_cache(m, outdir, Path("cache"))
            if changed and fail_on_change:
                raise SystemExit(1)
        if generate:
            try:
                generate_spec_for_market(m, outdir, Path("specs"))
            except Exception as exc:
                logger.warning("Skipped %s: %s", m, exc)


cli.add_command(build, name="build-all")


@cli.command("generate")
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES + ["all"]),
    help="Target market or 'all'",
)
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
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on first market error when generating all",
)
@click.option(
    "--include-missing",
    is_flag=True,
    help="Include auto-discovered fields in spec",
)
@click.option(
    "--include-type",
    "include_types",
    multiple=True,
    type=click.Choice(["numeric", "string", "custom"]),
    help="Include only fields of given type",
)
@click.option(
    "--exclude-type",
    "exclude_types",
    multiple=True,
    type=click.Choice(["discovered"]),
    help="Exclude fields of given type",
)
@click.option(
    "--only-timeframe-supported",
    is_flag=True,
    help="Include only fields supporting timeframes",
)
@click.option(
    "--only-daily",
    is_flag=True,
    help="Include only daily timeframe fields",
)
def generate(
    market: str,
    indir: Path,
    outdir: Path,
    max_size: int,
    strict: bool,
    include_missing: bool,
    include_types: tuple[str, ...],
    exclude_types: tuple[str, ...],
    only_timeframe_supported: bool,
    only_daily: bool,
) -> None:
    """Generate OpenAPI YAML using collected JSON and TSV."""

    try:
        if market == "all":
            out_files = []
            for m in detect_all_markets(indir):
                try:
                    out_files.append(
                        generate_spec_for_market(
                            m,
                            indir,
                            outdir,
                            max_size,
                            include_missing=include_missing,
                            include_types=include_types,
                            exclude_types=exclude_types,
                            only_timeframe_supported=only_timeframe_supported,
                            only_daily=only_daily,
                        )
                    )
                except Exception as exc:
                    logger.warning("Skipped %s: %s: %s", m, type(exc).__name__, exc)
                    if strict:
                        raise
                    click.echo(
                        f"[⚠️] Skipped {m}: {type(exc).__name__}: {exc}",
                        err=True,
                    )
            if out_files:
                names = ", ".join(f.name for f in out_files)
                click.echo(f"\u2713 Generated: {names}")
        else:
            out_file = generate_for_market(
                market,
                indir,
                outdir,
                max_size,
                include_missing=include_missing,
                include_types=include_types,
                exclude_types=exclude_types,
                only_timeframe_supported=only_timeframe_supported,
                only_daily=only_daily,
            )
            size_kb = out_file.stat().st_size // 1024
            click.echo(f"\u2713 {out_file.name} {size_kb} KB")
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))


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


@cli.command()
@click.option(
    "--format",
    "format_",
    default="json",
    show_default=True,
    type=click.Choice(["json", "yaml"]),
    help="Output format",
)
@click.option(
    "--outfile", default="bundle.json", show_default=True, help="Bundle file path"
)
def bundle(format_: str, outfile: str) -> None:
    """Bundle all specifications under ``specs/`` directory."""

    try:
        out_path = bundle_all_specs("specs/", outfile, format=format_)
    except FileNotFoundError as exc:  # pragma: no cover - click handles output
        raise click.ClickException(str(exc))
    size_kb = Path(out_path).stat().st_size // 1024
    click.echo(f"\u2713 {out_path} {size_kb} KB")


@cli.command("generate-if-needed")
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES + ["all"]),
    help="Market name or 'all'",
)
@click.option(
    "--strict", is_flag=True, help="Fail with exit code 1 if diff detects changes"
)
@click.option("--bundle", is_flag=True, help="Run 'bundle' after generation")
@click.option("--validate", "validate_", is_flag=True, help="Validate generated YAML")
def generate_if_needed(
    market: str, strict: bool, bundle: bool, validate_: bool
) -> None:
    """Generate specs only when diff finds changes."""

    from src.compare.cache_diff import diff_market

    markets = SCOPES if market == "all" else [market]
    changed: list[str] = []
    for m in markets:
        text, has_changes = diff_market(m, Path("results"), Path("cache"))
        if has_changes:
            add = len([line for line in text.splitlines() if line.startswith("[+]")])
            rem = len([line for line in text.splitlines() if line.startswith("[-]")])
            chg = len([line for line in text.splitlines() if line.startswith("[*]")])
            parts = []
            if add:
                parts.append(f"{add} field{'s' if add != 1 else ''} added")
            if rem:
                parts.append(f"{rem} field{'s' if rem != 1 else ''} removed")
            if chg:
                parts.append(f"{chg} field{'s' if chg != 1 else ''} changed")
            summary = ", ".join(parts)
            click.echo(f"[+] {m} — {summary} → regenerating")
            changed.append(m)
        else:
            click.echo(f"[✓] {m} — no changes")

    if strict:
        if changed:
            raise SystemExit(1)
        return

    if not changed:
        click.echo("No changes detected — skipping generation")
        return

    for m in changed:
        generate_spec_for_market(m, Path("results"), Path("specs"))
        if validate_:
            try:
                with open(f"specs/{m}.yaml", "r", encoding="utf-8") as fh:
                    spec = yaml.safe_load(fh)
                validate_spec(spec)
            except (
                FileNotFoundError,
                yaml.YAMLError,
                OpenAPISpecValidatorError,
            ) as exc:
                raise click.ClickException(str(exc))
    if bundle:
        bundle_all_specs("specs", "bundle.yaml")
    click.echo("✅ Specs updated for: " + ", ".join(changed))


@cli.command()
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
@click.option("--verbose", is_flag=True, help="Show full JSON output")
def debug(market: str, verbose: bool) -> None:
    """Diagnose TradingView connectivity for the given market."""

    result = TradingViewAPI().diagnose_connection(market, verbose)
    click.echo(result)


@cli.command("diff")
@click.option(
    "--market",
    required=True,
    type=click.Choice(SCOPES + ["all"]),
    help="Market name or 'all'",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(path_type=Path),
    help="Save report to file",
)
def diff_cmd(market: str, output_file: Path | None) -> None:
    """Compare results with cached versions."""

    from src.compare.cache_diff import diff_market

    markets = SCOPES if market == "all" else [market]
    chunks: list[str] = []
    for m in markets:
        text, _changed = diff_market(m, Path("results"), Path("cache"))
        if text:
            chunks.append(f"## {m}\n{text}")
    report = "\n\n".join(chunks)
    if output_file:
        Path(output_file).write_text(report + "\n")
    if report:
        click.echo(report)


@cli.command("list-fields")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
@click.option(
    "--group-by", default="type", show_default=True, type=click.Choice(["type"])
)
def list_fields(market: str, group_by: str) -> None:
    """List fields grouped by classification."""

    market_dir = Path("results") / market
    meta_file = market_dir / "metainfo.json"
    scan_file = market_dir / "scan.json"
    status_file = market_dir / "field_status.tsv"
    try:
        meta_data = json.loads(meta_file.read_text())
        json.loads(scan_file.read_text())
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

    fields_json = meta_data.get("data", {}).get("fields") or meta_data.get("fields", [])
    columns: dict[str, dict[str, Any]] = {}
    for item in fields_json:
        if isinstance(item, dict):
            name = item.get("name") or item.get("id")
            if name:
                columns[name] = {"type": item.get("type", "string")}

    from src.analyzer.scan_audit import find_missing_fields

    missing = []
    if status_file.exists():
        missing = find_missing_fields(meta_file, scan_file, status_file)
    for item in missing:
        columns[item["name"]] = {"type": item.get("type", "string"), "source": "scan"}

    info = classify_fields(columns)
    if group_by == "type":
        for key, values in info.items():
            if values:
                click.echo(f"{key}: {', '.join(sorted(values))}")


@cli.command("audit-missing-fields")
@click.option("--market", required=True, type=click.Choice(SCOPES), help="Market name")
@click.option(
    "--indir",
    type=click.Path(path_type=Path),
    default="results",
    show_default=True,
    help="Input directory",
)
@click.option("--outfile", type=click.Path(path_type=Path), help="Save result to file")
def audit_missing_fields_cli(market: str, indir: Path, outfile: Path | None) -> None:
    """Show fields present in scan.json but missing from metainfo."""

    from src.analyzer.scan_audit import find_missing_fields

    market_dir = indir / market
    meta_file = market_dir / "metainfo.json"
    scan_file = market_dir / "scan.json"
    status_file = market_dir / "field_status.tsv"

    try:
        missing = find_missing_fields(meta_file, scan_file, status_file)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))

    lines = [f'Field "{m["name"]}" — inferred as {m["type"]}' for m in missing]
    text = "\n".join(lines)
    if outfile:
        Path(outfile).write_text(text + "\n")
    if text:
        click.echo(text)


@cli.command()
@click.option(
    "--outfile",
    type=click.Path(path_type=Path),
    default="README.generated.md",
    show_default=True,
    help="Output README file",
)
def docs(outfile: Path) -> None:
    """Generate README file with CLI command list."""

    from src.docs.readme_generator import generate_readme

    out_path = generate_readme(outfile)
    click.echo(f"\u2713 {out_path}")


@cli.command("publish-pages")
@click.option(
    "--branch",
    default="gh-pages",
    show_default=True,
    help="Target branch",
)
def publish_pages(branch: str) -> None:
    """Publish YAML specs to GitHub Pages branch."""

    import shutil
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir(parents=True, exist_ok=True)
        for spec_file in Path("specs").glob("*.yaml"):
            shutil.copy2(spec_file, spec_dir / spec_file.name)
        bundle_file = Path("bundle.yaml")
        if bundle_file.exists():
            shutil.copy2(bundle_file, spec_dir / bundle_file.name)
        links = "".join(
            f'<li><a href="specs/{f.name}">{f.name}</a></li>'
            for f in spec_dir.glob("*.yaml")
        )
        (tmp_path / "index.html").write_text(f"<ul>{links}</ul>", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(["git", "checkout", "-b", branch], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Publish specs to GitHub Pages"],
            cwd=tmp_path,
            check=True,
        )
        try:
            remote = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "push", remote, f"HEAD:{branch}", "--force"],
                cwd=tmp_path,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise click.ClickException("Git push failed") from exc
    click.echo(f"\u2713 Published to {branch}")


@cli.command("publish-release-assets")
@click.option("--tag", required=True, help="Release tag")
def publish_release_assets(tag: str) -> None:
    """Upload specs to GitHub release."""

    import subprocess

    files = [str(p) for p in Path("specs").glob("*.yaml") if p.is_file()]
    if Path("bundle.yaml").exists():
        files.append("bundle.yaml")
    if Path("CHANGELOG.md").exists():
        files.append("CHANGELOG.md")

    cmd = ["gh", "release", "upload", tag, "--clobber", *files]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException("Release upload failed") from exc
    click.echo("\u2713 Assets uploaded")


@cli.command()
def version() -> None:
    """Show current package version."""

    click.echo(_get_version())


@cli.command("bump-version")
@click.option(
    "--type",
    "kind",
    type=click.Choice(["patch", "minor", "major"]),
    default="patch",
    show_default=True,
    help="Version part to bump",
)
def bump_version_cli(kind: str) -> None:
    """Increment project version."""

    new_version = _bump_version(kind)
    click.echo(new_version)


@cli.command()
def changelog() -> None:
    """Generate CHANGELOG from git history."""

    path = _generate_changelog()
    click.echo(f"\u2713 {path}")


if __name__ == "__main__":
    cli()
