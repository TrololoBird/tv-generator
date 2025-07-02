#!/usr/bin/env python3
"""
Unified Market Processor - унифицированный обработчик для любого рынка TradingView
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from tv_generator.api import TradingViewAPI
from tv_generator.core import OpenAPIPipeline
from tv_generator.sync import sync_markets, sync_metainfo, sync_scan
from tv_generator.validation import validate_all_specs

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class UnifiedMarketProcessor:
    """Унифицированный процессор для обработки любого рынка TradingView."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Инициализация процессора."""
        self.config = config or {}
        self.api_client = TradingViewAPI()
        self.pipeline = OpenAPIPipeline(
            data_dir=Path(self.config.get("data_dir", "data")),
            specs_dir=Path(self.config.get("specs_dir", "docs/specs")),
            results_dir=Path(self.config.get("results_dir", "results")),
            api_client=self.api_client,
            cache_dir=Path("cache"),
            setup_logging=False,  # Мы настроим логирование сами
            compact=self.config.get("compact", False),
            max_fields=self.config.get("max_fields", None),
        )

        # Статистика обработки
        self.stats = {
            "processed_markets": 0,
            "successful_markets": 0,
            "failed_markets": [],
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    def setup_logging(self, verbose: bool = False, log_file: str | None = None) -> None:
        """Настройка логирования."""
        level = "DEBUG" if verbose else "INFO"
        logger.remove()

        # Консольный логгер
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )

        # Файловый логгер
        if log_file:
            log_path = Path("logs") / log_file
            log_path.parent.mkdir(exist_ok=True)
            logger.add(
                log_path,
                level=level,
                format=("{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - " "{message}"),
                rotation="10 MB",
                retention="7 days",
            )

    def is_data_stale(self, path: Path, hours: int = 24) -> bool:
        """Проверка устаревания данных."""
        if not path.exists():
            return True

        file_age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        return file_age > timedelta(hours=hours)

    async def update_base_data(self, force: bool = False) -> bool:
        """Обновление базовых данных (markets.json, display_names)."""
        logger.info("Обновление базовых данных...")

        try:
            # Обновление списка рынков
            markets_path = Path("data/markets.json")
            if force or self.is_data_stale(markets_path):
                logger.info("Обновление списка рынков...")
                sync_markets()

            # Обновление display names
            display_names_path = Path("data/column_display_names.json")
            if force or self.is_data_stale(display_names_path):
                logger.info("Обновление display names...")
                from tv_generator.sync import sync_display_names

                sync_display_names()

            logger.success("Базовые данные обновлены")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления базовых данных: {e}")
            self.stats["errors"].append(f"Base data update error: {e}")
            return False

    async def market_task_runner(self, markets: list[str], coro_func, task_name: str) -> int:
        """Общий шаблон для массовых асинхронных задач по рынкам с параллелизмом и обработкой ошибок."""
        logger.info(f"{task_name} для {len(markets)} рынков...")
        results = []
        errors = []
        sem = asyncio.Semaphore(8)  # ограничение параллелизма (можно вынести в конфиг)

        async def safe_task(market):
            async with sem:
                try:
                    await coro_func(market)
                    logger.success(f"{task_name} для {market} успешно")
                    return (market, True)
                except Exception as e:
                    logger.error(f"Ошибка {task_name} для {market}: {e}")
                    errors.append((market, str(e)))
                    return (market, False)

        results = await asyncio.gather(*(safe_task(m) for m in markets))
        success_count = sum(1 for _, ok in results if ok)
        fail_count = len(markets) - success_count
        logger.info(f"{task_name}: {success_count}/{len(markets)} успешно, " f"{fail_count} с ошибками")
        if errors:
            self.stats["failed_markets"].extend([m for m, _ in errors])
            self.stats["errors"].extend([f"{task_name} {m} error: {e}" for m, e in errors])
        return success_count

    async def update_market_data(self, markets: list[str], force: bool = False) -> bool:
        async def update_one(market):
            metainfo_path = Path(f"data/metainfo/{market}.json")
            if force or self.is_data_stale(metainfo_path):
                logger.info(f"Обновление metainfo для {market}...")
                sync_metainfo(market)
            scan_path = Path(f"data/scan/{market}.json")
            if force or self.is_data_stale(scan_path):
                logger.info(f"Обновление scan данных для {market}...")
                sync_scan(market)

        success_count = await self.market_task_runner(markets, update_one, "Обновление данных")
        self.stats["processed_markets"] = len(markets)
        self.stats["successful_markets"] = success_count
        return success_count == len(markets)

    async def generate_specifications(self, markets: list[str]) -> bool:
        async def generate_one(market):
            metainfo_path = Path(f"data/metainfo/{market}.json")
            scan_path = Path(f"data/scan/{market}.json")
            if not metainfo_path.exists():
                raise RuntimeError(f"Metainfo для {market} не найден")
            if not scan_path.exists():
                raise RuntimeError(f"Scan данные для {market} не найдены")
            ok = await self.pipeline.generate_and_save_spec(market)
            if not ok:
                raise RuntimeError(f"Ошибка генерации спецификации для {market}")

        success_count = await self.market_task_runner(markets, generate_one, "Генерация спецификаций")
        return success_count > 0

    async def validate_specifications(self, markets: list[str]) -> bool:
        """Валидация сгенерированных спецификаций."""
        logger.info(f"Валидация спецификаций для {len(markets)} рынков...")

        try:
            # Используем встроенную валидацию
            validation_result = await validate_all_specs(markets)

            if validation_result.success:
                logger.success("Все спецификации прошли валидацию")
                return True
            else:
                logger.warning(f"Валидация завершена с предупреждениями: {validation_result.errors}")
                return True  # Предупреждения не критичны

        except Exception as e:
            logger.error(f"Ошибка валидации: {e}")
            self.stats["errors"].append(f"Validation error: {e}")
            return False

    async def test_api_endpoints(self, markets: list[str]) -> bool:
        async def test_one(market):
            metainfo_data = await self.api_client.get_metainfo(market)
            if not metainfo_data:
                raise RuntimeError(f"Ошибка получения metainfo для {market}")
            scan_data = await self.api_client.scan_tickers(market, "stock", limit=10, filters=[])
            if not scan_data:
                raise RuntimeError(f"Ошибка scan API для {market}")

        success_count = await self.market_task_runner(markets, test_one, "Тест API")
        return success_count > 0

    async def process_markets(self, markets: list[str], steps: list[str], force: bool = False) -> bool:
        """Основной метод обработки рынков."""
        self.stats["start_time"] = datetime.now()
        logger.info(f"Начало обработки {len(markets)} рынков: {', '.join(markets)}")

        try:
            # Шаг 1: Обновление базовых данных
            if "update_base" in steps:
                if not await self.update_base_data(force):
                    logger.error("Ошибка обновления базовых данных")
                    return False

            # Шаг 2: Обновление данных рынков
            if "update_markets" in steps:
                if not await self.update_market_data(markets, force):
                    logger.warning("Не все данные рынков обновлены")

            # Шаг 3: Тестирование API
            if "test_api" in steps:
                if not await self.test_api_endpoints(markets):
                    logger.warning("API тесты не прошли для всех рынков")

            # Шаг 4: Генерация спецификаций
            if "generate_specs" in steps:
                if not await self.generate_specifications(markets):
                    logger.error("Ошибка генерации спецификаций")
                    return False

            # Шаг 5: Валидация спецификаций
            if "validate_specs" in steps:
                if not await self.validate_specifications(markets):
                    logger.warning("Валидация спецификаций завершена с ошибками")

            self.stats["end_time"] = datetime.now()
            duration = self.stats["end_time"] - self.stats["start_time"]

            logger.success(f"Обработка завершена за {duration.total_seconds():.2f} секунд")
            logger.info(f"Успешно обработано: {self.stats['successful_markets']}/" f"{self.stats['processed_markets']}")

            if self.stats["failed_markets"]:
                logger.warning(f"Неудачные рынки: {', '.join(self.stats['failed_markets'])}")

            return True

        except Exception as e:
            logger.error(f"Критическая ошибка обработки: {e}")
            self.stats["errors"].append(f"Critical error: {e}")
            return False

    def get_available_markets(self) -> list[str]:
        """Получение списка доступных рынков."""
        try:
            markets_path = Path("data/markets.json")
            if markets_path.exists():
                with open(markets_path, encoding="utf-8") as f:
                    markets = json.load(f)
                return markets if isinstance(markets, list) else []
            else:
                # Возвращаем стандартные рынки если файл не найден
                return ["stock", "forex", "crypto", "futures", "cfd", "bonds", "etf", "index"]
        except Exception as e:
            logger.error(f"Ошибка загрузки списка рынков: {e}")
            return []

    def save_report(self, output_path: str | None = None) -> None:
        """Сохранение отчета о обработке."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"results/processing_report_{timestamp}.json"

        report_path = Path(output_path)
        report_path.parent.mkdir(exist_ok=True)

        # Добавляем дополнительную информацию в отчет
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "config": self.config,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Отчет сохранен: {report_path}")


async def main():
    """Главная функция CLI."""
    parser = argparse.ArgumentParser(
        description="Унифицированный обработчик рынков TradingView",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            """
Примеры использования:
  # Обработка всех рынков
  python unified_market_processor.py --all
  # Обработка конкретных рынков
  python unified_market_processor.py --markets stock forex crypto
  # Только обновление данных
  python unified_market_processor.py --markets stock --steps update_base,update_markets
  # Принудительное обновление
  python unified_market_processor.py --markets stock --force
  # Подробное логирование
  python unified_market_processor.py --markets stock --verbose
            """
        ),
    )

    # Основные параметры
    parser.add_argument("--markets", nargs="+", help="Список рынков для обработки")
    parser.add_argument("--all", action="store_true", help="Обработать все доступные рынки")
    parser.add_argument(
        "--steps",
        nargs="+",
        default=["update_base", "update_markets", "test_api", "generate_specs", "validate_specs"],
        choices=["update_base", "update_markets", "test_api", "generate_specs", "validate_specs"],
        help="Шаги обработки (по умолчанию: все шаги)",
    )

    # Параметры поведения
    parser.add_argument("--force", action="store_true", help="Принудительное обновление данных")
    parser.add_argument("--verbose", action="store_true", help="Подробное логирование")
    parser.add_argument("--log-file", help="Файл для сохранения логов")
    parser.add_argument("--report", help="Путь для сохранения отчета")

    # Параметры конфигурации
    parser.add_argument("--data-dir", default="data", help="Директория с данными (по умолчанию: data)")
    parser.add_argument(
        "--specs-dir", default="docs/specs", help="Директория для спецификаций (по умолчанию: docs/specs)"
    )
    parser.add_argument("--results-dir", default="results", help="Директория для результатов (по умолчанию: results)")
    parser.add_argument("--compact", action="store_true", help="Генерировать компактную OpenAPI спецификацию (≤1MB)")
    parser.add_argument(
        "--max-fields", type=int, default=None, help="Максимальное число полей в спецификации (например, 200)"
    )

    args = parser.parse_args()

    # Проверка аргументов
    if not args.markets and not args.all:
        parser.error("Необходимо указать --markets или --all")

    # Настройка процессора
    config = {
        "data_dir": args.data_dir,
        "specs_dir": args.specs_dir,
        "results_dir": args.results_dir,
        "force": args.force,
        "steps": args.steps,
        "compact": args.compact,
        "max_fields": args.max_fields,
    }

    processor = UnifiedMarketProcessor(config)
    processor.setup_logging(verbose=args.verbose, log_file=args.log_file)

    # Определение списка рынков
    if args.all:
        markets = processor.get_available_markets()
        if not markets:
            logger.error("Не удалось получить список рынков")
            return 1
    else:
        markets = args.markets

    logger.info(f"Обработка рынков: {', '.join(markets)}")
    logger.info(f"Шаги: {', '.join(args.steps)}")

    # Выполнение обработки
    success = await processor.process_markets(markets, args.steps, args.force)

    # Сохранение отчета
    if args.report:
        processor.save_report(args.report)
    else:
        processor.save_report()

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Обработка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        # TODO: Аудит — глухой except, требуется уточнение типов ошибок
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
