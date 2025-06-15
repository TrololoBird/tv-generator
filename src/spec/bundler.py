from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import yaml


def bundle_all_specs(
    spec_dir: str | Path, outfile: str | Path, format: str = "json"
) -> Path:
    """Bundle all YAML specs under *spec_dir* into a single file.

    Each ``*.yaml`` file is loaded and placed under a key named after the file
    stem (market name). The resulting dictionary is written to ``outfile`` in
    the requested *format* (``json`` or ``yaml``).
    """

    base = Path(spec_dir)
    data: Dict[str, Any] = {}
    for yaml_file in base.glob("*.yaml"):
        with yaml_file.open("r", encoding="utf-8") as fh:
            data[yaml_file.stem] = yaml.safe_load(fh)

    out_path = Path(outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if format == "json":
        out_path.write_text(json.dumps(data, indent=2))
    else:
        out_path.write_text(yaml.safe_dump(data, sort_keys=False))
    return out_path
