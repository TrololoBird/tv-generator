from __future__ import annotations

from pathlib import Path
import datetime
import subprocess
import toml
import yaml
from src.utils.fs import load_yaml

"""Helpers for project version management and changelog generation."""

DEFAULT_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"
DEFAULT_SPECS_DIR = Path(__file__).resolve().parents[2] / "specs"


def _load_pyproject(path: Path) -> dict:
    """Load ``pyproject.toml`` as a dictionary.

    Parameters
    ----------
    path : Path
        Path to the ``pyproject.toml`` file.

    Returns
    -------
    dict
        Parsed TOML mapping.

    Raises
    ------
    RuntimeError
        If the file does not exist.
    """

    try:
        return toml.load(path)
    except FileNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("pyproject.toml not found") from exc


def get_version(path: Path | None = None) -> str:
    """Return project version from ``pyproject.toml``.

    Parameters
    ----------
    path : Path | None, optional
        Path to the ``pyproject.toml`` file. If ``None`` the default
        repository file is used.

    Returns
    -------
    str
        Version string defined in the project metadata.

    Raises
    ------
    RuntimeError
        If the version cannot be found.
    """

    path = path or DEFAULT_PYPROJECT_PATH
    data = _load_pyproject(path)
    version = data.get("project", {}).get("version") or data.get("tool", {}).get(
        "poetry", {}
    ).get("version")
    if not version:
        raise RuntimeError("Version not found in pyproject.toml")
    return str(version)


def get_current_version() -> str:
    """Return current project version using default ``pyproject.toml``."""

    return get_version()


def _write_pyproject(data: dict, path: Path) -> None:
    """Write modified project metadata back to disk."""

    path.write_text(toml.dumps(data))


def set_version(new_version: str, path: Path | None = None) -> None:
    """Update the version string in ``pyproject.toml``.

    Parameters
    ----------
    new_version : str
        New semantic version value.
    path : Path | None, optional
        Location of ``pyproject.toml``. Defaults to the repository file.

    Raises
    ------
    RuntimeError
        If the version field cannot be located.
    """

    path = path or DEFAULT_PYPROJECT_PATH
    data = _load_pyproject(path)
    if "project" in data and "version" in data["project"]:
        data["project"]["version"] = new_version
    elif data.get("tool", {}).get("poetry", {}).get("version"):
        data.setdefault("tool", {}).setdefault("poetry", {})["version"] = new_version
    else:
        raise RuntimeError("Version not found in pyproject.toml")
    _write_pyproject(data, path)


def _increment(version: str, kind: str) -> str:
    """Return ``version`` incremented according to ``kind``.

    Parameters
    ----------
    version : str
        Base semantic version string.
    kind : str
        One of ``"patch"``, ``"minor"`` or ``"major"``.

    Returns
    -------
    str
        Incremented version string.

    Raises
    ------
    ValueError
        If ``kind`` is not a valid increment type.
    """

    parts = [int(p) for p in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    if kind == "patch":
        parts[2] += 1
    elif kind == "minor":
        parts[1] += 1
        parts[2] = 0
    elif kind == "major":
        parts[0] += 1
        parts[1] = parts[2] = 0
    else:  # pragma: no cover - click validation prevents
        raise ValueError(f"invalid version type: {kind}")
    return ".".join(str(p) for p in parts)


def _update_spec_files(version: str, specs_dir: Path) -> None:
    """Update ``info.version`` field for all spec files in ``specs_dir``."""

    for spec_file in specs_dir.glob("*.yaml"):
        try:
            data = load_yaml(spec_file, max_size=5_242_880)
        except Exception:  # pragma: no cover - malformed YAML
            continue
        if isinstance(data, dict) and "info" in data:
            data.setdefault("info", {})["version"] = version
            spec_file.write_text(yaml.dump(data, sort_keys=False))


def bump_version(
    kind: str, *, pyproject: Path | None = None, specs_dir: Path | None = None
) -> str:
    """Increment project version and update specifications.

    Parameters
    ----------
    kind : str
        Type of version bump: ``"patch"``, ``"minor"`` or ``"major"``.
    pyproject : Path | None, optional
        Path to ``pyproject.toml``. Defaults to repository file.
    specs_dir : Path | None, optional
        Directory containing YAML specs to update.

    Returns
    -------
    str
        The newly assigned version string.
    """

    pyproject = pyproject or DEFAULT_PYPROJECT_PATH
    specs_dir = specs_dir or DEFAULT_SPECS_DIR
    current = get_version(pyproject)
    new_version = _increment(current, kind)
    set_version(new_version, pyproject)
    if specs_dir.exists():
        _update_spec_files(new_version, specs_dir)
    return new_version


def _collect_commits(range_spec: str) -> list[str]:
    """Return commit messages for the given git range."""

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-merges", range_spec],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError:  # pragma: no cover - git absent
        return []
    lines = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            lines.append(parts[1])
    return lines


def generate_changelog(
    pyproject: Path | None = None, changelog: Path | None = None
) -> Path:
    """Create or update ``CHANGELOG.md`` using git history.

    Parameters
    ----------
    pyproject : Path | None, optional
        Project metadata file used to obtain the current version.
    changelog : Path | None, optional
        Target changelog file. Defaults to ``CHANGELOG.md`` in the
        repository root.

    Returns
    -------
    Path
        Path to the generated changelog file.
    """

    pyproject = pyproject or DEFAULT_PYPROJECT_PATH
    changelog = changelog or Path("CHANGELOG.md")

    version = get_version(pyproject)
    try:
        last_tag = subprocess.run(
            ["git", "describe", "--abbrev=0", "--tags"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        last_tag = ""

    range_spec = f"{last_tag}..HEAD" if last_tag else "HEAD"
    messages = _collect_commits(range_spec)
    date = datetime.date.today().isoformat()

    if changelog.exists():
        content = changelog.read_text().splitlines()
    else:
        content = ["# Changelog", ""]

    header_index = 1 if content and content[0].startswith("#") else 0
    entry = [f"## [{version}] — {date}", ""]
    entry.extend(f"- {m}" for m in messages)
    entry.append("")
    content[header_index:header_index] = entry
    changelog.write_text("\n".join(content) + "\n")
    return changelog
