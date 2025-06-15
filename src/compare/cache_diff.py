from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, Tuple


_CUSTOM_PATTERNS = [r"^TV_Custom\.", r"_impact_score$", r"^BTC_", r"^custom_"]


def _is_custom(name: str) -> bool:
    for pat in _CUSTOM_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


def _load_meta_fields(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    fields = data.get("data", {}).get("fields") or data.get("fields", [])
    mapping: Dict[str, str] = {}
    for item in fields:
        if isinstance(item, dict):
            name = item.get("name") or item.get("id")
            if name:
                mapping[str(name)] = str(item.get("type", "string"))
    return mapping


def backup_results(
    market: str, results_dir: Path = Path("results"), cache_dir: Path = Path("cache")
) -> None:
    """Save current result files to cache directory if they exist."""
    src_dir = Path(results_dir) / market
    if not src_dir.exists():
        return
    dst_dir = Path(cache_dir) / market
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ["metainfo.json", "scan.json", "field_status.tsv"]:
        file = src_dir / name
        if file.exists():
            shutil.copy2(file, dst_dir / name)


def update_cache(
    market: str, results_dir: Path = Path("results"), cache_dir: Path = Path("cache")
) -> None:
    """Update cache directory with latest results."""
    src_dir = Path(results_dir) / market
    dst_dir = Path(cache_dir) / market
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ["metainfo.json", "scan.json", "field_status.tsv"]:
        file = src_dir / name
        if file.exists():
            shutil.copy2(file, dst_dir / name)


def diff_market(
    market: str,
    results_dir: Path = Path("results"),
    cache_dir: Path = Path("cache"),
) -> Tuple[str, bool]:
    """Return diff report for *market* and whether changes detected."""
    new_meta = _load_meta_fields(Path(results_dir) / market / "metainfo.json")
    old_meta = _load_meta_fields(Path(cache_dir) / market / "metainfo.json")

    added = {f for f in new_meta if f not in old_meta}
    removed = {f for f in old_meta if f not in new_meta}
    changed = {f for f in new_meta if f in old_meta and new_meta[f] != old_meta[f]}

    lines = []
    for f in sorted(added):
        lines.append(f"[+] Added field: {f} (type: {new_meta[f]})")
    for f in sorted(removed):
        lines.append(f"[-] Removed field: {f}")
    for f in sorted(changed):
        lines.append(f"[*] Changed: {f} (type: {old_meta[f]} -> {new_meta[f]})")

    custom = [f for f in added if _is_custom(f)]
    if custom:
        lines.append("")
        lines.append("New custom indicators: " + ", ".join(sorted(custom)))

    changed_flag = bool(lines)
    if changed_flag:
        lines.append("")
        lines.append(f"Recommendation: run `tvgen generate --market {market}`")

    return "\n".join(lines), changed_flag


__all__ = [
    "backup_results",
    "update_cache",
    "diff_market",
]
