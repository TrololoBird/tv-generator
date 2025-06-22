#!/usr/bin/env python3
"""
Простой CLI для TradingView OpenAPI Generator без Typer.
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import json

from .core import Pipeline
from .api import TradingViewAPI
from .config import settings


def setup_logging(verbose: bool = False) -> None:
    """Настройка логирования."""
    from loguru import logger
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем новый обработчик
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        format=settings.log_format,
        level=log_level,
        colorize=True
    )
    
    return logger


def info() -> None:
    """Показать информацию о проекте."""
    print("🚀 TradingView OpenAPI Generator")
    print("=" * 50)
    print(f"Python: {sys.version}")
    print(f"API URL: {settings.tradingview_base_url}")
    print(f"Таймаут: {settings.request_timeout}s")
    print(f"Rate Limit: {settings.requests_per_second} req/s")
    print()
    
    print("📊 Доступные рынки:")
    for name, config in settings.markets.items():
        print(f"  • {name}: {config['description']} ({config['endpoint']})")
    print()
    
    print("📁 Директории:")
    print(f"  • Результаты: {settings.results_dir}")
    print(f"  • Спецификации: {settings.specs_dir}")
    print()
    
    print("🔧 Команды:")
    print("  • info - показать эту информацию")
    print("  • fetch-data - получить данные с TradingView")
    print("  • test-specs - протестировать спецификации")
    print("  • generate - сгенерировать OpenAPI спецификации")
    print("  • health - проверить здоровье системы")


async def fetch_data(markets: Optional[List[str]] = None, verbose: bool = False) -> None:
    """Получить данные с TradingView."""
    logger = setup_logging(verbose)
    
    try:
        logger.info("🚀 Запуск получения данных с TradingView")
        
        pipeline = Pipeline()
        await pipeline.run()
        
        logger.info("✅ Данные успешно получены")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении данных: {e}")
        sys.exit(1)


async def test_specs(verbose: bool = False) -> None:
    """Протестировать спецификации."""
    logger = setup_logging(verbose)

    try:
        logger.info("🧪 Тестирование спецификаций")

        # Простая проверка спецификаций без внешнего модуля
        specs_dir = Path(settings.specs_dir)
        if not specs_dir.exists():
            logger.error("❌ Директория спецификаций не найдена")
            return

        spec_files = list(specs_dir.glob("*.json"))
        if not spec_files:
            logger.warning("⚠️ Спецификации не найдены")
            return

        logger.info(f"📋 Найдено {len(spec_files)} спецификаций")

        for spec_file in spec_files:
            try:
                with open(spec_file, 'r', encoding='utf-8') as f:
                    spec_data = json.load(f)
                
                # Базовая валидация OpenAPI спецификации
                if "openapi" not in spec_data:
                    logger.error(f"❌ {spec_file.name}: Не является OpenAPI спецификацией")
                    continue
                
                if "paths" not in spec_data:
                    logger.error(f"❌ {spec_file.name}: Отсутствуют пути (paths)")
                    continue
                
                if "info" not in spec_data:
                    logger.error(f"❌ {spec_file.name}: Отсутствует информация (info)")
                    continue
                
                logger.info(f"✅ {spec_file.name}: Валидна")
                
            except json.JSONDecodeError:
                logger.error(f"❌ {spec_file.name}: Невалидный JSON")
            except Exception as e:
                logger.error(f"❌ {spec_file.name}: Ошибка - {e}")

        logger.info("✅ Тестирование спецификаций завершено")

    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        raise


async def generate(output: Optional[str] = None, verbose: bool = False) -> None:
    """Генерировать OpenAPI спецификации."""
    logger = setup_logging(verbose)
    
    try:
        logger.info("📝 Генерация OpenAPI спецификаций")
        
        # Импорт здесь для избежания циклических зависимостей
        from generate_openapi import main as gen_main
        gen_main()
        
        logger.info("✅ Генерация завершена успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации: {e}")
        sys.exit(1)


async def health(verbose: bool = False) -> None:
    """Проверить здоровье системы."""
    logger = setup_logging(verbose)
    
    try:
        logger.info("🏥 Проверка здоровья системы")
        
        api = TradingViewAPI()
        async with api:
            health_status = await api.health_check()
        
        pipeline = Pipeline()
        pipeline_health = await pipeline.health_check()
        
        print("📊 Статус здоровья системы:")
        print(f"  • API: {health_status['status']}")
        print(f"  • Pipeline: {pipeline_health['pipeline']}")
        
        if health_status['endpoints']:
            print("  • Эндпоинты:")
            for endpoint, status in health_status['endpoints'].items():
                print(
                    f"    - {endpoint}: {status}"
                )
        
        logger.info("✅ Проверка здоровья завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке здоровья: {e}")
        sys.exit(1)


def validate() -> None:
    """Валидация конфигурации и зависимостей."""
    print("🔍 Валидация конфигурации...")
    
    # Проверка директорий
    results_dir = Path(settings.results_dir)
    specs_dir = Path(settings.specs_dir)
    
    print("📁 Проверка директорий:")
    if results_dir.exists():
        print(f"  ✅ Директория результатов: {results_dir}")
    else:
        print(
            f"  ⚠️ Директория результатов: {results_dir} (создастся автоматически)"
        )
    
    if specs_dir.exists():
        print(f"  ✅ Директория спецификаций: {specs_dir}")
    else:
        print(
            f"  ⚠️ Директория спецификаций: {specs_dir} (создастся автоматически)"
        )
    
    print("📊 Проверка конфигурации:")
    print(
        f"  ✅ Конфигурация рынков: {len(settings.markets)} рынков"
    )
    print(f"  ✅ API URL: {settings.tradingview_base_url}")
    print(f"  ✅ Таймаут: {settings.request_timeout}s")
    print(f"  ✅ Rate Limit: {settings.requests_per_second} req/s")


def main() -> None:
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "TradingView OpenAPI Generator - "
            "автоматизированный генератор OpenAPI 3.1.0 спецификаций"
        )
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")
    
    # Команда info
    subparsers.add_parser("info", help="Показать информацию о проекте")
    
    # Команда fetch-data
    fetch_parser = subparsers.add_parser("fetch-data", help="Получить данные с TradingView")
    fetch_parser.add_argument(
        "--markets",
        nargs="+",
        help=(
            "Конкретные рынки для обработки"
        )
    )
    
    # Команда test-specs
    subparsers.add_parser("test-specs", help="Протестировать спецификации")
    
    # Команда generate
    generate_parser = subparsers.add_parser("generate", help="Генерировать OpenAPI спецификации")
    generate_parser.add_argument(
        "--output", "-o",
        help=(
            "Путь для сохранения OpenAPI спецификации"
        )
    )
    
    # Команда health
    subparsers.add_parser("health", help="Проверить здоровье системы")
    
    # Команда validate
    subparsers.add_parser("validate", help="Валидация конфигурации и зависимостей")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Выполнение команд
    if args.command == "info":
        info()
    elif args.command == "fetch-data":
        asyncio.run(fetch_data(args.markets, args.verbose))
    elif args.command == "test-specs":
        asyncio.run(test_specs(args.verbose))
    elif args.command == "generate":
        asyncio.run(generate(args.output, args.verbose))
    elif args.command == "health":
        asyncio.run(health(args.verbose))
    elif args.command == "validate":
        validate()


if __name__ == "__main__":
    main()
