#!/usr/bin/env python3
"""
Скрипт для автоматической очистки проекта TradingView OpenAPI Generator
перед новым релизом или генерацией.
"""

import os
import shutil
import glob


def cleanup_directories():
    """Очищает временные директории и файлы."""
    directories_to_clean = [
        'results',
        'logs', 
        'specs'
    ]
    
    for directory in directories_to_clean:
        if os.path.exists(directory):
            print(f"🧹 Очищаю директорию: {directory}")
            try:
                shutil.rmtree(directory)
                os.makedirs(directory, exist_ok=True)
                print(f"✅ {directory} очищена")
            except Exception as e:
                print(f"❌ Ошибка при очистке {directory}: {e}")


def cleanup_temp_files():
    """Удаляет временные файлы."""
    temp_patterns = [
        '*.tmp',
        '*.cache',
        '*.log',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache'
    ]
    
    for pattern in temp_patterns:
        matches = glob.glob(pattern, recursive=True)
        for match in matches:
            try:
                if os.path.isfile(match):
                    os.remove(match)
                elif os.path.isdir(match):
                    shutil.rmtree(match)
                print(f"🗑️ Удалён: {match}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {match}: {e}")


def cleanup_old_specs():
    """Удаляет старые спецификации."""
    spec_patterns = [
        'specs/*.yaml',
        'specs/*.yml',
        'specs/*.json.bak'
    ]
    
    for pattern in spec_patterns:
        matches = glob.glob(pattern)
        for match in matches:
            try:
                os.remove(match)
                print(f"🗑️ Удалена старая спецификация: {match}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {match}: {e}")


def main():
    """Основная функция очистки."""
    print("🚀 Начинаю очистку проекта TradingView OpenAPI Generator")
    print("=" * 60)
    
    # Очистка директорий
    cleanup_directories()
    
    # Очистка временных файлов
    cleanup_temp_files()
    
    # Очистка старых спецификаций
    cleanup_old_specs()
    
    print("=" * 60)
    print("✅ Очистка завершена!")
    print("📝 Проект готов к новой генерации спецификаций")


if __name__ == "__main__":
    main() 