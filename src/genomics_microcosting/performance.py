# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Performance optimization tools for microcosting analysis."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable

import polars as pl

from .logging_config import get_logger

if TYPE_CHECKING:
    from .execution_contracts import ProfileMetrics, ProfilerDecorator

logger = get_logger(__name__)

try:
    import psutil
except ImportError:
    psutil = None


class PerformanceProfiler:
    """Profiles performance of operations and provides optimization suggestions."""

    def __init__(self) -> None:
        """Initialize the performance profiler."""
        self.metrics: dict[str, ProfileMetrics] = {}
        self.call_counts: dict[str, int] = {}

    def profile(self, operation_name: str) -> ProfilerDecorator:
        """Profile calls to a function."""

        def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.time()
                start_memory = self._get_memory_usage()

                try:
                    result = func(*args, **kwargs)
                except Exception:
                    self._record(
                        operation_name,
                        start_time,
                        start_memory,
                        success=False,
                    )
                    raise
                self._record(operation_name, start_time, start_memory, success=True)
                return result

            return wrapper

        return decorator

    def _record(
        self,
        operation: str,
        start_time: float,
        start_memory: float,
        *,
        success: bool,
    ) -> None:
        """Record one completed call, retaining the existing metric definitions."""
        execution_time = time.time() - start_time
        memory_used = self._get_memory_usage() - start_memory
        if operation not in self.metrics:
            self.metrics[operation] = {
                "call_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float("inf"),
                "total_memory": 0.0,
                "avg_memory": 0.0,
                "max_memory": 0.0,
                "errors": 0,
            }
        metrics = self.metrics[operation]
        metrics["call_count"] += 1
        metrics["total_time"] += execution_time
        metrics["avg_time"] = metrics["total_time"] / metrics["call_count"]
        metrics["max_time"] = max(metrics["max_time"], execution_time)
        metrics["min_time"] = min(metrics["min_time"], execution_time)
        metrics["total_memory"] += memory_used
        metrics["avg_memory"] = metrics["total_memory"] / metrics["call_count"]
        metrics["max_memory"] = max(metrics["max_memory"], memory_used)
        if not success:
            metrics["errors"] += 1
        logger.info(
            "Profiled %s: %ss, %sMB",
            operation,
            format(execution_time, ".4f"),
            format(memory_used, ".2f"),
        )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if psutil is None:
            return 0.0
        return psutil.Process().memory_info().rss / 1024 / 1024

    def get_report(self) -> dict[str, ProfileMetrics]:
        """Get performance report.

        Returns:
            Dict[str, Dict[str, Any]]: Performance metrics for all operations

        """
        return self.metrics

    def print_report(self) -> None:
        """Print formatted performance report."""
        if not self.metrics:
            logger.info("%s", "No performance data collected.")
            return

        logger.info("%s", "\nPerformance Report")
        logger.info("%s", "=" * 80)
        logger.info(
            "%s",
            (
                f"{'Operation':<30} {'Calls':<8} {'Avg Time':<12} "
                f"{'Max Time':<12} {'Avg Memory':<12} {'Errors':<8}"
            ),
        )
        logger.info("%s", "-" * 80)

        for operation, metrics in self.metrics.items():
            logger.info(
                "%s",
                f"{operation:<30} {metrics['call_count']:<8} "
                f"{metrics['avg_time']:<12.4f} "
                f"{metrics['max_time']:<12.4f} {metrics['avg_memory']:<12.2f} "
                f"{metrics['errors']:<8}",
            )


class DataOptimizer:
    """Optimizes data handling for better performance."""

    @staticmethod
    def optimize_dataframe(
        df: pl.DataFrame,
        *,
        numeric_columns: tuple[str, ...] = (),
    ) -> pl.DataFrame:
        """Optimize DataFrame memory usage.

        Args:
            df (pl.DataFrame): DataFrame to optimize
            numeric_columns: Columns explicitly selected for Float64 conversion

        Returns:
            pl.DataFrame: Optimized DataFrame

        """
        logger.info("Optimizing DataFrame with shape %s", df.shape)
        optimized_df = df.clone()
        for column in numeric_columns:
            optimized_df = optimized_df.with_columns(
                pl.col(column).cast(pl.Float64, strict=True),
            )
        optimized_df = optimized_df.with_columns(
            [
                optimized_df[name].shrink_dtype()
                for name, dtype in optimized_df.schema.items()
                if dtype.is_integer()
            ],
        )
        return optimized_df

    @staticmethod
    def chunked_processing(df: pl.DataFrame, chunk_size: int = 1000) -> pl.DataFrame:
        """Process DataFrame in chunks to reduce memory usage.

        Args:
            df (pl.DataFrame): DataFrame to process
            chunk_size (int): Size of each chunk

        Returns:
            pl.DataFrame: Processed DataFrame

        """
        logger.info("Processing DataFrame in chunks of size %s", chunk_size)

        # This is a placeholder - in a real implementation, this would
        # apply some processing to each chunk and combine results
        if chunk_size < 1:
            message = "Chunk size must be positive"
            raise ValueError(message)
        chunks = [
            df.slice(start, chunk_size) for start in range(0, len(df), chunk_size)
        ]
        for i, chunk in enumerate(chunks):
            logger.debug(
                "Processing chunk %s/%s with %s rows",
                i + 1,
                len(chunks),
                len(chunk),
            )
        return pl.concat(chunks) if chunks else df


class ParallelProcessor:
    """Handles parallel processing for better performance."""

    @staticmethod
    def parallel_apply(
        df: pl.DataFrame,
        func: Callable[[pl.Series], object],
        column: str,
        n_cores: int = 4,
    ) -> pl.Series:
        """Apply function to column in parallel.

        Args:
            df (pl.DataFrame): DataFrame to process
            func (Callable): Function to apply
            column (str): Column to apply function to
            n_cores (int): Number of cores to use

        Returns:
            pl.Series: Result of applying function

        """
        if n_cores < 1:
            message = "Worker count must be positive"
            raise ValueError(message)
        source = df[column]
        if source.is_empty():
            return source.clone()
        chunk_size = max(1, (len(source) + n_cores - 1) // n_cores)
        chunks = [
            source.slice(start, chunk_size)
            for start in range(0, len(source), chunk_size)
        ]

        def apply_chunk(chunk: pl.Series) -> pl.Series:
            result = func(chunk)
            if not isinstance(result, pl.Series):
                message = "Parallel callback must return a Polars Series"
                raise TypeError(message)
            return result

        with ThreadPoolExecutor(max_workers=n_cores) as executor:
            results = list(executor.map(apply_chunk, chunks))
        if any(
            len(result) != len(chunk)
            for result, chunk in zip(results, chunks, strict=True)
        ):
            message = "Parallel callback must preserve row count"
            raise ValueError(message)
        return pl.concat(results)


class CachingOptimizer[Value = object]:
    """Implements caching strategies for performance optimization."""

    def __init__(self) -> None:
        """Initialize the caching optimizer."""
        self.cache: dict[str, Value] = {}
        self.access_counts: dict[str, int] = {}

    def get(self, key: str) -> Value | None:
        """Get value from cache.

        Args:
            key (str): Cache key

        Returns:
            Cached value or None if not found

        """
        if key in self.cache:
            self.access_counts[key] = self.access_counts.get(key, 0) + 1
            logger.debug("Cache hit for key %s", key)
            return self.cache[key]
        logger.debug("Cache miss for key %s", key)
        return None

    def set(self, key: str, value: Value) -> None:
        """Set value in cache.

        Args:
            key (str): Cache key
            value: Value to cache

        """
        self.cache[key] = value
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        logger.debug("Set cache for key %s", key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics

        """
        total_accesses = sum(self.access_counts.values())
        return {
            "cache_size": len(self.cache),
            "total_accesses": total_accesses,
            "hit_rate": total_accesses / max(1, len(self.access_counts)),
            "most_accessed": sorted(
                self.access_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }


# Example usage function
def example_usage() -> None:
    """Demonstrate the performance optimization tools."""
    logger.info("%s", "Performance Optimization Tools Example")

    # Create profiler
    profiler = PerformanceProfiler()

    # Profile a function
    @profiler.profile("data_processing")
    def process_data() -> pl.DataFrame:
        # Simulate some data processing
        df = pl.DataFrame(
            {
                "A": range(10000),
                "B": range(10000, 20000),
                "C": [f"item_{i}" for i in range(10000)],
            },
        )

        # Optimize the DataFrame
        optimizer = DataOptimizer()
        optimized_df = optimizer.optimize_dataframe(df)

        # Process in chunks
        return optimizer.chunked_processing(optimized_df, chunk_size=1000)

    # Run the function
    result = process_data()
    logger.info("%s", f"Processed DataFrame with shape {result.shape}")

    # Print performance report
    profiler.print_report()

    # Test caching
    cache = CachingOptimizer()
    cache.set("test_key", "test_value")
    value = cache.get("test_key")
    logger.info("%s", f"Retrieved from cache: {value}")

    stats = cache.get_stats()
    logger.info("%s", f"Cache stats: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
