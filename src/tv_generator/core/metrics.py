"""
Metrics collection system for OpenAPI generator.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import psutil
from loguru import logger


@dataclass
class GenerationMetrics:
    """Metrics for generation process."""

    market: str
    fields_processed: int
    duration: float
    memory_usage: float
    api_calls: int
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MetricsCollector:
    """Collector for generation metrics."""

    def __init__(self):
        self.metrics: list[GenerationMetrics] = []
        self.start_time: float | None = None
        self.process = psutil.Process()

    def start_generation(self) -> None:
        """Start timing generation process."""
        self.start_time = time.time()

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def record_generation(self, metrics: GenerationMetrics) -> None:
        """Record generation metrics."""
        self.metrics.append(metrics)
        logger.info(
            "generation_completed",
            market=metrics.market,
            fields_processed=metrics.fields_processed,
            duration=metrics.duration,
            memory_usage=metrics.memory_usage,
            api_calls=metrics.api_calls,
            success=metrics.success,
        )

    def get_summary(self) -> dict[str, any]:
        """Get summary of all metrics."""
        if not self.metrics:
            return {}

        successful = [m for m in self.metrics if m.success]
        failed = [m for m in self.metrics if not m.success]

        total_duration = sum(m.duration for m in self.metrics)
        avg_memory = sum(m.memory_usage for m in self.metrics) / len(self.metrics)

        return {
            "total_generations": len(self.metrics),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.metrics) if self.metrics else 0,
            "total_duration": total_duration,
            "avg_duration": total_duration / len(self.metrics) if self.metrics else 0,
            "avg_memory_usage": avg_memory,
            "max_memory_usage": max(m.memory_usage for m in self.metrics) if self.metrics else 0,
            "total_api_calls": sum(m.api_calls for m in self.metrics),
            "total_fields_processed": sum(m.fields_processed for m in self.metrics),
        }

    def get_market_metrics(self, market: str) -> GenerationMetrics | None:
        """Get metrics for specific market."""
        for metric in reversed(self.metrics):
            if metric.market == market:
                return metric
        return None

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.start_time = None

    def export_metrics(self, file_path: str) -> None:
        """Export metrics to JSON file."""
        import json

        summary = self.get_summary()
        metrics_data = {
            "summary": summary,
            "detailed_metrics": [
                {
                    "market": m.market,
                    "fields_processed": m.fields_processed,
                    "duration": m.duration,
                    "memory_usage": m.memory_usage,
                    "api_calls": m.api_calls,
                    "success": m.success,
                    "timestamp": m.timestamp.isoformat(),
                    "errors": m.errors,
                    "warnings": m.warnings,
                }
                for m in self.metrics
            ],
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Metrics exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")


class PerformanceMonitor:
    """Performance monitoring utilities."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time: float | None = None
        self.start_memory: float | None = None

    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = self.get_memory_usage()

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def get_duration(self) -> float:
        """Get elapsed time since start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_memory_increase(self) -> float:
        """Get memory increase since start."""
        if self.start_memory is None:
            return 0.0
        return self.get_memory_usage() - self.start_memory

    def get_performance_summary(self) -> dict[str, any]:
        """Get performance summary."""
        return {
            "duration": self.get_duration(),
            "current_memory": self.get_memory_usage(),
            "memory_increase": self.get_memory_increase(),
            "cpu_percent": self.process.cpu_percent(),
        }
