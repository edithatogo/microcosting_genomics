# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Load testing framework for genomics microcosting analysis.

This module provides load testing capabilities with variable data sizes
to benchmark performance of the genomics microcosting framework.
"""

import logging
import sys
import time
import unittest
from datetime import UTC, datetime
from typing import Concatenate, TypedDict
lazy from collections.abc import Callable
lazy from unittest.mock import Mock

import numpy as np
import polars as pl
lazy import psutil

from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer
from genomics_microcosting.performance import DataOptimizer, PerformanceProfiler
from tests.checks import require_runtime_instance


class LoadTestResult(TypedDict):
    """One synthetic workload run, including failure and resource observations."""

    data_size: int
    operation_name: str
    execution_time: float
    memory_used: float
    success: bool
    error: str | None
    timestamp: datetime


class DriverBenchmarkResult(TypedDict):
    """Native driver rows and measured callback time."""

    cost_drivers: pl.DataFrame
    execution_time: float
    data_size: int


class LoadingBenchmarkResult(TypedDict):
    """An explicitly simulated in-memory copy, not native file loading proof."""

    data: pl.DataFrame
    execution_time: float
    data_size: int
    requested_path: str


logger = logging.getLogger(__name__)
SMALL_DATA_SIZE = 100
STANDARD_DATA_SIZE = 1000


def _write_line(message: str) -> None:
    """Preserve this command-line utility's existing text output."""
    sys.stdout.write(message + "\n")


class LoadTestingFramework:
    """Load testing framework with variable data sizes."""

    def __init__(self) -> None:
        """Initialize the load testing framework."""
        self.profiler = PerformanceProfiler()
        self.results: list[LoadTestResult] = []

    def generate_test_data(self, size: int) -> pl.DataFrame:
        """Generate test data of specified size.

        Args:
            size (int): Number of rows to generate

        Returns:
            pl.DataFrame: Generated test data

        """
        rng = np.random.RandomState(42)  # Preserve the exact legacy fixture stream.

        # Generate realistic test data for genomics microcosting
        test_types = ["Panel", "WES (P)", "WES (T)", "WGS"]
        categories = ["Labour", "Equipment", "Consumables", "Compute", "Storage"]
        sub_categories = [
            "Sequencing",
            "Library Prep",
            "DNA Extraction",
            "Processing",
            "Archival",
        ]

        data = {
            "Test": rng.choice(test_types, size),
            "Category": rng.choice(categories, size),
            "Sub-Category": rng.choice(sub_categories, size),
            "Step": ["Sample Prep"] * size,
            "Quantity": rng.uniform(0.5, 5.0, size),
            "Unit_Cost": rng.uniform(50.0, 200.0, size),
        }

        # Calculate total cost
        data["Total_Cost"] = np.array(data["Quantity"]) * np.array(data["Unit_Cost"])

        return pl.DataFrame(data)

    def run_load_test[**P](
        self,
        data_size: int,
        operation_name: str,
        test_function: Callable[Concatenate[pl.DataFrame, P], object],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> LoadTestResult:
        """Run a load test with specified data size.

        Args:
            data_size (int): Size of test data
            operation_name (str): Name of the operation being tested
            test_function (callable): Function to test
            *args: Arguments to pass to test function
            **kwargs: Keyword arguments to pass to test function

        Returns:
            dict: Test results including timing and memory usage

        """
        # Generate test data
        test_data = self.generate_test_data(data_size)

        # Profile the operation
        start_time = time.time()
        start_memory = self._get_memory_usage()

        # Run the test function
        success = False
        error = None
        try:
            test_function(test_data, *args, **kwargs)
            success = True
        except Exception:
            logger.exception("Synthetic load callback failed")
            error = "Exception occurred during test execution"

        end_time = time.time()
        end_memory = self._get_memory_usage()

        # Calculate metrics
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory

        # Store results
        test_result: LoadTestResult = {
            "data_size": data_size,
            "operation_name": operation_name,
            "execution_time": execution_time,
            "memory_used": memory_used,
            "success": success,
            "error": error,
            "timestamp": datetime.now(UTC),
        }

        self.results.append(test_result)
        return test_result

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB.

        Returns:
            float: Memory usage in MB

        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0

    def run_scalability_test[**P](
        self,
        sizes: list[int],
        operation_name: str,
        test_function: Callable[Concatenate[pl.DataFrame, P], object],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> list[LoadTestResult]:
        """Run scalability test across multiple data sizes.

        Args:
            sizes (list): List of data sizes to test
            operation_name (str): Name of the operation being tested
            test_function (callable): Function to test
            *args: Arguments to pass to test function
            **kwargs: Keyword arguments to pass to test function

        Returns:
            list: List of test results

        """
        results: list[LoadTestResult] = []

        for size in sizes:
            _write_line(f"Running load test with {size} rows...")
            result = self.run_load_test(
                size,
                operation_name,
                test_function,
                *args,
                **kwargs,
            )
            results.append(result)
            _write_line(
                f"  Time: {result['execution_time']:.4f}s, "
                f"Memory: {result['memory_used']:.2f}MB",
            )

        return results

    def get_performance_report(self) -> pl.DataFrame:
        """Get performance report as DataFrame.

        Returns:
            pl.DataFrame: Performance report

        """
        return pl.DataFrame(self.results)

    def print_performance_summary(self) -> None:
        """Print formatted performance summary."""
        if not self.results:
            _write_line("No performance data collected.")
            return

        df = pl.DataFrame(self.results)

        _write_line("\nLoad Testing Performance Summary")
        _write_line("=" * 80)
        _write_line(
            f"{'Data Size':<12} {'Operation':<25} {'Time (s)':<12} "
            f"{'Memory (MB)':<12} {'Success':<8}",
        )
        _write_line("-" * 80)

        for row in df.iter_rows(named=True):
            _write_line(
                f"{row['data_size']:<12} {row['operation_name']:<25} "
                f"{row['execution_time']:<12.4f} "
                f"{row['memory_used']:<12.2f} {row['success']:<8}",
            )


class DataFrameOptimizationWorkload:
    """Test DataFrame optimization performance."""

    def __init__(self) -> None:
        """Select the native table optimizer for each workload."""
        self.optimizer = DataOptimizer()

    def test_optimization_performance(self, df: pl.DataFrame) -> pl.DataFrame:
        """Test DataFrame optimization performance.

        Args:
            df (pl.DataFrame): DataFrame to optimize

        Returns:
            pl.DataFrame: Optimized DataFrame

        """
        return self.optimizer.optimize_dataframe(df)

    def test_chunked_processing_performance(
        self,
        df: pl.DataFrame,
        chunk_size: int = 1000,
    ) -> pl.DataFrame:
        """Test chunked processing performance.

        Args:
            df (pl.DataFrame): DataFrame to process
            chunk_size (int): Chunk size for processing

        Returns:
            pl.DataFrame: Processed DataFrame

        """
        return self.optimizer.chunked_processing(df, chunk_size)


class TestLoadTestingFramework(unittest.TestCase):
    """Load testing framework tests."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.load_tester = LoadTestingFramework()
        self.optimizer_tester = DataFrameOptimizationWorkload()

    def test_generate_test_data(self) -> None:
        """Test generation of test data."""
        # Test small dataset
        small_data = self.load_tester.generate_test_data(100)
        require_runtime_instance(small_data, pl.DataFrame)
        if not ((len(small_data)) == SMALL_DATA_SIZE):
            raise AssertionError
        if ("Test") not in (small_data.columns):
            raise AssertionError
        if ("Category") not in (small_data.columns):
            raise AssertionError
        if ("Total_Cost") not in (small_data.columns):
            raise AssertionError

        # Test larger dataset
        large_data = self.load_tester.generate_test_data(1000)
        if not ((len(large_data)) == STANDARD_DATA_SIZE):
            raise AssertionError

        # Verify data types
        if not (large_data["Quantity"].dtype.is_numeric()):
            raise AssertionError
        if not (large_data["Unit_Cost"].dtype.is_numeric()):
            raise AssertionError
        if not (large_data["Total_Cost"].dtype.is_numeric()):
            raise AssertionError

    def test_run_load_test(self) -> None:
        """Test running a single load test."""

        def simple_operation(df: pl.DataFrame) -> object:
            return df["Total_Cost"].sum()

        result = self.load_tester.run_load_test(
            data_size=1000,
            operation_name="sum_total_cost",
            test_function=simple_operation,
        )

        require_runtime_instance(result, dict)
        if ("data_size") not in (result):
            raise AssertionError
        if ("execution_time") not in (result):
            raise AssertionError
        if ("memory_used") not in (result):
            raise AssertionError
        if ("success") not in (result):
            raise AssertionError
        if not ((result["data_size"]) == STANDARD_DATA_SIZE):
            raise AssertionError
        if not (result["success"]):
            raise AssertionError

    def test_scalability_test(self) -> None:
        """Test scalability testing across multiple data sizes."""

        def count_rows(df: pl.DataFrame) -> int:
            return len(df)

        sizes = [100, 500, 1000]
        results = self.load_tester.run_scalability_test(
            sizes=sizes,
            operation_name="count_rows",
            test_function=count_rows,
        )

        require_runtime_instance(results, list)
        if not ((len(results)) == (len(sizes))):
            raise AssertionError

        # Verify results
        for i, result in enumerate(results):
            if not ((result["data_size"]) == (sizes[i])):
                raise AssertionError
            if not (result["success"]):
                raise AssertionError

    def test_dataframe_optimization_performance(self) -> None:
        """Test DataFrame optimization performance."""
        # Create test DataFrame
        df = self.load_tester.generate_test_data(10000)

        # Test optimization
        result = self.load_tester.run_load_test(
            data_size=len(df),
            operation_name="dataframe_optimization",
            test_function=self.optimizer_tester.test_optimization_performance,
        )

        if not (result["success"]):
            raise AssertionError
        if not ((result["execution_time"]) > (0)):
            raise AssertionError

    def test_performance_report(self) -> None:
        """Test performance report generation."""

        # Run a few tests to generate data
        def dummy_operation(df: pl.DataFrame) -> pl.DataFrame:
            return df.head(10)

        self.load_tester.run_load_test(100, "dummy1", dummy_operation)
        self.load_tester.run_load_test(200, "dummy2", dummy_operation)

        # Get report
        report = self.load_tester.get_performance_report()
        require_runtime_instance(report, pl.DataFrame)
        if not ((len(report)) > (0)):
            raise AssertionError

        # Check required columns
        required_columns = [
            "data_size",
            "operation_name",
            "execution_time",
            "memory_used",
            "success",
        ]
        for col in required_columns:
            if (col) not in (report.columns):
                raise AssertionError


class BenchmarkingScenarios:
    """Benchmarking scenarios for different operations."""

    @staticmethod
    def cost_driver_analysis_benchmark(
        data_manager_mock: Mock,
        data_size: int,
    ) -> DriverBenchmarkResult:
        """Benchmark cost driver analysis with specified data size.

        Args:
            data_manager_mock: Mock data manager
            data_size (int): Size of test data

        Returns:
            dict: Benchmark results

        """
        # Generate test data
        load_tester = LoadTestingFramework()
        test_data = load_tester.generate_test_data(data_size)

        # Mock data manager to return test data
        data_manager_mock.load_sheet.return_value = test_data

        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager_mock)

        # Run analysis
        start_time = time.time()
        cost_drivers = analyzer.calculate_absolute_cost_drivers(
            test_data,
        )
        execution_time = time.time() - start_time

        return {
            "cost_drivers": cost_drivers,
            "execution_time": execution_time,
            "data_size": data_size,
        }

    @staticmethod
    def data_loading_benchmark(
        file_path: str,
        data_size: int,
    ) -> LoadingBenchmarkResult:
        """Benchmark data loading performance.

        Args:
            file_path (str): Path to test file
            data_size (int): Size of test data

        Returns:
            dict: Benchmark results

        """
        # This would test actual file loading performance
        # For now, we'll simulate it
        load_tester = LoadTestingFramework()
        test_data = load_tester.generate_test_data(data_size)

        start_time = time.time()
        # Simulate data loading
        result = test_data.clone()
        execution_time = time.time() - start_time

        return {
            "data": result,
            "requested_path": file_path,
            "execution_time": execution_time,
            "data_size": data_size,
        }


# Example usage:
if __name__ == "__main__":
    # Create load testing framework
    load_tester = LoadTestingFramework()

    # Define test function
    def sample_analysis(df: pl.DataFrame) -> dict[str, object]:
        """Sample analysis function."""
        # Simulate some analysis work
        return {
            "total_rows": len(df),
            "avg_cost": df["Total_Cost"].mean(),
            "max_cost": df["Total_Cost"].max(),
            "min_cost": df["Total_Cost"].min(),
        }

    # Run scalability test
    sizes = [1000, 5000, 10000, 50000]
    _write_line("Running scalability test...")
    results = load_tester.run_scalability_test(
        sizes=sizes,
        operation_name="sample_analysis",
        test_function=sample_analysis,
    )

    # Print performance summary
    load_tester.print_performance_summary()

    # Get detailed report
    report = load_tester.get_performance_report()
    _write_line(f"\nDetailed report shape: {report.shape}")


def test_chunked_workload_uses_native_table_boundary() -> None:
    """Exercise the workload itself rather than recording a hidden callback error."""
    result = DataFrameOptimizationWorkload().test_chunked_processing_performance(
        pl.DataFrame({"value": list(range(7))}),
        chunk_size=3,
    )
    require_runtime_instance(result, pl.DataFrame)
    if result["value"].to_list() != list(range(7)):
        raise AssertionError
