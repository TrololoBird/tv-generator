#!/usr/bin/env python3
"""
Validation and CI/CD System for OpenAPI Specifications
Упрощенная версия для финального прогона
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OpenAPIValidator:
    """Система валидации OpenAPI спецификаций"""

    def __init__(self):
        self.specs_dir = Path("docs/specs")
        self.results_dir = Path("results")
        self.validation_results = {}

    def validate_specification(self, spec_path: Path) -> dict[str, Any]:
        """Валидирует отдельную спецификацию"""
        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = json.load(f)

            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "file": str(spec_path),
                "timestamp": datetime.now().isoformat(),
            }

            # Базовая валидация
            required_fields = ["openapi", "info", "paths"]
            for field in required_fields:
                if field not in spec:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required field: {field}")

            # Проверка версии OpenAPI
            if spec.get("openapi") != "3.1.0":
                validation_result["warnings"].append("OpenAPI version should be 3.1.0")

            # Проверка наличия путей
            if not spec.get("paths"):
                validation_result["warnings"].append("No paths defined")

            # Проверка undocumented параметров
            self._check_undocumented_parameters(spec, validation_result)

            return validation_result

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to parse: {e}"],
                "warnings": [],
                "file": str(spec_path),
                "timestamp": datetime.now().isoformat(),
            }

    def _check_undocumented_parameters(self, spec: dict[str, Any], result: dict[str, Any]):
        """Проверяет undocumented параметры"""
        undocumented_found = False

        # Проверяем в путях
        for path, path_item in spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() == "post" and "requestBody" in operation:
                    schema = operation["requestBody"].get("content", {}).get("application/json", {}).get("schema", {})
                    if self._has_undocumented_params(schema):
                        undocumented_found = True
                        result["warnings"].append(f"Undocumented parameters found in {path}")

        # Проверяем в компонентах
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            if schema.get("x-undocumented") or schema.get("x-experimental"):
                undocumented_found = True
                result["warnings"].append(f"Undocumented schema found: {schema_name}")

        if undocumented_found:
            result["warnings"].append("Undocumented parameters detected - use with caution")

    def _has_undocumented_params(self, schema: dict[str, Any]) -> bool:
        """Проверяет наличие undocumented параметров в схеме"""
        if schema.get("x-undocumented") or schema.get("x-experimental"):
            return True

        for prop_name, prop_schema in schema.get("properties", {}).items():
            if prop_schema.get("x-undocumented") or prop_schema.get("x-experimental"):
                return True
            if isinstance(prop_schema, dict) and self._has_undocumented_params(prop_schema):
                return True

        return False

    def validate_all_specifications(self) -> dict[str, Any]:
        """Валидирует все спецификации"""
        logger.info("Начинаю валидацию OpenAPI спецификаций")

        validation_results = {}

        # Валидируем все файлы спецификаций
        for spec_file in self.specs_dir.glob("*_openapi.json"):
            logger.info(f"🔍 Валидирую: {spec_file.name}")
            result = self.validate_specification(spec_file)
            validation_results[spec_file.name] = result

            if result["valid"]:
                logger.info(f"✅ {spec_file.name} - валидна")
            else:
                logger.warning(f"⚠️ {spec_file.name} - ошибки валидации")

        # Сохраняем результаты
        validation_report_path = self.results_dir / "validation_report.json"
        with open(validation_report_path, "w", encoding="utf-8") as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 Отчет валидации сохранен: {validation_report_path}")

        # Подсчитываем статистику
        total_specs = len(validation_results)
        valid_specs = sum(1 for result in validation_results.values() if result["valid"])
        total_errors = sum(len(result["errors"]) for result in validation_results.values())
        total_warnings = sum(len(result["warnings"]) for result in validation_results.values())

        logger.info(f"📊 Статистика валидации:")
        logger.info(f"   Всего спецификаций: {total_specs}")
        logger.info(f"   Валидных: {valid_specs}")
        logger.info(f"   Ошибок: {total_errors}")
        logger.info(f"   Предупреждений: {total_warnings}")

        return validation_results


class CICDPipeline:
    """CI/CD пайплайн для автоматизации"""

    def __init__(self):
        self.repo_path = Path(".")
        self.specs_dir = Path("specs")
        self.results_dir = Path("results")

    def run_tests(self) -> bool:
        """Запускает тесты"""
        logger.info("🧪 Запуск тестов...")

        try:
            # Запускаем pytest
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
            )

            if result.returncode == 0:
                logger.info("Тесты прошли успешно")
                return True
            else:
                logger.error(f"❌ Тесты не прошли: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске тестов: {e}")
            return False

    def validate_specifications(self) -> bool:
        """Валидирует спецификации"""
        logger.info("🔍 Валидация спецификаций...")

        try:
            validator = OpenAPIValidator()
            results = validator.validate_all_specifications()

            # Проверяем, что все спецификации валидны
            all_valid = all(result["valid"] for result in results.values())

            if all_valid:
                logger.info("Все спецификации валидны")
                return True
            else:
                logger.error("❌ Некоторые спецификации невалидны")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка при валидации: {e}")
            return False


def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Validation and CI/CD for OpenAPI specs")
    parser.add_argument("--validate", action="store_true", help="Validate specifications")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--cicd", action="store_true", help="Run CI/CD pipeline")

    args = parser.parse_args()

    if args.validate:
        validator = OpenAPIValidator()
        validator.validate_all_specifications()

    elif args.test:
        cicd = CICDPipeline()
        cicd.run_tests()

    elif args.cicd:
        cicd = CICDPipeline()
        cicd.validate_specifications()
        cicd.run_tests()

    else:
        # По умолчанию запускаем валидацию
        validator = OpenAPIValidator()
        validator.validate_all_specifications()


if __name__ == "__main__":
    main()
