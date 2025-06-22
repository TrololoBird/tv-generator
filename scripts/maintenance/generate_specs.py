#!/usr/bin/env python3
"""
Script for generating OpenAPI specifications
Скрипт для генерации OpenAPI спецификаций
"""

import sys
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))

from tv_generator.core import generate_all_specifications

def main():
    """Генерирует все спецификации"""
    print("🚀 Генерация OpenAPI спецификаций...")
    
    try:
        generate_all_specifications()
        print("✅ Генерация завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
