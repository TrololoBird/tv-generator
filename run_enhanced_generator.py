#!/usr/bin/env python3
"""
Enhanced OpenAPI Generator Runner
Скрипт для запуска расширенного генератора OpenAPI спецификаций
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enhanced_generator_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска"""
    start_time = datetime.now()
    logger.info("🚀 Запуск расширенного генератора OpenAPI спецификаций")

    try:
        # Импортируем основной генератор
        from enhanced_generator import EnhancedOpenAPIGenerator

        # Создаем экземпляр генератора
        generator = EnhancedOpenAPIGenerator()

        # Запускаем полный пайплайн
        success = await generator.run_full_pipeline()

        end_time = datetime.now()
        duration = end_time - start_time

        if success:
            logger.info(f"✅ Генерация завершена успешно за {duration}")
            logger.info("📊 Результаты сохранены в директории results/")
            logger.info("📋 Спецификации обновлены в директории specs/")
            return 0
        else:
            logger.error(f"❌ Генерация завершилась с ошибками за {duration}")
            return 1

    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        logger.error("Убедитесь, что установлены все зависимости: pip install -r requirements-enhanced.txt")
        return 1
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return 1

if __name__ == "__main__":
    # Создаем директорию для логов
    Path("logs").mkdir(exist_ok=True)

    # Запускаем генератор
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
