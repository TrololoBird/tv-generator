#!/usr/bin/env python3
"""
Tests for Enhanced OpenAPI Generator
"""

import json
import pytest
from pathlib import Path
from enhanced_generator import EnhancedOpenAPIGenerator

class TestEnhancedGenerator:
    """Тесты для Enhanced OpenAPI Generator"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.generator = EnhancedOpenAPIGenerator()
        self.specs_dir = Path("specs")
        self.results_dir = Path("results")
    
    def test_generator_initialization(self):
        """Тест инициализации генератора"""
        assert self.generator.markets == ["america", "crypto", "forex", "futures", "cfd", "bond", "coin"]
        assert len(self.generator.undocumented_params) > 0
        assert "filter2" in self.generator.undocumented_params
        assert "sort.sortBy" in self.generator.undocumented_params
    
    def test_market_specification_generation(self):
        """Тест генерации спецификации для рынка"""
        spec = self.generator.generate_market_specification("crypto")
        
        # Проверяем базовую структуру
        assert spec["openapi"] == "3.1.0"
        assert "info" in spec
        assert "paths" in spec
        assert "components" in spec
        
        # Проверяем пути
        assert "/crypto/scan" in spec["paths"]
        assert "/crypto/metainfo" in spec["paths"]
        
        # Проверяем схемы
        schemas = spec["components"]["schemas"]
        assert "CryptoScanRequest" in schemas
        assert "CryptoScanResponse" in schemas
        assert "CryptoMetainfo" in schemas
    
    def test_undocumented_parameters_in_schema(self):
        """Тест наличия undocumented параметров в схеме"""
        spec = self.generator.generate_market_specification("crypto")
        request_schema = spec["components"]["schemas"]["CryptoScanRequest"]
        
        # Проверяем наличие undocumented параметров
        undocumented_found = False
        for prop_name, prop_schema in request_schema["properties"].items():
            if prop_schema.get("x-experimental") or prop_schema.get("x-undocumented"):
                undocumented_found = True
                break
        
        assert undocumented_found, "Undocumented parameters not found in schema"
    
    def test_experimental_params_present(self):
        """Тест наличия экспериментальных параметров"""
        spec = self.generator.generate_market_specification("forex")
        request_schema = spec["components"]["schemas"]["ForexScanRequest"]
        
        # Проверяем конкретные undocumented параметры
        experimental_params = [
            "filter2", "sort.sortBy", "sort.sortOrder", 
            "options.decimal_places", "options.currency"
        ]
        
        for param in experimental_params:
            if param in request_schema["properties"]:
                prop = request_schema["properties"][param]
                assert prop.get("x-experimental") or prop.get("x-undocumented"), \
                    f"Parameter {param} should be marked as experimental"
    
    def test_gap_coverage(self):
        """Тест покрытия gap-анализа"""
        # Проверяем, что все undocumented параметры из gap-анализа включены
        gap_params = [
            "filter2", "symbols.query.types", "sort.sortBy", "sort.sortOrder",
            "options.decimal_places", "options.currency", "options.timezone",
            "options.session", "symbols.query.exchanges", "symbols.tickers",
            "filter.operation", "filter.left", "filter.right", "filter.settings"
        ]
        
        for param in gap_params:
            assert param in self.generator.undocumented_params, \
                f"Gap parameter {param} not included in generator"
    
    def test_all_markets_generation(self):
        """Тест генерации всех рынков"""
        specs = self.generator.generate_all_specifications()
        
        # Проверяем, что все рынки сгенерированы
        assert len(specs) == len(self.generator.markets)
        
        for market in self.generator.markets:
            assert market in specs, f"Market {market} not generated"
            
            # Проверяем, что файл создан
            spec_file = self.specs_dir / f"{market}_openapi.json"
            assert spec_file.exists(), f"Spec file for {market} not created"
    
    def test_specification_validity(self):
        """Тест валидности сгенерированных спецификаций"""
        specs = self.generator.generate_all_specifications()
        
        for market, spec in specs.items():
            # Проверяем обязательные поля
            assert "openapi" in spec
            assert "info" in spec
            assert "paths" in spec
            assert "components" in spec
            
            # Проверяем версию OpenAPI
            assert spec["openapi"] == "3.1.0"
            
            # Проверяем информацию
            info = spec["info"]
            assert "title" in info
            assert "version" in info
            assert market.upper() in info["title"]
    
    def test_report_generation(self):
        """Тест генерации отчета"""
        self.generator.generate_all_specifications()
        
        # Проверяем, что отчет создан
        report_file = self.results_dir / "generation_report.json"
        assert report_file.exists(), "Generation report not created"
        
        # Проверяем содержимое отчета
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        assert "timestamp" in report
        assert "generator_version" in report
        assert "total_markets" in report
        assert "undocumented_parameters" in report
        assert report["generator_version"] == "2.0.0"
        assert report["openapi_version"] == "3.1.0"

def test_generator_integration():
    """Интеграционный тест генератора"""
    generator = EnhancedOpenAPIGenerator()
    
    # Генерируем все спецификации
    specs = generator.generate_all_specifications()
    
    # Проверяем результаты
    assert len(specs) == 7  # 7 рынков
    assert all(market in specs for market in generator.markets)
    
    # Проверяем файлы
    for market in generator.markets:
        spec_file = Path("specs") / f"{market}_openapi.json"
        assert spec_file.exists()
        
        # Проверяем, что файл содержит валидный JSON
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
        
        assert spec_data["openapi"] == "3.1.0"
        assert market.upper() in spec_data["info"]["title"]
