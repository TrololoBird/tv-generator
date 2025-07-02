"""
Конфигурация pytest для тестов в корне проекта.
"""

from pathlib import Path

import pytest


@pytest.fixture
def spec_paths():
    specs_dir = Path(__file__).parent / "specs"
    return list(specs_dir.glob("*.yaml")) + list(specs_dir.glob("*.json"))
