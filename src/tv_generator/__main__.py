#!/usr/bin/env python3
"""
Entry point for tv-generator package
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем функцию main из main.py
from .main import main

if __name__ == "__main__":
    asyncio.run(main())
