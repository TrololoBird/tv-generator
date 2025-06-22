#!/usr/bin/env python3
"""
Project Cleanup and Optimization Script
Аудит, чистка и оптимизация структуры проекта
"""

import os
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectCleanup:
    """Класс для аудита и очистки проекта"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.removed_files = []
        self.removed_dirs = []
        self.archived_files = []
        self.optimized_files = []
        self.duplicates_found = []
        self.unused_files = []
        
    def scan_project_structure(self) -> Dict:
        """Сканирует структуру проекта"""
        logger.info("🔍 Сканирование структуры проекта...")
        
        structure = {
            'files': [],
            'dirs': [],
            'file_sizes': {},
            'duplicates': [],
            'cache_dirs': [],
            'temp_files': [],
            'large_files': [],
            'empty_files': []
        }
        
        for root, dirs, files in os.walk(self.project_root):
            # Пропускаем виртуальные окружения
            if '.venv' in root or '.venv_new' in root:
                continue
                
            rel_root = Path(root).relative_to(self.project_root)
            
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                structure['dirs'].append(str(rel_root / dir_name))
                
                # Поиск кэш-директорий
                if dir_name in ['__pycache__', '.pytest_cache', '.mypy_cache', '.coverage']:
                    structure['cache_dirs'].append(str(dir_path))
            
            for file_name in files:
                file_path = Path(root) / file_name
                rel_file_path = rel_root / file_name
                structure['files'].append(str(rel_file_path))
                
                # Размер файла
                try:
                    file_size = file_path.stat().st_size
                    structure['file_sizes'][str(rel_file_path)] = file_size
                    
                    if file_size == 0:
                        structure['empty_files'].append(str(rel_file_path))
                    elif file_size > 10 * 1024 * 1024:  # > 10MB
                        structure['large_files'].append(str(rel_file_path))
                        
                except OSError:
                    continue
                
                # Поиск временных файлов
                if any(ext in file_name.lower() for ext in ['.tmp', '.bak', '.old', '.log', '.out']):
                    structure['temp_files'].append(str(rel_file_path))
        
        return structure
    
    def find_duplicates(self, structure: Dict) -> List[Tuple[str, str]]:
        """Находит дубликаты файлов"""
        logger.info("🔍 Поиск дубликатов файлов...")
        
        duplicates = []
        file_groups = {}
        
        for file_path, size in structure['file_sizes'].items():
            if size == 0:
                continue
                
            file_name = Path(file_path).name
            if file_name not in file_groups:
                file_groups[file_name] = []
            file_groups[file_name].append(file_path)
        
        for file_name, file_paths in file_groups.items():
            if len(file_paths) > 1:
                # Проверяем содержимое файлов
                for i, path1 in enumerate(file_paths):
                    for path2 in file_paths[i+1:]:
                        if self._files_are_identical(path1, path2):
                            duplicates.append((path1, path2))
        
        return duplicates
    
    def _files_are_identical(self, path1: str, path2: str) -> bool:
        """Проверяет идентичность файлов"""
        try:
            file1 = self.project_root / path1
            file2 = self.project_root / path2
            
            if file1.stat().st_size != file2.stat().st_size:
                return False
            
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                return f1.read() == f2.read()
        except OSError:
            return False
    
    def find_unused_files(self, structure: Dict) -> List[str]:
        """Находит неиспользуемые файлы"""
        logger.info("🔍 Поиск неиспользуемых файлов...")
        
        unused = []
        main_package = 'tv_generator'
        
        # Файлы, которые точно используются
        used_files = {
            'pyproject.toml', 'requirements.txt', 'requirements-dev.txt',
            'README.md', 'LICENSE', '.gitignore', 'pytest.ini',
            'conftest.py', 'Dockerfile', 'CHANGELOG.md', 'AGENTS.md',
            'TODO.md', 'field_type_mapping.json', '.flake8',
            '.pre-commit-config.yaml'
        }
        
        # Основные скрипты
        main_scripts = {
            'enhanced_generator.py', 'generate_openapi.py', 'openapi_updater.py',
            'validation_and_ci.py', 'run_enhanced_generator.py'
        }
        
        for file_path in structure['files']:
            file_name = Path(file_path).name
            
            # Пропускаем файлы в основных директориях
            if any(part in file_path for part in [main_package, 'tests/', 'scripts/', 'docs/']):
                continue
                
            # Пропускаем используемые файлы
            if file_name in used_files or file_name in main_scripts:
                continue
                
            # Пропускаем спецификации и результаты
            if 'specs/' in file_path or 'results/' in file_path:
                continue
                
            # Пропускаем логи
            if 'logs/' in file_path:
                continue
                
            # Проверяем, является ли файл демо или временным
            if any(keyword in file_name.lower() for keyword in ['demo', 'test', 'example', 'temp', 'tmp']):
                unused.append(file_path)
        
        return unused
    
    def analyze_documentation(self, structure: Dict) -> Dict:
        """Анализирует документацию проекта"""
        logger.info("📚 Анализ документации...")
        
        docs = {
            'readme_files': [],
            'markdown_files': [],
            'rst_files': [],
            'empty_docs': [],
            'duplicate_docs': []
        }
        
        for file_path in structure['files']:
            if file_path.endswith('.md'):
                docs['markdown_files'].append(file_path)
                if Path(file_path).name.lower() == 'readme.md':
                    docs['readme_files'].append(file_path)
            elif file_path.endswith('.rst'):
                docs['rst_files'].append(file_path)
        
        # Проверяем пустые документы
        for doc_file in docs['markdown_files'] + docs['rst_files']:
            try:
                file_path = self.project_root / doc_file
                if file_path.stat().st_size < 100:  # < 100 байт
                    docs['empty_docs'].append(doc_file)
            except OSError:
                continue
        
        return docs
    
    def cleanup_cache_directories(self, structure: Dict) -> int:
        """Очищает кэш-директории"""
        logger.info("🧹 Очистка кэш-директорий...")
        
        removed_count = 0
        
        for cache_dir in structure['cache_dirs']:
            try:
                cache_path = Path(cache_dir)
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                    self.removed_dirs.append(str(cache_path))
                    removed_count += 1
                    logger.info(f"Удалена кэш-директория: {cache_path}")
            except OSError as e:
                logger.warning(f"Не удалось удалить {cache_dir}: {e}")
        
        return removed_count
    
    def cleanup_temp_files(self, structure: Dict) -> int:
        """Очищает временные файлы"""
        logger.info("🧹 Очистка временных файлов...")
        
        removed_count = 0
        
        for temp_file in structure['temp_files']:
            try:
                file_path = self.project_root / temp_file
                if file_path.exists():
                    file_path.unlink()
                    self.removed_files.append(str(file_path))
                    removed_count += 1
                    logger.info(f"Удален временный файл: {file_path}")
            except OSError as e:
                logger.warning(f"Не удалось удалить {temp_file}: {e}")
        
        return removed_count
    
    def cleanup_empty_files(self, structure: Dict) -> int:
        """Очищает пустые файлы"""
        logger.info("🧹 Очистка пустых файлов...")
        
        removed_count = 0
        
        for empty_file in structure['empty_files']:
            # Пропускаем важные пустые файлы
            if any(skip in empty_file for skip in ['__init__.py', '.gitkeep']):
                continue
                
            try:
                file_path = self.project_root / empty_file
                if file_path.exists():
                    file_path.unlink()
                    self.removed_files.append(str(file_path))
                    removed_count += 1
                    logger.info(f"Удален пустой файл: {file_path}")
            except OSError as e:
                logger.warning(f"Не удалось удалить {empty_file}: {e}")
        
        return removed_count
    
    def archive_old_files(self, structure: Dict) -> int:
        """Архивирует старые файлы"""
        logger.info("📦 Архивирование старых файлов...")
        
        archived_count = 0
        archive_dir = self.project_root / 'legacy'
        archive_dir.mkdir(exist_ok=True)
        
        # Файлы для архивирования
        files_to_archive = [
            'demo_enhanced_generator.py',
            'demo_enhanced_system.py',
            'ENHANCED_GENERATOR_IMPLEMENTATION.md',
            'ENHANCED_IMPLEMENTATION_COMPLETE.md',
            'FINAL_REPORT.md',
            'README_ENHANCED.md',
            'requirements-enhanced.txt'
        ]
        
        for file_name in files_to_archive:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    # Перемещаем в архив
                    archive_path = archive_dir / file_name
                    shutil.move(str(file_path), str(archive_path))
                    self.archived_files.append(str(file_path))
                    archived_count += 1
                    logger.info(f"Архивирован файл: {file_path}")
                except OSError as e:
                    logger.warning(f"Не удалось архивировать {file_name}: {e}")
        
        return archived_count
    
    def optimize_project_structure(self) -> Dict:
        """Оптимизирует структуру проекта"""
        logger.info("🔧 Оптимизация структуры проекта...")
        
        optimizations = {
            'moved_files': [],
            'created_dirs': [],
            'consolidated_files': []
        }
        
        # Создаем директорию для утилит
        utils_dir = self.project_root / 'scripts' / 'utils'
        utils_dir.mkdir(exist_ok=True)
        optimizations['created_dirs'].append(str(utils_dir))
        
        # Перемещаем вспомогательные скрипты
        utility_scripts = [
            'validation_and_ci.py',
            'openapi_updater.py'
        ]
        
        for script in utility_scripts:
            script_path = self.project_root / script
            if script_path.exists():
                try:
                    new_path = utils_dir / script
                    shutil.move(str(script_path), str(new_path))
                    optimizations['moved_files'].append((str(script_path), str(new_path)))
                    logger.info(f"Перемещен скрипт: {script_path} -> {new_path}")
                except OSError as e:
                    logger.warning(f"Не удалось переместить {script}: {e}")
        
        return optimizations
    
    def generate_cleanup_report(self, structure: Dict, duplicates: List, unused: List, docs: Dict) -> str:
        """Генерирует отчет о чистке"""
        logger.info("📊 Генерация отчета о чистке...")
        
        report = []
        report.append("# PROJECT_CLEANUP_REPORT.md")
        report.append("")
        report.append(f"## Отчет о аудите и очистке проекта")
        report.append(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Проект:** {self.project_root.name}")
        report.append("")
        
        # Статистика
        report.append("## 📊 Статистика проекта")
        report.append(f"- **Всего файлов:** {len(structure['files'])}")
        report.append(f"- **Всего директорий:** {len(structure['dirs'])}")
        report.append(f"- **Кэш-директорий:** {len(structure['cache_dirs'])}")
        report.append(f"- **Временных файлов:** {len(structure['temp_files'])}")
        report.append(f"- **Пустых файлов:** {len(structure['empty_files'])}")
        report.append(f"- **Больших файлов (>10MB):** {len(structure['large_files'])}")
        report.append("")
        
        # Дубликаты
        if duplicates:
            report.append("## 🔄 Найденные дубликаты")
            for dup1, dup2 in duplicates:
                report.append(f"- `{dup1}` = `{dup2}`")
            report.append("")
        
        # Неиспользуемые файлы
        if unused:
            report.append("## 🗑️ Неиспользуемые файлы")
            for file_path in unused:
                report.append(f"- `{file_path}`")
            report.append("")
        
        # Документация
        report.append("## 📚 Анализ документации")
        report.append(f"- **README файлов:** {len(docs['readme_files'])}")
        report.append(f"- **Markdown файлов:** {len(docs['markdown_files'])}")
        report.append(f"- **RST файлов:** {len(docs['rst_files'])}")
        report.append(f"- **Пустых документов:** {len(docs['empty_docs'])}")
        report.append("")
        
        # Результаты очистки
        report.append("## 🧹 Результаты очистки")
        report.append(f"- **Удалено файлов:** {len(self.removed_files)}")
        report.append(f"- **Удалено директорий:** {len(self.removed_dirs)}")
        report.append(f"- **Архивировано файлов:** {len(self.archived_files)}")
        report.append("")
        
        if self.removed_files:
            report.append("### Удаленные файлы:")
            for file_path in self.removed_files:
                report.append(f"- `{file_path}`")
            report.append("")
        
        if self.removed_dirs:
            report.append("### Удаленные директории:")
            for dir_path in self.removed_dirs:
                report.append(f"- `{dir_path}`")
            report.append("")
        
        if self.archived_files:
            report.append("### Архивированные файлы:")
            for file_path in self.archived_files:
                report.append(f"- `{file_path}`")
            report.append("")
        
        # Рекомендации
        report.append("## 💡 Рекомендации по оптимизации")
        report.append("")
        report.append("### Структура директорий:")
        report.append("- ✅ `src/tv_generator/` - основной пакет")
        report.append("- ✅ `tests/` - тесты")
        report.append("- ✅ `scripts/` - вспомогательные скрипты")
        report.append("- ✅ `docs/` - документация")
        report.append("- ✅ `specs/` - спецификации")
        report.append("- ✅ `results/` - результаты")
        report.append("- ✅ `logs/` - логи")
        report.append("")
        
        report.append("### Файлы конфигурации:")
        report.append("- ✅ `pyproject.toml` - основная конфигурация")
        report.append("- ✅ `requirements.txt` - зависимости")
        report.append("- ✅ `requirements-dev.txt` - dev зависимости")
        report.append("- ✅ `.gitignore` - игнорируемые файлы")
        report.append("- ✅ `README.md` - основная документация")
        report.append("")
        
        report.append("### Основные скрипты:")
        report.append("- ✅ `enhanced_generator.py` - основной генератор")
        report.append("- ✅ `generate_openapi.py` - базовый генератор")
        report.append("- ✅ `run_enhanced_generator.py` - скрипт запуска")
        report.append("")
        
        return "\n".join(report)
    
    def run_cleanup(self) -> str:
        """Запускает полную очистку проекта"""
        logger.info("🚀 Запуск аудита и очистки проекта...")
        
        # Сканирование структуры
        structure = self.scan_project_structure()
        
        # Поиск дубликатов
        duplicates = self.find_duplicates(structure)
        
        # Поиск неиспользуемых файлов
        unused = self.find_unused_files(structure)
        
        # Анализ документации
        docs = self.analyze_documentation(structure)
        
        # Очистка кэш-директорий
        cache_removed = self.cleanup_cache_directories(structure)
        
        # Очистка временных файлов
        temp_removed = self.cleanup_temp_files(structure)
        
        # Очистка пустых файлов
        empty_removed = self.cleanup_empty_files(structure)
        
        # Архивирование старых файлов
        archived = self.archive_old_files(structure)
        
        # Оптимизация структуры
        optimizations = self.optimize_project_structure()
        
        # Генерация отчета
        report = self.generate_cleanup_report(structure, duplicates, unused, docs)
        
        logger.info(f"✅ Очистка завершена:")
        logger.info(f"   - Удалено кэш-директорий: {cache_removed}")
        logger.info(f"   - Удалено временных файлов: {temp_removed}")
        logger.info(f"   - Удалено пустых файлов: {empty_removed}")
        logger.info(f"   - Архивировано файлов: {archived}")
        
        return report

def main():
    """Основная функция"""
    project_root = Path.cwd()
    
    print("🧹 АУДИТ, ЧИСТКА И ОПТИМИЗАЦИЯ СТРУКТУРЫ ПРОЕКТА")
    print("=" * 60)
    print()
    
    cleanup = ProjectCleanup(project_root)
    report = cleanup.run_cleanup()
    
    # Сохраняем отчет
    report_path = project_root / "PROJECT_CLEANUP_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Очистка завершена!")
    print(f"📄 Отчет сохранен: {report_path}")
    print()
    print(report)

if __name__ == "__main__":
    main() 