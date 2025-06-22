#!/usr/bin/env python3
"""
Project Structure Optimization Script
Дополнительная оптимизация структуры проекта
"""

import os
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectStructureOptimizer:
    """Класс для оптимизации структуры проекта"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.optimizations = []
        
    def create_standard_structure(self):
        """Создает стандартную структуру проекта"""
        logger.info("🏗️ Создание стандартной структуры проекта...")
        
        # Стандартные директории
        standard_dirs = [
            'src',
            'src/tv_generator',
            'scripts/utils',
            'scripts/maintenance',
            'docs/api',
            'docs/user_guide',
            'data/raw',
            'data/processed',
            'reports',
            'backups'
        ]
        
        for dir_path in standard_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                self.optimizations.append(f"Создана директория: {dir_path}")
                logger.info(f"Создана директория: {dir_path}")
        
        # Создаем __init__.py в src/tv_generator
        init_file = self.project_root / 'src' / 'tv_generator' / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            self.optimizations.append(f"Создан файл: {init_file}")
    
    def move_main_package_to_src(self):
        """Перемещает основной пакет в src/"""
        logger.info("📦 Перемещение основного пакета в src/...")
        
        current_package = self.project_root / 'tv_generator'
        target_package = self.project_root / 'src' / 'tv_generator'
        
        if current_package.exists() and not target_package.exists():
            try:
                # Перемещаем все файлы кроме __init__.py (он уже создан)
                for item in current_package.iterdir():
                    if item.name != '__init__.py':
                        shutil.move(str(item), str(target_package / item.name))
                
                # Удаляем старую директорию
                shutil.rmtree(current_package)
                self.optimizations.append("Перемещен пакет tv_generator в src/")
                logger.info("Перемещен пакет tv_generator в src/")
            except OSError as e:
                logger.warning(f"Не удалось переместить пакет: {e}")
    
    def consolidate_scripts(self):
        """Консолидирует скрипты по категориям"""
        logger.info("🔧 Консолидация скриптов...")
        
        # Категории скриптов
        script_categories = {
            'maintenance': ['cleanup.py', 'optimize_structure.py'],
            'utils': ['validation_and_ci.py', 'openapi_updater.py']
        }
        
        for category, scripts in script_categories.items():
            category_dir = self.project_root / 'scripts' / category
            category_dir.mkdir(exist_ok=True)
            
            for script in scripts:
                script_path = self.project_root / 'scripts' / script
                if script_path.exists():
                    try:
                        new_path = category_dir / script
                        shutil.move(str(script_path), str(new_path))
                        self.optimizations.append(f"Перемещен скрипт {script} в scripts/{category}/")
                        logger.info(f"Перемещен скрипт {script} в scripts/{category}/")
                    except OSError as e:
                        logger.warning(f"Не удалось переместить {script}: {e}")
    
    def organize_documentation(self):
        """Организует документацию"""
        logger.info("📚 Организация документации...")
        
        # Перемещаем спецификации в docs/
        specs_dir = self.project_root / 'specs'
        docs_specs_dir = self.project_root / 'docs' / 'specs'
        
        if specs_dir.exists() and not docs_specs_dir.exists():
            try:
                shutil.move(str(specs_dir), str(docs_specs_dir))
                self.optimizations.append("Перемещены спецификации в docs/specs/")
                logger.info("Перемещены спецификации в docs/specs/")
            except OSError as e:
                logger.warning(f"Не удалось переместить спецификации: {e}")
        
        # Создаем основной README в docs/
        docs_readme = self.project_root / 'docs' / 'README.md'
        if not docs_readme.exists():
            docs_content = """# Документация проекта

## Структура документации

- `api/` - Документация API
- `user_guide/` - Руководство пользователя
- `specs/` - OpenAPI спецификации
- `README.md` - Этот файл

## Быстрый старт

1. Установка: `pip install -e .`
2. Запуск: `python -m tv_generator`
3. Генерация спецификаций: `python scripts/maintenance/generate_specs.py`

## Подробная документация

См. соответствующие разделы в поддиректориях.
"""
            docs_readme.write_text(docs_content, encoding='utf-8')
            self.optimizations.append("Создан README в docs/")
    
    def organize_data_and_results(self):
        """Организует данные и результаты"""
        logger.info("📊 Организация данных и результатов...")
        
        # Перемещаем результаты в data/processed/
        results_dir = self.project_root / 'results'
        data_processed_dir = self.project_root / 'data' / 'processed'
        
        if results_dir.exists() and not data_processed_dir.exists():
            try:
                shutil.move(str(results_dir), str(data_processed_dir))
                self.optimizations.append("Перемещены результаты в data/processed/")
                logger.info("Перемещены результаты в data/processed/")
            except OSError as e:
                logger.warning(f"Не удалось переместить результаты: {e}")
        
        # Перемещаем логи в reports/
        logs_dir = self.project_root / 'logs'
        reports_dir = self.project_root / 'reports'
        
        if logs_dir.exists():
            try:
                # Перемещаем содержимое logs в reports
                for log_file in logs_dir.iterdir():
                    if log_file.is_file():
                        shutil.move(str(log_file), str(reports_dir / log_file.name))
                
                # Удаляем пустую директорию logs
                shutil.rmtree(logs_dir)
                self.optimizations.append("Перемещены логи в reports/")
                logger.info("Перемещены логи в reports/")
            except OSError as e:
                logger.warning(f"Не удалось переместить логи: {e}")
    
    def create_entry_points(self):
        """Создает точки входа"""
        logger.info("🚪 Создание точек входа...")
        
        # Основной CLI
        main_cli = self.project_root / 'main.py'
        if not main_cli.exists():
            cli_content = """#!/usr/bin/env python3
\"\"\"
TradingView OpenAPI Generator - Main Entry Point
Главная точка входа для генератора OpenAPI спецификаций
\"\"\"

import sys
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from tv_generator.cli import main

if __name__ == "__main__":
    main()
"""
            main_cli.write_text(cli_content, encoding='utf-8')
            self.optimizations.append("Создан главный CLI: main.py")
            logger.info("Создан главный CLI: main.py")
        
        # Скрипт генерации спецификаций
        generate_script = self.project_root / 'scripts' / 'maintenance' / 'generate_specs.py'
        if not generate_script.exists():
            generate_content = """#!/usr/bin/env python3
\"\"\"
Script for generating OpenAPI specifications
Скрипт для генерации OpenAPI спецификаций
\"\"\"

import sys
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))

from tv_generator.core import generate_all_specifications

def main():
    \"\"\"Генерирует все спецификации\"\"\"
    print("🚀 Генерация OpenAPI спецификаций...")
    
    try:
        generate_all_specifications()
        print("✅ Генерация завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
            generate_script.write_text(generate_content, encoding='utf-8')
            self.optimizations.append("Создан скрипт генерации: scripts/maintenance/generate_specs.py")
            logger.info("Создан скрипт генерации: scripts/maintenance/generate_specs.py")
    
    def update_pyproject_toml(self):
        """Обновляет pyproject.toml для новой структуры"""
        logger.info("⚙️ Обновление pyproject.toml...")
        
        pyproject_path = self.project_root / 'pyproject.toml'
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding='utf-8')
                
                # Обновляем пути для новой структуры
                content = content.replace(
                    'packages = ["tv_generator"]',
                    'packages = ["src/tv_generator"]'
                )
                
                # Обновляем entry points
                if 'tvgen = "tv_generator.cli:main"' in content:
                    content = content.replace(
                        'tvgen = "tv_generator.cli:main"',
                        'tvgen = "src.tv_generator.cli:main"'
                    )
                
                if 'tvgen-simple = "tv_generator.simple_cli:main"' in content:
                    content = content.replace(
                        'tvgen-simple = "tv_generator.simple_cli:main"',
                        'tvgen-simple = "src.tv_generator.simple_cli:main"'
                    )
                
                pyproject_path.write_text(content, encoding='utf-8')
                self.optimizations.append("Обновлен pyproject.toml для новой структуры")
                logger.info("Обновлен pyproject.toml для новой структуры")
            except Exception as e:
                logger.warning(f"Не удалось обновить pyproject.toml: {e}")
    
    def create_standard_configs(self):
        """Создает стандартные конфигурационные файлы"""
        logger.info("📋 Создание стандартных конфигураций...")
        
        # .env.example
        env_example = self.project_root / '.env.example'
        if not env_example.exists():
            env_content = """# TradingView OpenAPI Generator Configuration
# Конфигурация генератора OpenAPI спецификаций

# API Configuration
API_BASE_URL=https://scanner.tradingview.com
API_TIMEOUT=30

# Generation Settings
DEFAULT_MARKET=us_stocks
OUTPUT_FORMAT=json
VALIDATE_SPECS=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=reports/generator.log

# Development
DEBUG=false
TEST_MODE=false
"""
            env_example.write_text(env_content, encoding='utf-8')
            self.optimizations.append("Создан .env.example")
        
        # setup.cfg для инструментов
        setup_cfg = self.project_root / 'setup.cfg'
        if not setup_cfg.exists():
            setup_content = """[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .venv,.venv_new,__pycache__,.git,.mypy_cache,.pytest_cache

[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True

[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
"""
            setup_cfg.write_text(setup_content, encoding='utf-8')
            self.optimizations.append("Создан setup.cfg")
    
    def generate_structure_report(self) -> str:
        """Генерирует отчет об оптимизации структуры"""
        logger.info("📊 Генерация отчета об оптимизации...")
        
        report = []
        report.append("# PROJECT_STRUCTURE_OPTIMIZATION_REPORT.md")
        report.append("")
        report.append(f"## Отчет об оптимизации структуры проекта")
        report.append(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Проект:** {self.project_root.name}")
        report.append("")
        
        report.append("## 🏗️ Выполненные оптимизации")
        report.append("")
        
        for optimization in self.optimizations:
            report.append(f"- ✅ {optimization}")
        report.append("")
        
        report.append("## 📁 Новая структура проекта")
        report.append("")
        report.append("```")
        report.append("tv-generator/")
        report.append("├── src/")
        report.append("│   └── tv_generator/          # Основной пакет")
        report.append("│       ├── __init__.py")
        report.append("│       ├── api.py")
        report.append("│       ├── cli.py")
        report.append("│       ├── config.py")
        report.append("│       ├── core.py")
        report.append("│       └── simple_cli.py")
        report.append("├── scripts/")
        report.append("│   ├── maintenance/           # Скрипты обслуживания")
        report.append("│   │   ├── cleanup.py")
        report.append("│   │   ├── optimize_structure.py")
        report.append("│   │   └── generate_specs.py")
        report.append("│   └── utils/                 # Утилиты")
        report.append("│       ├── validation_and_ci.py")
        report.append("│       └── openapi_updater.py")
        report.append("├── tests/                     # Тесты")
        report.append("├── docs/")
        report.append("│   ├── api/                   # Документация API")
        report.append("│   ├── user_guide/            # Руководство пользователя")
        report.append("│   ├── specs/                 # OpenAPI спецификации")
        report.append("│   └── README.md")
        report.append("├── data/")
        report.append("│   ├── raw/                   # Сырые данные")
        report.append("│   └── processed/             # Обработанные данные")
        report.append("├── reports/                   # Отчеты и логи")
        report.append("├── backups/                   # Резервные копии")
        report.append("├── main.py                    # Главная точка входа")
        report.append("├── pyproject.toml")
        report.append("├── requirements.txt")
        report.append("├── requirements-dev.txt")
        report.append("├── README.md")
        report.append("└── .env.example")
        report.append("```")
        report.append("")
        
        report.append("## 🚀 Точки входа")
        report.append("")
        report.append("### Основные команды:")
        report.append("- `python main.py` - Главный CLI")
        report.append("- `python scripts/maintenance/generate_specs.py` - Генерация спецификаций")
        report.append("- `python scripts/maintenance/cleanup.py` - Очистка проекта")
        report.append("")
        
        report.append("### Установка и разработка:")
        report.append("- `pip install -e .` - Установка в режиме разработки")
        report.append("- `pytest` - Запуск тестов")
        report.append("- `black .` - Форматирование кода")
        report.append("- `flake8` - Проверка стиля")
        report.append("")
        
        report.append("## 📋 Следующие шаги")
        report.append("")
        report.append("1. **Обновить импорты** в коде для новой структуры")
        report.append("2. **Обновить тесты** для работы с новой структурой")
        report.append("3. **Обновить документацию** с новыми путями")
        report.append("4. **Протестировать** все точки входа")
        report.append("5. **Обновить CI/CD** конфигурацию")
        report.append("")
        
        return "\n".join(report)
    
    def run_optimization(self) -> str:
        """Запускает полную оптимизацию структуры"""
        logger.info("🚀 Запуск оптимизации структуры проекта...")
        
        # Создание стандартной структуры
        self.create_standard_structure()
        
        # Перемещение основного пакета
        self.move_main_package_to_src()
        
        # Консолидация скриптов
        self.consolidate_scripts()
        
        # Организация документации
        self.organize_documentation()
        
        # Организация данных и результатов
        self.organize_data_and_results()
        
        # Создание точек входа
        self.create_entry_points()
        
        # Обновление конфигурации
        self.update_pyproject_toml()
        
        # Создание стандартных конфигураций
        self.create_standard_configs()
        
        # Генерация отчета
        report = self.generate_structure_report()
        
        logger.info(f"✅ Оптимизация завершена: {len(self.optimizations)} изменений")
        
        return report

def main():
    """Основная функция"""
    project_root = Path.cwd()
    
    print("🔧 ОПТИМИЗАЦИЯ СТРУКТУРЫ ПРОЕКТА")
    print("=" * 50)
    print()
    
    optimizer = ProjectStructureOptimizer(project_root)
    report = optimizer.run_optimization()
    
    # Сохраняем отчет
    report_path = project_root / "PROJECT_STRUCTURE_OPTIMIZATION_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Оптимизация завершена!")
    print(f"📄 Отчет сохранен: {report_path}")
    print()
    print(report)

if __name__ == "__main__":
    main() 