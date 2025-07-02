#!/usr/bin/env python3
"""
CLI interface for tv-generator package.
This is a compatibility layer that uses the main.py functionality.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tv_generator.main import main as main_function


def main():
    """Main CLI entry point."""
    asyncio.run(main_function())


if __name__ == "__main__":
    main()
