#!/usr/bin/env python3
"""
Скрипт для настройки dev окружения с pre-commit хуками.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Выполнить команду с обработкой ошибок."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ошибка:")
        print(f"   Команда: {cmd}")
        print(f"   Ошибка: {e.stderr}")
        return False


def main():
    """Основная функция настройки."""
    print("🚀 Настройка dev окружения для TradingView OpenAPI Generator")
    print("=" * 60)
    
    # Проверяем, что мы в корне проекта
    if not Path(".pre-commit-config.yaml").exists():
        print("❌ .pre-commit-config.yaml не найден. Запустите скрипт из корня проекта.")
        sys.exit(1)
    
    # Устанавливаем зависимости
    success = True
    
    success &= run_command(
        "python -m pip install --upgrade pip",
        "Обновление pip"
    )
    
    success &= run_command(
        "pip install -e .[dev]",
        "Установка проекта в dev режиме"
    )
    
    success &= run_command(
        "pip install pre-commit",
        "Установка pre-commit"
    )
    
    # Устанавливаем pre-commit хуки
    success &= run_command(
        "pre-commit install",
        "Установка pre-commit хуков"
    )
    
    # Обновляем pre-commit хуки
    success &= run_command(
        "pre-commit autoupdate",
        "Обновление pre-commit хуков"
    )
    
    # Запускаем pre-commit на всех файлах
    success &= run_command(
        "pre-commit run --all-files",
        "Запуск pre-commit на всех файлах"
    )
    
    if success:
        print("\n🎉 Настройка dev окружения завершена успешно!")
        print("\n📋 Доступные команды:")
        print("   tvgen --help          - Справка по CLI")
        print("   tvgen info            - Информация о проекте")
        print("   tvgen fetch-data      - Сбор данных")
        print("   tvgen generate        - Генерация спецификаций")
        print("   tvgen validate        - Валидация спецификаций")
        print("   pytest                - Запуск тестов")
        print("   pre-commit run        - Запуск pre-commit хуков")
    else:
        print("\n❌ Настройка завершена с ошибками. Проверьте вывод выше.")
        sys.exit(1)


if __name__ == "__main__":
    main() 