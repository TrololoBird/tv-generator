from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.cli import cli


def _list_commands() -> Iterable[tuple[str, str]]:
    """Return sorted pairs of command name and short help."""
    cmds = []
    for name, command in cli.commands.items():
        help_text = command.help or ""
        cmds.append((name, help_text))
    return sorted(cmds)


def generate_readme(path: Path = Path("README.generated.md")) -> Path:
    """Generate README content with CLI command list."""
    lines: list[str] = []
    lines.append("# tv-generator")
    lines.append("")
    lines.append(
        "🧠 **tv-generator** — это CLI-инструмент для автоматической "
        "генерации OpenAPI 3.1 спецификаций на основе TradingView API "
        "`/scan` и `/metainfo`."
    )
    lines.append("")
    lines.append(
        "🔗 Онлайн OpenAPI: "
        "[crypto.yaml](https://trololobird.github.io/tv-generator/specs/crypto.yaml)"
    )
    lines.append("")
    lines.append("## 📦 Установка")
    lines.append("")
    lines.extend(
        [
            "```bash",
            "git clone https://github.com/TrololoBird/tv-generator.git",
            "cd tv-generator",
            "pip install -e .[dev]",
            "```",
            "",
        ]
    )
    lines.append("## 🚀 Быстрый старт")
    lines.append("")
    lines.extend(
        [
            "```bash",
            "tvgen collect --market crypto",
            "tvgen generate --market crypto --outdir specs",
            "tvgen validate --spec specs/crypto.yaml",
            "```",
            "",
            "Однострочный пример: `tvgen generate --market crypto --outdir specs`",
            "",
        ]
    )
    lines.append("## 🛠️ CLI команды")
    lines.append("")
    for name, help_text in _list_commands():
        lines.append(f"- `{name}` - {help_text}")
    lines.append("")
    lines.append("## Публикация спецификаций")
    lines.append("")
    lines.extend(
        [
            "```bash",
            "python scripts/publish_pages.py --branch gh-pages",
            "```",
            "",
        ]
    )
    lines.append("## 📁 Структура проекта")
    lines.append("")
    lines.extend(
        [
            "- `src/` — исходный код CLI и генератора",
            "- `results/` — сохранённые ответы TradingView",
            "- `specs/` — итоговые спецификации OpenAPI",
            "",
        ]
    )
    lines.append("## 🎯 Цель")
    lines.append("")
    lines.append("Генерация OpenAPI 3.1 спецификаций на основе TradingView.")
    lines.append("")
    lines.extend(
        [
            "## Timeframe codes",
            "```",
            "1, 5, 15, 30, 60, 120, 240   -> minutes",
            "1D                          -> 1 day",
            "1W                          -> 1 week",
            "```",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":  # pragma: no cover - manual execution
    generate_readme()
