"""
Parallel pipeline for concurrent OpenAPI generation.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from loguru import logger

from ..types import OpenAPIGeneratorResult
from .metrics import GenerationMetrics, MetricsCollector
from ..main import OpenAPIPipeline


class ParallelOpenAPIPipeline(OpenAPIPipeline):
    """Parallel pipeline for generating OpenAPI specifications."""

    def __init__(self, max_concurrent: int = 4, chunk_size: int = 10, **kwargs):
        """Initialize the parallel pipeline."""
        super().__init__(**kwargs)
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _generate_spec_with_semaphore(self, market: str) -> tuple[str, bool, str | None]:
        """Generate spec with semaphore to limit concurrency."""
        async with self.semaphore:
            try:
                success = await self.generate_and_save_spec(market)
                return market, success, None
            except Exception as e:
                error_msg = f"Error generating spec for {market}: {e}"
                logger.error(error_msg)
                return market, False, error_msg

    async def _process_chunk(self, markets_chunk: list[str]) -> list[tuple[str, bool, str | None]]:
        """Process a chunk of markets concurrently."""
        tasks = [self._generate_spec_with_semaphore(market) for market in markets_chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                market = markets_chunk[i]
                error_msg = f"Exception for {market}: {result}"
                logger.error(error_msg)
                processed_results.append((market, False, error_msg))
            else:
                processed_results.append(result)

        return processed_results

    async def generate_all_specs_parallel(self) -> OpenAPIGeneratorResult:
        """Generate OpenAPI specifications for all markets in parallel."""
        self.metrics_collector.start_generation()

        try:
            markets = await self.load_markets()
            if not markets:
                logger.warning("No markets found")
                return OpenAPIGeneratorResult(
                    success=False,
                    message="No markets found",
                    generated_specs=0,
                    total_markets=0,
                    errors=["No markets found"],
                )

            logger.info(
                f"Starting parallel generation for {len(markets)} markets with {self.max_concurrent} concurrent workers"
            )

            # Split markets into chunks
            chunks = [markets[i : i + self.chunk_size] for i in range(0, len(markets), self.chunk_size)]
            logger.info(f"Split into {len(chunks)} chunks of size {self.chunk_size}")

            # Process chunks sequentially, but markets within chunks concurrently
            all_results = []
            successful_generations = 0
            failed_generations = 0
            errors = []

            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i + 1}/{len(chunks)} with {len(chunk)} markets")
                chunk_results = await self._process_chunk(chunk)
                all_results.extend(chunk_results)

                # Update counters
                for market, success, error in chunk_results:
                    if success:
                        successful_generations += 1
                    else:
                        failed_generations += 1
                        if error:
                            errors.append(error)

                logger.info(
                    f"Chunk {i + 1} completed: {len([r for r in chunk_results if r[1]])} successful, {len([r for r in chunk_results if not r[1]])} failed"
                )

            # Get metrics summary
            metrics_summary = self.metrics_collector.get_summary()

            result = OpenAPIGeneratorResult(
                success=failed_generations == 0,
                message=f"Generated {successful_generations} specs, {failed_generations} failed (parallel processing)",
                generated_specs=successful_generations,
                total_markets=len(markets),
                errors=errors if errors else None,
                metrics=metrics_summary,
            )

            logger.info(f"Parallel generation completed: {result.message}")
            return result

        except Exception as e:
            logger.error(f"Error in generate_all_specs_parallel: {e}")
            return OpenAPIGeneratorResult(
                success=False,
                message=f"Parallel generation failed: {e}",
                generated_specs=0,
                total_markets=0,
                errors=[str(e)],
            )

    async def generate_specs_with_progress(
        self, markets: list[str] | None = None, progress_callback: Optional[Callable] = None
    ) -> OpenAPIGeneratorResult:
        """Generate specs with progress reporting."""
        if markets is None:
            markets = await self.load_markets()

        if not markets:
            return OpenAPIGeneratorResult(
                success=False,
                message="No markets provided",
                generated_specs=0,
                total_markets=0,
                errors=["No markets provided"],
            )

        self.metrics_collector.start_generation()
        total_markets = len(markets)
        completed = 0
        successful = 0
        failed = 0
        errors = []

        # Create tasks for all markets
        tasks = [self._generate_spec_with_semaphore(market) for market in markets]

        # Process tasks as they complete
        for task in asyncio.as_completed(tasks):
            market, success, error = await task
            completed += 1

            if success:
                successful += 1
            else:
                failed += 1
                if error:
                    errors.append(error)

            # Report progress
            if progress_callback:
                progress = {
                    "completed": completed,
                    "total": total_markets,
                    "successful": successful,
                    "failed": failed,
                    "percentage": (completed / total_markets) * 100,
                    "current_market": market,
                }
                progress_callback(progress)

            logger.info(
                f"Progress: {completed}/{total_markets} ({progress['percentage']:.1f}%) - {market}: {'SUCCESS' if success else 'FAILED'}"
            )

        # Get metrics summary
        metrics_summary = self.metrics_collector.get_summary()

        result = OpenAPIGeneratorResult(
            success=failed == 0,
            message=f"Generated {successful} specs, {failed} failed (parallel with progress)",
            generated_specs=successful,
            total_markets=total_markets,
            errors=errors if errors else None,
            metrics=metrics_summary,
        )

        logger.info(f"Parallel generation with progress completed: {result.message}")
        return result

    async def generate_specs_with_retry(
        self, max_retries: int = 3, retry_delay: float = 1.0, markets: list[str] | None = None
    ) -> OpenAPIGeneratorResult:
        """Generate specs with retry logic for failed markets."""
        if markets is None:
            markets = await self.load_markets()

        if not markets:
            return OpenAPIGeneratorResult(
                success=False,
                message="No markets provided",
                generated_specs=0,
                total_markets=0,
                errors=["No markets provided"],
            )

        self.metrics_collector.start_generation()
        total_markets = len(markets)
        successful_generations = 0
        failed_generations = 0
        errors = []

        # Track failed markets for retry
        failed_markets = []

        # First attempt
        logger.info(f"Starting first attempt for {len(markets)} markets")
        for market in markets:
            try:
                success = await self.generate_and_save_spec(market)
                if success:
                    successful_generations += 1
                else:
                    failed_markets.append(market)
                    failed_generations += 1
                    errors.append(f"Failed to generate spec for {market}")
            except Exception as e:
                failed_markets.append(market)
                failed_generations += 1
                error_msg = f"Error generating spec for {market}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        # Retry failed markets
        for attempt in range(1, max_retries + 1):
            if not failed_markets:
                break

            logger.info(f"Retry attempt {attempt}/{max_retries} for {len(failed_markets)} failed markets")
            await asyncio.sleep(retry_delay)

            retry_markets = failed_markets.copy()
            failed_markets = []

            for market in retry_markets:
                try:
                    success = await self.generate_and_save_spec(market)
                    if success:
                        successful_generations += 1
                        failed_generations -= 1
                        # Remove from errors list
                        errors = [e for e in errors if not e.startswith(f"Error generating spec for {market}")]
                    else:
                        failed_markets.append(market)
                except Exception as e:
                    failed_markets.append(market)
                    error_msg = f"Retry {attempt} failed for {market}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        # Get metrics summary
        metrics_summary = self.metrics_collector.get_summary()

        result = OpenAPIGeneratorResult(
            success=failed_generations == 0,
            message=f"Generated {successful_generations} specs, {failed_generations} failed after {max_retries} retries",
            generated_specs=successful_generations,
            total_markets=total_markets,
            errors=errors if errors else None,
            metrics=metrics_summary,
        )

        logger.info(f"Parallel generation with retry completed: {result.message}")
        return result

    async def get_generation_stats(self) -> dict[str, Any]:
        """Get generation statistics."""
        try:
            markets = await self.load_markets()
            metrics_summary = self.metrics_collector.get_summary()

            return {
                "total_markets": len(markets),
                "max_concurrent": self.max_concurrent,
                "chunk_size": self.chunk_size,
                "metrics": metrics_summary,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting generation stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
