# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for the performance optimization module."""

from typing import Never

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from genomics_microcosting.performance import (
    CachingOptimizer,
    DataOptimizer,
    PerformanceProfiler,
)
from tests.checks import require_equal


def test_performance_profiler() -> None:
    """Test the PerformanceProfiler class."""
    profiler = PerformanceProfiler()

    # Test profiling a function
    @profiler.profile("test_operation")
    def sample_operation() -> int:
        # Simulate some work
        return sum(range(1000))

    # Run the operation
    result = sample_operation()
    require_equal(result, 499500)

    # Check metrics
    report = profiler.get_report()
    if "test_operation" not in report:
        raise AssertionError
    metrics = report["test_operation"]
    if not (metrics["call_count"] == 1):
        raise AssertionError
    if not (metrics["total_time"] > 0):
        raise AssertionError
    if not (metrics["avg_time"] > 0):
        raise AssertionError


def test_data_optimizer_optimize_dataframe() -> None:
    """Test optimizing DataFrame memory usage."""
    # Create a DataFrame with mixed data types
    df = pl.DataFrame(
        {
            "int64_col": pl.Series([1, 2, 3], dtype=pl.Int64),
            "float64_col": pl.Series([1.1, 2.2, 3.3], dtype=pl.Float64),
            "object_col": ["a", "b", "c"],
            "numeric_string_col": ["1", "2", "3"],
        },
    )

    # Optimize the DataFrame
    optimizer = DataOptimizer()
    optimized_df = optimizer.optimize_dataframe(
        df,
        numeric_columns=("numeric_string_col",),
    )

    # Check that the DataFrame is still valid
    if not (len(optimized_df) == len(df)):
        raise AssertionError
    if not (list(optimized_df.columns) == list(df.columns)):
        raise AssertionError

    # Check that some columns were optimized
    # The numeric string column should be converted to numeric
    if not (optimized_df["numeric_string_col"].dtype.is_numeric()):
        raise AssertionError

    # Memory usage should be the same or lower
    original_memory = df.estimated_size()
    optimized_memory = optimized_df.estimated_size()
    if not (optimized_memory <= original_memory):
        raise AssertionError


def test_data_optimizer_chunked_processing() -> None:
    """Test chunked processing of DataFrames."""
    # Create a large DataFrame
    df = pl.DataFrame(
        {
            "A": range(1000),
            "B": range(1000, 2000),
        },
    )

    # Process in chunks
    optimizer = DataOptimizer()
    chunked_df = optimizer.chunked_processing(df, chunk_size=100)

    # Check that the result is the same
    assert_frame_equal(df, chunked_df)


def test_caching_optimizer() -> None:
    """Test the CachingOptimizer class."""
    minimum_cache_accesses = 3
    cache = CachingOptimizer()

    # Test setting and getting values
    cache.set("key1", "value1")
    if not (cache.get("key1") == "value1"):
        raise AssertionError

    # Test cache miss
    if cache.get("nonexistent") is not None:
        raise AssertionError

    # Test cache statistics
    cache.set("key2", "value2")
    cache.get("key1")  # Access key1 again
    cache.get("key1")  # Access key1 again

    stats = cache.get_stats()
    require_equal(stats["cache_size"], 2)
    # The access count includes the initial set operations, so it will be higher
    if not (stats["total_accesses"] >= minimum_cache_accesses):
        raise AssertionError
    require_equal(len(stats["most_accessed"]), 2)


def test_performance_profiler_report() -> None:
    """Test the performance profiler report generation."""
    profiler = PerformanceProfiler()

    # Profile multiple operations
    @profiler.profile("operation1")
    def op1() -> int:
        return sum(range(100))

    @profiler.profile("operation2")
    def op2() -> int:
        return sum(range(200))

    # Run operations multiple times
    for _ in range(3):
        op1()
        op2()

    # Get report
    report = profiler.get_report()
    require_equal(len(report), 2)
    if "operation1" not in report:
        raise AssertionError
    if "operation2" not in report:
        raise AssertionError

    # Check metrics for operation1
    op1_metrics = report["operation1"]
    require_equal(op1_metrics["call_count"], 3)
    if not (op1_metrics["total_time"] > 0):
        raise AssertionError
    if not (op1_metrics["avg_time"] > 0):
        raise AssertionError
    if not (op1_metrics["max_time"] > 0):
        raise AssertionError
    if not (op1_metrics["min_time"] < float("inf")):
        raise AssertionError

    # Check metrics for operation2
    op2_metrics = report["operation2"]
    require_equal(op2_metrics["call_count"], 3)


def test_performance_profiler_error_handling() -> None:
    """Test error handling in performance profiler."""
    profiler = PerformanceProfiler()

    # Profile a function that raises an exception
    @profiler.profile("error_operation")
    def error_operation() -> Never:
        message = "Test error"
        raise ValueError(message)

    # The profiler should re-raise the exception
    with pytest.raises(ValueError, match="Test error"):
        error_operation()

    # Check that the error was recorded
    report = profiler.get_report()
    if "error_operation" not in report:
        raise AssertionError
    metrics = report["error_operation"]
    if not (metrics["errors"] == 1):
        raise AssertionError


if __name__ == "__main__":
    pytest.main([__file__])


def test_optimizer_preserves_mixed_text_and_float_precision() -> None:
    """Reject lossy text conversion and retain financial Float64 precision."""
    source = pl.DataFrame(
        {"mixed": ["1", "unknown"], "money": [123456.789012345, 1 / 3]},
    )
    result = DataOptimizer.optimize_dataframe(source)
    assert_frame_equal(source, result)


def test_chunking_rejects_nonpositive_size() -> None:
    """Do not allow an invalid block size to produce misleading output."""
    with pytest.raises(ValueError, match="positive"):
        DataOptimizer.chunked_processing(pl.DataFrame({"x": [1]}), chunk_size=0)
