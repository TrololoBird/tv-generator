#!/usr/bin/env python3
"""
TradingView OpenAPI Generator - Main Entry Point
Главная точка входа для генератора OpenAPI спецификаций
"""

import sys
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from tv_generator.cli import main

if __name__ == "__main__":
    main()
