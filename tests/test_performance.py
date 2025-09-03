"""Tests for the performance optimization module."""

import pandas as pd
import pytest
from pathlib import Path
import numpy as np

from unimelb_phd_phase_1.performance import PerformanceProfiler, DataOptimizer, CachingOptimizer


def test_performance_profiler():
    """Test the PerformanceProfiler class."""
    profiler = PerformanceProfiler()
    
    # Test profiling a function
    @profiler.profile("test_operation")
    def sample_operation():
        # Simulate some work
        result = sum(range(1000))
        return result
    
    # Run the operation
    result = sample_operation()
    assert result == 499500
    
    # Check metrics
    report = profiler.get_report()
    assert "test_operation" in report
    metrics = report["test_operation"]
    assert metrics["call_count"] == 1
    assert metrics["total_time"] > 0
    assert metrics["avg_time"] > 0


def test_data_optimizer_optimize_dataframe():
    """Test optimizing DataFrame memory usage."""
    # Create a DataFrame with mixed data types
    df = pd.DataFrame({
        "int64_col": pd.Series([1, 2, 3], dtype="int64"),
        "float64_col": pd.Series([1.1, 2.2, 3.3], dtype="float64"),
        "object_col": ["a", "b", "c"],
        "numeric_string_col": ["1", "2", "3"]
    })
    
    # Optimize the DataFrame
    optimizer = DataOptimizer()
    optimized_df = optimizer.optimize_dataframe(df)
    
    # Check that the DataFrame is still valid
    assert len(optimized_df) == len(df)
    assert list(optimized_df.columns) == list(df.columns)
    
    # Check that some columns were optimized
    # The numeric string column should be converted to numeric
    assert pd.api.types.is_numeric_dtype(optimized_df["numeric_string_col"])
    
    # Memory usage should be the same or lower
    original_memory = df.memory_usage(deep=True).sum()
    optimized_memory = optimized_df.memory_usage(deep=True).sum()
    assert optimized_memory <= original_memory


def test_data_optimizer_chunked_processing():
    """Test chunked processing of DataFrames."""
    # Create a large DataFrame
    df = pd.DataFrame({
        "A": range(1000),
        "B": range(1000, 2000)
    })
    
    # Process in chunks
    optimizer = DataOptimizer()
    chunked_df = optimizer.chunked_processing(df, chunk_size=100)
    
    # Check that the result is the same
    pd.testing.assert_frame_equal(df, chunked_df)


def test_caching_optimizer():
    """Test the CachingOptimizer class."""
    cache = CachingOptimizer()
    
    # Test setting and getting values
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Test cache miss
    assert cache.get("nonexistent") is None
    
    # Test cache statistics
    cache.set("key2", "value2")
    cache.get("key1")  # Access key1 again
    cache.get("key1")  # Access key1 again
    
    stats = cache.get_stats()
    assert stats["cache_size"] == 2
    # The access count includes the initial set operations, so it will be higher
    assert stats["total_accesses"] >= 3
    assert len(stats["most_accessed"]) == 2


def test_performance_profiler_report():
    """Test the performance profiler report generation."""
    profiler = PerformanceProfiler()
    
    # Profile multiple operations
    @profiler.profile("operation1")
    def op1():
        return sum(range(100))
    
    @profiler.profile("operation2")
    def op2():
        return sum(range(200))
    
    # Run operations multiple times
    for _ in range(3):
        op1()
        op2()
    
    # Get report
    report = profiler.get_report()
    assert len(report) == 2
    assert "operation1" in report
    assert "operation2" in report
    
    # Check metrics for operation1
    op1_metrics = report["operation1"]
    assert op1_metrics["call_count"] == 3
    assert op1_metrics["total_time"] > 0
    assert op1_metrics["avg_time"] > 0
    assert op1_metrics["max_time"] > 0
    assert op1_metrics["min_time"] < float('inf')
    
    # Check metrics for operation2
    op2_metrics = report["operation2"]
    assert op2_metrics["call_count"] == 3


def test_performance_profiler_error_handling():
    """Test error handling in performance profiler."""
    profiler = PerformanceProfiler()
    
    # Profile a function that raises an exception
    @profiler.profile("error_operation")
    def error_operation():
        raise ValueError("Test error")
    
    # The profiler should re-raise the exception
    with pytest.raises(ValueError, match="Test error"):
        error_operation()
    
    # Check that the error was recorded
    report = profiler.get_report()
    assert "error_operation" in report
    metrics = report["error_operation"]
    assert metrics["errors"] == 1


if __name__ == "__main__":
    pytest.main([__file__])