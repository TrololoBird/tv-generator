"""
TradingView OpenAPI Generator

Автоматизированный генератор OpenAPI 3.1.0 спецификаций для TradingView Scanner API.
"""

__version__ = "1.0.54"
__author__ = "TradingView OpenAPI Generator Team"

from .config import Settings
from .api import TradingViewAPI
from .core import Pipeline

__all__ = ["Settings", "TradingViewAPI", "Pipeline"] 