# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Processing time measurement utilities for genomics microcosting analysis.

This module provides utilities to measure and analyze processing time for
various operations in the genomics microcosting framework.
"""

import logging
import statistics
import sys
import time
import unittest
from typing import Literal, TypedDict
lazy from collections.abc import Callable

import numpy as np
import polars as pl

from genomics_microcosting.performance import PerformanceProfiler
from tests.checks import require_keys, require_runtime_instance


class ExecutionMeasurement(TypedDict):
    """One callback execution, retaining its result and failure separately."""

    operation_name: str
    wall_time: float
    cpu_time: float
    success: bool
    error: str | None
    result: object
    timestamp: float


class TimeSummary(TypedDict):
    """Statistics of successfully executed synthetic workloads."""

    mean: float
    median: float
    stdev: float
    min: float
    max: float


class ExecutionBatch(TypedDict):
    """Fields shared by successful and failed benchmark batches."""

    operation_name: str
    iterations: int
    successful_executions: int
    all_measurements: list[ExecutionMeasurement]


class SuccessfulBatch(ExecutionBatch):
    """A batch with observed successful timings."""

    wall_time_stats: TimeSummary
    cpu_time_stats: TimeSummary


class FailedBatch(ExecutionBatch):
    """A batch with no valid timings to summarize."""

    error: str


type ExecutionStats = SuccessfulBatch | FailedBatch


class TimeComparison(TypedDict):
    """Timing differences without fabricating missing observations."""

    baseline_mean: float
    test_mean: float
    improvement: float
    improvement_percentage: float


class AvailableComparison(TypedDict):
    """A comparison backed by successful batches on both sides."""

    comparison_possible: Literal[True]
    baseline_operation: str
    test_operation: str
    wall_time_comparison: TimeComparison
    cpu_time_comparison: TimeComparison


class UnavailableComparison(TypedDict):
    """An explicit inability to compare failed workloads."""

    comparison_possible: Literal[False]
    error: str


class ProcessingScalingAnalysis(TypedDict):
    """Observed sizes and timings in one synthetic scaling experiment."""

    sizes: list[int]
    wall_times: list[float]
    average_scaling_factor: float
    scaling_behavior: str
    scalability_results: dict[int, ExecutionStats]


class ProcessingReportRow(TypedDict):
    """Public columns emitted by the measurement report."""

    operation_name: str
    wall_time: float
    cpu_time: float
    success: bool
    timestamp: float


logger = logging.getLogger(__name__)
SUBLINEAR_LIMIT = 0.5
LINEAR_LIMIT = 1.5
EXPECTED_ITERATIONS = 5


def _write_line(message: str) -> None:
    """Write the utility's existing text output with one trailing newline."""
    sys.stdout.write(message + "\n")


class ProcessingTimeMeasurer:
    """Measures and analyzes processing time for various operations."""

    def __init__(self) -> None:
        """Initialize the processing time measurer."""
        self.measurements: dict[str, list[ExecutionMeasurement]] = {}
        self.profiler = PerformanceProfiler()

    def measure_execution_time[**P](
        self,
        operation_name: str,
        operation_func: Callable[P, object],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ExecutionMeasurement:
        """Measure execution time for a single operation.

        Args:
            operation_name (str): Name of the operation
            operation_func (Callable): Function to measure
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Dict[str, Any]: Measurement results

        """
        start_time = time.perf_counter()
        start_cpu = time.process_time()

        try:
            result = operation_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            logger.exception("Synthetic timing callback failed")
            result = None
            success = False
            error = str(e)

        end_time = time.perf_counter()
        end_cpu = time.process_time()

        wall_time = end_time - start_time
        cpu_time = end_cpu - start_cpu

        measurement: ExecutionMeasurement = {
            "operation_name": operation_name,
            "wall_time": wall_time,
            "cpu_time": cpu_time,
            "success": success,
            "error": error,
            "result": result,
            "timestamp": time.time(),
        }

        if operation_name not in self.measurements:
            self.measurements[operation_name] = []
        self.measurements[operation_name].append(measurement)

        return measurement

    def measure_multiple_executions[**P](
        self,
        operation_name: str,
        operation_func: Callable[P, object],
        iterations: int = 10,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ExecutionStats:
        """Measure execution time for multiple executions of an operation.

        Args:
            operation_name (str): Name of the operation
            operation_func (Callable): Function to measure
            iterations (int): Number of times to execute the function
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Dict[str, Any]: Aggregated measurement results

        """
        measurements: list[ExecutionMeasurement] = []

        for i in range(iterations):
            measurement = self.measure_execution_time(
                f"{operation_name}_run_{i + 1}",
                operation_func,
                *args,
                **kwargs,
            )
            measurements.append(measurement)

        # Calculate statistics
        successful_measurements = [m for m in measurements if m["success"]]

        if successful_measurements:
            wall_times = [m["wall_time"] for m in successful_measurements]
            cpu_times = [m["cpu_time"] for m in successful_measurements]

            stats: ExecutionStats = {
                "operation_name": operation_name,
                "iterations": iterations,
                "successful_executions": len(successful_measurements),
                "wall_time_stats": {
                    "mean": statistics.mean(wall_times),
                    "median": statistics.median(wall_times),
                    "stdev": statistics.stdev(wall_times) if len(wall_times) > 1 else 0,
                    "min": min(wall_times),
                    "max": max(wall_times),
                },
                "cpu_time_stats": {
                    "mean": statistics.mean(cpu_times),
                    "median": statistics.median(cpu_times),
                    "stdev": statistics.stdev(cpu_times) if len(cpu_times) > 1 else 0,
                    "min": min(cpu_times),
                    "max": max(cpu_times),
                },
                "all_measurements": measurements,
            }
        else:
            stats = {
                "operation_name": operation_name,
                "iterations": iterations,
                "successful_executions": 0,
                "error": "All executions failed",
                "all_measurements": measurements,
            }

        return stats

    def compare_processing_times(
        self,
        baseline_stats: ExecutionStats,
        test_stats: ExecutionStats,
    ) -> AvailableComparison | UnavailableComparison:
        """Compare processing times between baseline and test operations.

        Args:
            baseline_stats (Dict[str, Any]): Baseline measurement statistics
            test_stats (Dict[str, Any]): Test measurement statistics

        Returns:
            Dict[str, Any]: Comparison results

        """
        if (
            "wall_time_stats" not in baseline_stats
            or "cpu_time_stats" not in baseline_stats
            or "wall_time_stats" not in test_stats
            or "cpu_time_stats" not in test_stats
            or baseline_stats["successful_executions"] == 0
            or test_stats["successful_executions"] == 0
        ):
            return {
                "comparison_possible": False,
                "error": "Insufficient successful executions for comparison",
            }

        baseline_wall_mean = baseline_stats["wall_time_stats"]["mean"]
        test_wall_mean = test_stats["wall_time_stats"]["mean"]

        baseline_cpu_mean = baseline_stats["cpu_time_stats"]["mean"]
        test_cpu_mean = test_stats["cpu_time_stats"]["mean"]

        # Calculate improvements (negative means test is slower)
        wall_time_improvement = baseline_wall_mean - test_wall_mean
        wall_time_improvement_pct = (
            (wall_time_improvement / baseline_wall_mean * 100)
            if baseline_wall_mean > 0
            else 0
        )

        cpu_time_improvement = baseline_cpu_mean - test_cpu_mean
        cpu_time_improvement_pct = (
            (cpu_time_improvement / baseline_cpu_mean * 100)
            if baseline_cpu_mean > 0
            else 0
        )

        return {
            "comparison_possible": True,
            "baseline_operation": baseline_stats["operation_name"],
            "test_operation": test_stats["operation_name"],
            "wall_time_comparison": {
                "baseline_mean": baseline_wall_mean,
                "test_mean": test_wall_mean,
                "improvement": wall_time_improvement,
                "improvement_percentage": wall_time_improvement_pct,
            },
            "cpu_time_comparison": {
                "baseline_mean": baseline_cpu_mean,
                "test_mean": test_cpu_mean,
                "improvement": cpu_time_improvement,
                "improvement_percentage": cpu_time_improvement_pct,
            },
        }

    def get_processing_time_report(self) -> pl.DataFrame:
        """Get processing time report as DataFrame.

        Returns:
            pl.DataFrame: Processing time report

        """
        report_data: list[ProcessingReportRow] = [
            {
                "operation_name": operation_name,
                "wall_time": measurement["wall_time"],
                "cpu_time": measurement["cpu_time"],
                "success": measurement["success"],
                "timestamp": measurement["timestamp"],
            }
            for operation_name, measurements in self.measurements.items()
            for measurement in measurements
        ]

        return pl.DataFrame(report_data)

    def print_processing_time_summary(self) -> None:
        """Print formatted processing time summary."""
        if not self.measurements:
            _write_line("No processing time data collected.")
            return

        _write_line("\nProcessing Time Summary")
        _write_line("=" * 80)
        _write_line(
            f"{'Operation':<30} {'Count':<8} "
            f"{'Mean Wall Time':<15} {'Mean CPU Time':<15} "
            f"{'Success Rate':<12}",
        )
        _write_line("-" * 80)

        for operation_name, measurements in self.measurements.items():
            successful_count = sum(1 for m in measurements if m["success"])
            total_count = len(measurements)
            success_rate = (
                (successful_count / total_count) * 100 if total_count > 0 else 0
            )

            if successful_count > 0:
                wall_times = [m["wall_time"] for m in measurements if m["success"]]
                cpu_times = [m["cpu_time"] for m in measurements if m["success"]]
                mean_wall_time = statistics.mean(wall_times)
                mean_cpu_time = statistics.mean(cpu_times)
            else:
                mean_wall_time = 0
                mean_cpu_time = 0

            _write_line(
                f"{operation_name:<30} {total_count:<8} {mean_wall_time:<15.4f} "
                f"{mean_cpu_time:<15.4f} {success_rate:<11.1f}%",
            )


class CalculationEngineBenchmark:
    """Benchmark the calculation engine performance."""

    def __init__(self) -> None:
        """Initialize the benchmark."""
        self.time_measurer = ProcessingTimeMeasurer()

    def benchmark_formula_parsing(self, formulas: list[str]) -> ExecutionStats:
        """Benchmark formula parsing performance.

        Args:
            formulas (List[str]): List of formulas to parse

        Returns:
            Dict[str, Any]: Benchmark results

        """

        # This would test the actual formula parsing performance
        # For now, we'll simulate it
        def parse_formulas(formula_list: list[str]) -> int:
            # Simulate parsing work
            parsed_count = 0
            for formula in formula_list:
                # Simulate some parsing work
                if formula.startswith("="):
                    parsed_count += 1
                time.sleep(0.001)  # Simulate processing time
            return parsed_count

        return self.time_measurer.measure_multiple_executions(
            "formula_parsing",
            parse_formulas,
            iterations=EXPECTED_ITERATIONS,
            formula_list=formulas,
        )

    def benchmark_cell_calculations(self, cell_count: int) -> ExecutionStats:
        """Benchmark cell calculation performance.

        Args:
            cell_count (int): Number of cells to calculate

        Returns:
            Dict[str, Any]: Benchmark results

        """

        # This would test actual cell calculation performance
        # For now, we'll simulate it
        def calculate_cells(count: int) -> list[float]:
            # Simulate calculation work
            results: list[float] = []
            for i in range(count):
                # Simulate some calculation
                result = (i * 1.5) + (i * 0.7)
                results.append(result)
                if i % 100 == 0:
                    time.sleep(0.001)  # Simulate processing time
            return results

        return self.time_measurer.measure_multiple_executions(
            "cell_calculations",
            calculate_cells,
            iterations=3,
            count=cell_count,
        )


class TestProcessingTimeMeasurer(unittest.TestCase):
    """Processing time measurement tests."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.time_measurer = ProcessingTimeMeasurer()
        self.benchmark = CalculationEngineBenchmark()

    def test_single_execution_measurement(self) -> None:
        """Test measurement of single execution time."""

        def sample_operation() -> str:
            # Simulate some work
            time.sleep(0.01)
            return "result"

        measurement = self.time_measurer.measure_execution_time(
            "sample_operation",
            sample_operation,
        )

        require_runtime_instance(measurement, dict)
        require_keys(
            measurement,
            ("operation_name", "wall_time", "cpu_time", "success", "result"),
        )

        if not ((measurement["operation_name"]) == ("sample_operation")):
            raise AssertionError
        if not (measurement["success"]):
            raise AssertionError
        if not ((measurement["result"]) == ("result")):
            raise AssertionError
        if not ((measurement["wall_time"]) > (0)):
            raise AssertionError
        if not ((measurement["cpu_time"]) > (0)):
            raise AssertionError

    def test_multiple_execution_measurement(self) -> None:
        """Test measurement of multiple executions."""

        def sample_operation(x: int, y: int) -> int:
            # Simulate some work
            time.sleep(0.005)
            return x + y

        stats = self.time_measurer.measure_multiple_executions(
            "addition_operation",
            sample_operation,
            iterations=EXPECTED_ITERATIONS,
            x=10,
            y=20,
        )

        require_runtime_instance(stats, dict)
        require_keys(
            stats,
            (
                "operation_name",
                "iterations",
                "successful_executions",
                "wall_time_stats",
                "cpu_time_stats",
            ),
        )

        if not ((stats["operation_name"]) == ("addition_operation")):
            raise AssertionError
        if not ((stats["iterations"]) == (EXPECTED_ITERATIONS)):
            raise AssertionError
        if not ((stats["successful_executions"]) == (EXPECTED_ITERATIONS)):
            raise AssertionError

        # Check statistics
        if "wall_time_stats" not in stats:
            raise AssertionError(stats["error"])
        wall_stats = stats["wall_time_stats"]
        require_keys(wall_stats, ("mean", "median", "min", "max"))
        if not ((wall_stats["mean"]) > (0)):
            raise AssertionError

    def test_error_handling_in_measurement(self) -> None:
        """Test error handling during measurement."""

        def failing_operation() -> None:
            message = "Test error"
            raise ValueError(message)

        measurement = self.time_measurer.measure_execution_time(
            "failing_operation",
            failing_operation,
        )

        if measurement["success"]:
            raise AssertionError
        if ("error") not in (measurement):
            raise AssertionError
        if not ((measurement["error"]) is not None):
            raise AssertionError
        if (measurement["result"]) is not None:
            raise AssertionError

    def test_comparison_of_processing_times(self) -> None:
        """Test comparison of processing times."""

        # Create baseline measurements
        def fast_operation() -> str:
            time.sleep(0.01)
            return "fast"

        def slow_operation() -> str:
            time.sleep(0.02)
            return "slow"

        baseline_stats = self.time_measurer.measure_multiple_executions(
            "fast_operation",
            fast_operation,
            iterations=3,
        )

        test_stats = self.time_measurer.measure_multiple_executions(
            "slow_operation",
            slow_operation,
            iterations=3,
        )

        # Compare processing times
        comparison = self.time_measurer.compare_processing_times(
            baseline_stats,
            test_stats,
        )

        require_runtime_instance(comparison, dict)
        if ("comparison_possible") not in (comparison):
            raise AssertionError
        if comparison["comparison_possible"] is False:
            raise AssertionError

        # Check comparison results
        wall_comparison = comparison["wall_time_comparison"]
        require_keys(
            wall_comparison,
            ("baseline_mean", "test_mean", "improvement", "improvement_percentage"),
        )

        # Slow operation should have negative improvement (it's slower)
        if not ((wall_comparison["improvement"]) < (0)):
            raise AssertionError

    def test_processing_time_report(self) -> None:
        """Test processing time report generation."""

        # Run some measurements to generate data
        def dummy_operation() -> str:
            return "dummy"

        self.time_measurer.measure_execution_time("test1", dummy_operation)
        self.time_measurer.measure_execution_time("test2", dummy_operation)

        # Get report
        report = self.time_measurer.get_processing_time_report()
        require_runtime_instance(report, pl.DataFrame)
        if not ((len(report)) > (0)):
            raise AssertionError

        # Check required columns
        required_columns = [
            "operation_name",
            "wall_time",
            "cpu_time",
            "success",
            "timestamp",
        ]
        for col in required_columns:
            if (col) not in (report.columns):
                raise AssertionError

    def test_benchmark_formula_parsing(self) -> None:
        """Test formula parsing benchmark."""
        formulas = [
            "=A1+B1",
            "=SUM(A1:A10)",
            "=VLOOKUP(A1, B:C, 2, FALSE)",
            "=IF(A1>0, A1*B1, 0)",
        ]

        stats = self.benchmark.benchmark_formula_parsing(formulas)

        require_runtime_instance(stats, dict)
        require_keys(stats, ("operation_name", "iterations", "successful_executions"))
        if not ((stats["operation_name"]) == ("formula_parsing")):
            raise AssertionError

    def test_benchmark_cell_calculations(self) -> None:
        """Test cell calculation benchmark."""
        stats = self.benchmark.benchmark_cell_calculations(1000)

        require_runtime_instance(stats, dict)
        require_keys(stats, ("operation_name", "iterations", "successful_executions"))
        if not ((stats["operation_name"]) == ("cell_calculations")):
            raise AssertionError


class ScalabilityTester:
    """Test scalability of operations with increasing data sizes."""

    def __init__(self) -> None:
        """Initialize the scalability tester."""
        self.time_measurer = ProcessingTimeMeasurer()

    def test_scalability(
        self,
        operation_func: Callable[[list[int]], object],
        data_sizes: list[int],
    ) -> dict[int, ExecutionStats]:
        """Test scalability of an operation with different data sizes.

        Args:
            operation_func (Callable): Function to test
            data_sizes (List[int]): List of data sizes to test

        Returns:
            Dict[str, Any]: Scalability test results

        """
        results: dict[int, ExecutionStats] = {}

        for size in data_sizes:

            def test_operation(size: int = size) -> object:
                # Generate test data of specified size
                test_data = list(range(size))
                return operation_func(test_data)

            stats = self.time_measurer.measure_multiple_executions(
                f"scalability_test_{size}",
                test_operation,
                iterations=3,
            )

            results[size] = stats

        return results

    def analyze_scalability(
        self,
        scalability_results: dict[int, ExecutionStats],
    ) -> ProcessingScalingAnalysis:
        """Analyze scalability results.

        Args:
            scalability_results (Dict[int, Dict]): Results from scalability test

        Returns:
            Dict[str, Any]: Scalability analysis

        """
        sizes = list(scalability_results.keys())
        wall_times: list[float] = []

        for size in sizes:
            stats = scalability_results[size]
            if "wall_time_stats" in stats and stats["successful_executions"] > 0:
                wall_times.append(stats["wall_time_stats"]["mean"])
            else:
                wall_times.append(0)

        # Simple linear regression to determine scaling behavior
        if len(sizes) > 1 and all(t > 0 for t in wall_times):
            # Calculate approximate scaling factor
            scaling_factors: list[float] = []
            for i in range(1, len(sizes)):
                if sizes[i - 1] > 0 and wall_times[i - 1] > 0:
                    size_ratio = sizes[i] / sizes[i - 1]
                    time_ratio = wall_times[i] / wall_times[i - 1]
                    scaling_factor = time_ratio / size_ratio if size_ratio > 0 else 0
                    scaling_factors.append(scaling_factor)

            avg_scaling_factor = (
                statistics.mean(scaling_factors) if scaling_factors else 0
            )

            # Classify scaling behavior
            if avg_scaling_factor < SUBLINEAR_LIMIT:
                scaling_behavior = "sub-linear"
            elif avg_scaling_factor < LINEAR_LIMIT:
                scaling_behavior = "linear"
            else:
                scaling_behavior = "super-linear"
        else:
            avg_scaling_factor = 0
            scaling_behavior = "unknown"

        return {
            "sizes": sizes,
            "wall_times": wall_times,
            "average_scaling_factor": avg_scaling_factor,
            "scaling_behavior": scaling_behavior,
            "scalability_results": scalability_results,
        }


# Example usage:
if __name__ == "__main__":
    rng = np.random.default_rng()
    # Create processing time measurer
    time_measurer = ProcessingTimeMeasurer()

    # Define test operations
    def matrix_multiplication(size: int) -> tuple[int, ...]:
        """Simulate matrix multiplication."""
        # Create random matrices
        a = rng.random((size, size))
        b = rng.random((size, size))
        # Perform multiplication
        result = np.dot(a, b)
        return result.shape

    def data_processing(data_size: int) -> object:
        """Simulate data processing."""
        # Create test data
        data = pl.DataFrame(
            {
                "A": rng.random(data_size),
                "B": rng.random(data_size),
                "C": rng.random(data_size),
            },
        )
        # Perform some operations
        data["D"] = data["A"] * data["B"]
        data["E"] = data["C"] + data["D"]
        return data["E"].sum()

    # Measure multiple executions
    _write_line("Measuring matrix multiplication performance...")
    matrix_stats = time_measurer.measure_multiple_executions(
        "matrix_multiplication_50x50",
        matrix_multiplication,
        iterations=3,
        size=50,
    )

    _write_line("Measuring data processing performance...")
    data_stats = time_measurer.measure_multiple_executions(
        "data_processing_1000_rows",
        data_processing,
        iterations=3,
        data_size=1000,
    )

    # Print results
    if "wall_time_stats" not in matrix_stats:
        raise RuntimeError(matrix_stats["error"])
    if "wall_time_stats" not in data_stats:
        raise RuntimeError(data_stats["error"])
    _write_line("\nMatrix multiplication stats:")
    _write_line(f"  Mean wall time: {matrix_stats['wall_time_stats']['mean']:.4f}s")
    _write_line(
        f"  Success rate: {matrix_stats['successful_executions']}/"
        f"{matrix_stats['iterations']}",
    )

    _write_line("\nData processing stats:")
    _write_line(f"  Mean wall time: {data_stats['wall_time_stats']['mean']:.4f}s")
    _write_line(
        f"  Success rate: {data_stats['successful_executions']}/"
        f"{data_stats['iterations']}",
    )

    # Compare operations
    comparison = time_measurer.compare_processing_times(matrix_stats, data_stats)
    if comparison["comparison_possible"] is True:
        wall_comp = comparison["wall_time_comparison"]
        _write_line("\nComparison:")
        _write_line(
            f"  Matrix operation is {abs(wall_comp['improvement']):.4f}s "
            f"({'faster' if wall_comp['improvement'] > 0 else 'slower'}) "
            f"than data processing "
            f"({wall_comp['improvement_percentage']:.1f}%)",
        )

    # Print summary
    time_measurer.print_processing_time_summary()
