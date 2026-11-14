# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Scalability testing scenarios for genomics microcosting analysis.

This module provides comprehensive scalability testing scenarios to evaluate
how the genomics microcosting framework performs with increasing data sizes
and complexity.
"""

import logging
import time
import unittest
from typing import TYPE_CHECKING, Protocol, TypedDict, cast
from unittest.mock import Mock

import numpy as np
import polars as pl
lazy import psutil
lazy from matplotlib.figure import Figure

from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer
from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.performance import DataOptimizer, PerformanceProfiler
from tests.checks import require_equal, require_runtime_instance

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


class _BenchmarkAxes(Protocol):
    def plot(
        self,
        x: Sequence[int],
        y: Sequence[float],
        *,
        marker: str,
        label: str,
    ) -> object: ...
    def set_xlabel(self, label: str) -> object: ...
    def set_ylabel(self, label: str) -> object: ...
    def set_title(self, label: str) -> object: ...
    def legend(self) -> object: ...
    def grid(self, *, visible: bool) -> None: ...


class _BenchmarkPlotter(Protocol):
    def subplots(
        self,
        *,
        figsize: tuple[int, int],
    ) -> tuple[Figure, _BenchmarkAxes]: ...
    def tight_layout(self) -> None: ...
    def show(self) -> None: ...


# Use a non-interactive backend for the plotting tests.
try:
    import matplotlib as mpl

    mpl.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt

    has_matplotlib = True
except ImportError:
    has_matplotlib = False
    plt = None

logger = logging.getLogger(__name__)


class DriverMeasurement(TypedDict):
    """The observed driver report size and first category."""

    cost_drivers_count: int
    top_cost_driver: object


class LoadingMeasurement(TypedDict):
    """Source table dimensions consumed by a loading benchmark."""

    sheets_loaded: int
    total_rows: int
    total_columns: int


class OptimizationMeasurement(TypedDict):
    """Measured native table memory after optimization."""

    sheets_optimized: int
    memory_savings_mb: float
    savings_percentage: float


class Measurement(TypedDict):
    """Fields required to compare benchmark observations."""

    data_size: int
    mean_execution_time: float


class ScalabilityResult(Measurement):
    """One measured synthetic callback batch, including actual success state."""

    operation_name: str
    complexity: str
    iterations: int
    min_execution_time: float
    max_execution_time: float
    mean_memory_usage: float
    success_rate: float
    timestamp: float


class ScalingAnalysis(TypedDict):
    """A comparison of measured sizes and execution times."""

    sizes: list[int]
    times: list[float]
    scaling_factors: list[float]
    average_scaling_factor: float
    scaling_behavior: str
    performance_regression: bool


class AnalysisError(TypedDict):
    """An explicit unavailable benchmark analysis."""

    error: str


class Baseline(TypedDict):
    """Frozen observations and their scaling summary."""

    results: list[ScalabilityResult]
    analysis: ScalingAnalysis | AnalysisError


class BenchmarkScenario(TypedDict):
    """A synthetic benchmark callback and its selected workload."""

    name: str
    function: Callable[[dict[str, pl.DataFrame]], object]
    sizes: list[int]
    complexity: str


class BaselineComparison(TypedDict):
    """Comparison against an existing synthetic baseline."""

    current_time: float
    baseline_time: float
    regression_detected: bool
    time_difference: float


class ScalabilityTester:
    """Comprehensive scalability tester for genomics microcosting analysis."""

    def __init__(self) -> None:
        """Initialize the scalability tester."""
        self.profiler = PerformanceProfiler()
        self.results: list[ScalabilityResult] = []

    def generate_scalability_test_data(
        self,
        size: int,
        complexity: str = "basic",
    ) -> dict[str, pl.DataFrame]:
        """Generate test data of specified size and complexity.

        Args:
            size (int): Number of rows to generate
            complexity (str): Complexity level ("basic", "medium", "complex")

        Returns:
            Dict[str, pl.DataFrame]: Generated test data

        """
        rng = np.random.default_rng(42 + size)  # Different seed for different sizes

        # Base data
        test_types = ["Panel", "WES (P)", "WES (T)", "WGS"]
        categories = ["Labour", "Equipment", "Consumables", "Compute", "Storage"]

        if complexity == "basic":
            sub_categories = ["Sequencing", "Library Prep", "DNA Extraction"]
            steps = ["Sample Prep"]
        elif complexity == "medium":
            sub_categories = [
                "Sequencing",
                "Library Prep",
                "DNA Extraction",
                "Processing",
                "Analysis",
            ]
            steps = ["Sample Prep", "QC", "Processing"]
        else:  # complex
            sub_categories = [
                "Sequencing",
                "Library Prep",
                "DNA Extraction",
                "Processing",
                "Analysis",
                "Storage",
                "Retrieval",
            ]
            steps = [
                "Sample Prep",
                "QC",
                "Processing",
                "Analysis",
                "Storage",
                "Retrieval",
            ]

        # Generate main detailed table
        data = {
            "Test": rng.choice(test_types, size),
            "Category": rng.choice(categories, size),
            "Sub-Category": rng.choice(sub_categories, size),
            "Step": rng.choice(steps, size),
            "Quantity": rng.uniform(0.5, 5.0, size),
            "Unit_Cost": rng.uniform(50.0, 200.0, size),
        }

        # Calculate total cost
        data["Total_Cost"] = np.array(data["Quantity"]) * np.array(data["Unit_Cost"])

        detailed_table = pl.DataFrame(data)

        # Generate additional sheets based on complexity
        additional_sheets: dict[str, pl.DataFrame] = {}

        if complexity in ["medium", "complex"]:
            # DSA parameters
            dsa_params = {
                "Labour Prices": pl.DataFrame(
                    {
                        "Parameter": ["Hourly Rate", "Overtime Rate"],
                        "Baseline": [50.0, 75.0],
                        "Low": [40.0, 60.0],
                        "High": [60.0, 90.0],
                    },
                ),
                "Equipment Throughput": pl.DataFrame(
                    {
                        "Parameter": ["Utilization Rate", "Maintenance Factor"],
                        "Baseline": [0.8, 0.95],
                        "Low": [0.6, 0.9],
                        "High": [0.95, 0.99],
                    },
                ),
            }
            additional_sheets.update(dsa_params)

        if complexity == "complex":
            # PSA parameters
            psa_params = {
                "PSA": pl.DataFrame(
                    {
                        "Parameter": [
                            "Labour Cost",
                            "Equipment Cost",
                            "Consumable Cost",
                            "Compute Cost",
                        ],
                        "Distribution": ["normal", "normal", "normal", "normal"],
                        "Mean": [50000, 40000, 30000, 20000],
                        "Std": [5000, 4000, 3000, 2000],
                    },
                ),
            }
            additional_sheets.update(psa_params)

        return {
            "Detailed Table": detailed_table,
            **additional_sheets,
        }

    def run_scalability_test(
        self,
        operation_name: str,
        test_function: Callable[[dict[str, pl.DataFrame]], object],
        sizes: list[int],
        complexity: str = "basic",
        iterations: int = 3,
    ) -> list[ScalabilityResult]:
        """Run scalability test across multiple data sizes.

        Args:
            operation_name (str): Name of the operation being tested
            test_function (Callable): Function to test
            sizes (List[int]): List of data sizes to test
            complexity (str): Complexity level
            iterations (int): Number of iterations per size

        Returns:
            List[Dict[str, any]]: Test results

        """
        results: list[ScalabilityResult] = []

        for size in sizes:
            logger.info(
                "%s",
                f"Running scalability test for {operation_name} with {size} rows...",
            )

            # Generate test data
            test_data = self.generate_scalability_test_data(size, complexity)

            # Run multiple iterations
            iteration_times: list[float] = []
            iteration_memory: list[float] = []
            successes = 0

            for _iteration in range(iterations):
                start_time = time.time()
                start_memory = self._get_memory_usage()

                try:
                    test_function(test_data)
                    successes += 1
                except Exception:
                    logger.exception("Could not complete the current operation")

                end_time = time.time()
                end_memory = self._get_memory_usage()

                execution_time = end_time - start_time
                memory_used = end_memory - start_memory

                iteration_times.append(execution_time)
                iteration_memory.append(memory_used)

            # Calculate statistics
            if iteration_times:
                mean_time = sum(iteration_times) / len(iteration_times)
                min_time = min(iteration_times)
                max_time = max(iteration_times)
            else:
                mean_time = min_time = max_time = 0

            if iteration_memory:
                mean_memory = sum(iteration_memory) / len(iteration_memory)
            else:
                mean_memory = 0

            # Store results
            test_result: ScalabilityResult = {
                "operation_name": operation_name,
                "data_size": size,
                "complexity": complexity,
                "iterations": iterations,
                "mean_execution_time": mean_time,
                "min_execution_time": min_time,
                "max_execution_time": max_time,
                "mean_memory_usage": mean_memory,
                "success_rate": successes / iterations if iterations > 0 else 0,
                "timestamp": time.time(),
            }

            results.append(test_result)
            self.results.append(test_result)

            logger.info(
                "%s",
                f"  Mean time: {mean_time:.4f}s, Mean memory: {mean_memory:.2f}MB",
            )

        return results

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

    def analyze_scaling_behavior(
        self,
        results: Sequence[Measurement],
    ) -> ScalingAnalysis | AnalysisError:
        """Analyze scaling behavior from test results.

        Args:
            results (List[Dict[str, any]]): Test results

        Returns:
            Dict[str, any]: Scaling analysis

        """
        sublinear_scaling_factor = 0.5
        linear_scaling_limit = 1.5
        poor_scaling_factor = 2.0
        if not results:
            return {"error": "No results to analyze"}

        # Extract data points
        sizes = [r["data_size"] for r in results]
        times = [r["mean_execution_time"] for r in results]

        # Calculate scaling factors
        scaling_factors: list[float] = []
        for i in range(1, len(sizes)):
            if sizes[i - 1] > 0 and times[i - 1] > 0:
                size_ratio = sizes[i] / sizes[i - 1]
                time_ratio = times[i] / times[i - 1]
                scaling_factor = time_ratio / size_ratio if size_ratio > 0 else 0
                scaling_factors.append(scaling_factor)

        avg_scaling_factor = (
            sum(scaling_factors) / len(scaling_factors) if scaling_factors else 0
        )

        # Classify scaling behavior
        if avg_scaling_factor < sublinear_scaling_factor:
            scaling_behavior = "sub-linear (good)"
        elif avg_scaling_factor < linear_scaling_limit:
            scaling_behavior = "linear (acceptable)"
        else:
            scaling_behavior = "super-linear (concerning)"

        return {
            "sizes": sizes,
            "times": times,
            "scaling_factors": scaling_factors,
            "average_scaling_factor": avg_scaling_factor,
            "scaling_behavior": scaling_behavior,
            "performance_regression": avg_scaling_factor > poor_scaling_factor,
        }

    def generate_scalability_report(self) -> pl.DataFrame:
        """Generate scalability report.

        Returns:
            pl.DataFrame: Scalability report

        """
        return pl.DataFrame(self.results)

    def plot_scalability_results(self, operation_name: str | None = None) -> None:
        """Plot scalability results.

        Args:
            operation_name (str): Specific operation to plot (None for all)

        """
        # Filter results
        if operation_name:
            results = [r for r in self.results if r["operation_name"] == operation_name]
        else:
            results = self.results

        if not results:
            logger.info("%s", "No results to plot")
            return

        # Group by operation
        operations: dict[str, list[ScalabilityResult]] = {}
        for result in results:
            op_name = result["operation_name"]
            if op_name not in operations:
                operations[op_name] = []
            operations[op_name].append(result)

        # Create plot
        if plt is None:
            message = "Matplotlib is required to plot benchmark results"
            raise ImportError(message)
        plotter = cast("_BenchmarkPlotter", plt)
        _fig, ax = plotter.subplots(figsize=(10, 6))

        for op_name, op_results in operations.items():
            sizes = [r["data_size"] for r in op_results]
            times = [r["mean_execution_time"] for r in op_results]
            ax.plot(sizes, times, marker="o", label=op_name)

        ax.set_xlabel("Data Size (rows)")
        ax.set_ylabel("Execution Time (seconds)")
        ax.set_title("Scalability Analysis")
        ax.legend()
        ax.grid(visible=True)

        plotter.tight_layout()
        plotter.show()


class GenomicsAnalysisScalability:
    """Scalability tests for genomics analysis operations."""

    def __init__(self) -> None:
        """Initialize the genomics analysis scalability tester."""
        self.tester = ScalabilityTester()

    def test_cost_driver_analysis_scalability(
        self,
        test_data: dict[str, pl.DataFrame],
    ) -> DriverMeasurement:
        """Test scalability of cost driver analysis.

        Args:
            test_data (Dict[str, pl.DataFrame]): Test data

        Returns:
            Dict[str, any]: Analysis results

        """
        # Mock data manager
        mock_data_manager = Mock(spec=DataManager)
        mock_data_manager.load_sheet.return_value = test_data.get("Detailed Table")

        # Initialize analyzer
        analyzer = CostDriverAnalyzer(mock_data_manager)

        # Run analysis
        detailed_table = test_data.get("Detailed Table", pl.DataFrame())
        cost_drivers = analyzer.calculate_absolute_cost_drivers(
            detailed_table,
        )

        return {
            "cost_drivers_count": len(cost_drivers),
            "top_cost_driver": cost_drivers.row(0, named=True)["Category"]
            if len(cost_drivers) > 0
            else None,
        }

    def test_data_loading_scalability(
        self,
        test_data: dict[str, pl.DataFrame],
    ) -> LoadingMeasurement:
        """Test scalability of data loading operations.

        Args:
            test_data (Dict[str, pl.DataFrame]): Test data

        Returns:
            Dict[str, any]: Loading results

        """
        # Simulate data loading
        total_rows = 0
        total_columns = 0

        for df in test_data.values():
            total_rows += len(df)
            total_columns += len(df.columns)

        return {
            "sheets_loaded": len(test_data),
            "total_rows": total_rows,
            "total_columns": total_columns,
        }

    def test_data_optimization_scalability(
        self,
        test_data: dict[str, pl.DataFrame],
    ) -> OptimizationMeasurement:
        """Test scalability of data optimization operations.

        Args:
            test_data (Dict[str, pl.DataFrame]): Test data

        Returns:
            Dict[str, any]: Optimization results

        """
        optimizer = DataOptimizer()

        # Optimize each DataFrame
        optimized_sheets: dict[str, pl.DataFrame] = {}
        for sheet_name, df in test_data.items():
            optimized_df = optimizer.optimize_dataframe(df)
            optimized_sheets[sheet_name] = optimized_df

        # Calculate memory savings
        original_memory = sum(df.estimated_size("b") for df in test_data.values())
        optimized_memory = sum(df.estimated_size() for df in optimized_sheets.values())

        memory_savings = original_memory - optimized_memory
        savings_percentage = (
            (memory_savings / original_memory * 100) if original_memory > 0 else 0
        )

        return {
            "sheets_optimized": len(optimized_sheets),
            "memory_savings_mb": memory_savings / 1024 / 1024,
            "savings_percentage": savings_percentage,
        }


class TestScalability(unittest.TestCase):
    """Scalability testing scenarios."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.scalability_tester = ScalabilityTester()
        self.genomics_scalability = GenomicsAnalysisScalability()

    def test_generate_scalability_test_data(self) -> None:
        """Test generation of scalability test data."""
        # Test basic complexity
        basic_data = self.scalability_tester.generate_scalability_test_data(
            1000,
            "basic",
        )
        require_runtime_instance(basic_data, dict)
        if ("Detailed Table") not in (basic_data):
            raise AssertionError
        require_equal(len(basic_data["Detailed Table"]), 1000)

        # Test medium complexity
        medium_data = self.scalability_tester.generate_scalability_test_data(
            1000,
            "medium",
        )
        if ("Detailed Table") not in (medium_data):
            raise AssertionError
        if ("Labour Prices") not in (medium_data):
            raise AssertionError

        # Test complex complexity
        complex_data = self.scalability_tester.generate_scalability_test_data(
            1000,
            "complex",
        )
        if ("Detailed Table") not in (complex_data):
            raise AssertionError
        if ("PSA") not in (complex_data):
            raise AssertionError

    def test_run_scalability_test(self) -> None:
        """Test running scalability tests."""

        def simple_operation(test_data: dict[str, pl.DataFrame]) -> int:
            # Simple operation that works with any test data
            df = test_data.get("Detailed Table", pl.DataFrame())
            return len(df)

        sizes = [100, 500, 1000]
        results = self.scalability_tester.run_scalability_test(
            "simple_operation",
            simple_operation,
            sizes,
            "basic",
            iterations=2,
        )

        require_runtime_instance(results, list)
        if not ((len(results)) == (len(sizes))):
            raise AssertionError

        # Check results structure
        for result in results:
            if ("operation_name") not in (result):
                raise AssertionError
            if ("data_size") not in (result):
                raise AssertionError
            if ("mean_execution_time") not in (result):
                raise AssertionError
            if ("success_rate") not in (result):
                raise AssertionError
            if not ((result["operation_name"]) == ("simple_operation")):
                raise AssertionError

    def test_analyze_scaling_behavior(self) -> None:
        """Test scaling behavior analysis."""
        # Create mock results
        mock_results: list[Measurement] = [
            {"data_size": 100, "mean_execution_time": 0.1},
            {"data_size": 500, "mean_execution_time": 0.5},
            {"data_size": 1000, "mean_execution_time": 1.0},
        ]

        analysis = self.scalability_tester.analyze_scaling_behavior(mock_results)

        if "error" in analysis:
            raise AssertionError(analysis["error"])
        require_runtime_instance(analysis, dict)
        if ("scaling_behavior") not in (analysis):
            raise AssertionError
        if ("average_scaling_factor") not in (analysis):
            raise AssertionError

        # Should show linear or sub-linear scaling for this data
        if (analysis["scaling_behavior"]) not in (
            ["sub-linear (good)", "linear (acceptable)"]
        ):
            raise AssertionError

    def test_cost_driver_analysis_scalability(self) -> None:
        """Test scalability of cost driver analysis."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(
            1000,
            "basic",
        )

        # Test cost driver analysis
        result = self.genomics_scalability.test_cost_driver_analysis_scalability(
            test_data,
        )

        require_runtime_instance(result, dict)
        if ("cost_drivers_count") not in (result):
            raise AssertionError
        if not ((result["cost_drivers_count"]) >= (0)):
            raise AssertionError

    def test_data_loading_scalability(self) -> None:
        """Test scalability of data loading operations."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(
            1000,
            "complex",
        )

        # Test data loading
        result = self.genomics_scalability.test_data_loading_scalability(test_data)

        require_runtime_instance(result, dict)
        if ("sheets_loaded") not in (result):
            raise AssertionError
        if ("total_rows") not in (result):
            raise AssertionError
        if ("total_columns") not in (result):
            raise AssertionError
        if not ((result["sheets_loaded"]) > (0)):
            raise AssertionError
        if not ((result["total_rows"]) > (0)):
            raise AssertionError

    def test_data_optimization_scalability(self) -> None:
        """Test scalability of data optimization operations."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(
            10000,
            "basic",
        )

        # Test data optimization
        result = self.genomics_scalability.test_data_optimization_scalability(test_data)

        require_runtime_instance(result, dict)
        if ("sheets_optimized") not in (result):
            raise AssertionError
        if ("memory_savings_mb") not in (result):
            raise AssertionError
        if ("savings_percentage") not in (result):
            raise AssertionError
        if not ((result["sheets_optimized"]) >= (0)):
            raise AssertionError


class PerformanceBaselineEstablisher:
    """Establish performance baselines for different operations."""

    def __init__(self) -> None:
        """Initialize the baseline establisher."""
        self.scalability_tester = ScalabilityTester()
        self.genomics_scalability = GenomicsAnalysisScalability()

    def establish_baselines(self) -> dict[str, Baseline]:
        """Establish performance baselines.

        Returns:
            Dict[str, Dict[str, any]]: Performance baselines

        """
        baselines: dict[str, Baseline] = {}
        workloads = self.genomics_scalability

        # Define test scenarios
        scenarios: list[BenchmarkScenario] = [
            {
                "name": "cost_driver_analysis",
                "function": workloads.test_cost_driver_analysis_scalability,
                "sizes": [1000, 5000, 10000],
                "complexity": "basic",
            },
            {
                "name": "data_loading",
                "function": self.genomics_scalability.test_data_loading_scalability,
                "sizes": [1000, 5000, 10000],
                "complexity": "complex",
            },
            {
                "name": "data_optimization",
                "function": workloads.test_data_optimization_scalability,
                "sizes": [10000, 50000, 100000],
                "complexity": "basic",
            },
        ]

        # Run baseline tests
        for scenario in scenarios:
            logger.info("%s", f"Establishing baseline for {scenario['name']}...")
            results = self.scalability_tester.run_scalability_test(
                scenario["name"],
                scenario["function"],
                scenario["sizes"],
                scenario["complexity"],
                iterations=3,
            )

            analysis = self.scalability_tester.analyze_scaling_behavior(results)
            baselines[scenario["name"]] = {
                "results": results,
                "analysis": analysis,
            }

        return baselines

    def compare_against_baselines(
        self,
        current_results: list[ScalabilityResult],
        baselines: dict[str, Baseline],
    ) -> dict[str, BaselineComparison]:
        """Compare current results against established baselines.

        Args:
            current_results (List[Dict[str, any]]): Current test results
            baselines (Dict[str, Dict[str, any]]): Established baselines

        Returns:
            Dict[str, any]: Comparison results

        """
        comparisons: dict[str, BaselineComparison] = {}

        for operation_name, baseline_data in baselines.items():
            baseline_results = baseline_data["results"]
            if not baseline_results:
                continue

            # Find corresponding current results
            current_op_results = [
                r for r in current_results if r["operation_name"] == operation_name
            ]
            if not current_op_results:
                continue

            # Compare at similar data sizes
            for current_result in current_op_results:
                current_size = current_result["data_size"]

                # Find baseline result for similar size
                baseline_result = min(
                    baseline_results,
                    key=lambda x: abs(x["data_size"] - current_size),
                )

                if baseline_result:
                    time_regression = (
                        current_result["mean_execution_time"]
                        > baseline_result["mean_execution_time"] * 1.1  # 10% threshold
                    )

                    comparisons[operation_name] = {
                        "current_time": current_result["mean_execution_time"],
                        "baseline_time": baseline_result["mean_execution_time"],
                        "regression_detected": time_regression,
                        "time_difference": (
                            current_result["mean_execution_time"]
                            - baseline_result["mean_execution_time"]
                        ),
                    }

        return comparisons


# Example usage:
if __name__ == "__main__":
    # Create scalability tester
    scalability_tester = ScalabilityTester()
    genomics_scalability = GenomicsAnalysisScalability()

    # Define test operations
    def cost_driver_test(test_data: dict[str, pl.DataFrame]) -> object:
        """Run cost driver analysis on the scalability fixture."""
        return genomics_scalability.test_cost_driver_analysis_scalability(test_data)

    def data_loading_test(test_data: dict[str, pl.DataFrame]) -> object:
        """Load the detailed table from the scalability fixture."""
        return genomics_scalability.test_data_loading_scalability(test_data)

    # Run scalability tests
    logger.info("%s", "Running cost driver analysis scalability test...")
    cost_driver_results = scalability_tester.run_scalability_test(
        "cost_driver_analysis",
        cost_driver_test,
        sizes=[1000, 5000, 10000],
        complexity="basic",
        iterations=2,
    )

    logger.info("%s", "\nRunning data loading scalability test...")
    data_loading_results = scalability_tester.run_scalability_test(
        "data_loading",
        data_loading_test,
        sizes=[1000, 5000, 10000],
        complexity="complex",
        iterations=2,
    )

    # Analyze scaling behavior
    logger.info("%s", "\nAnalyzing cost driver analysis scaling behavior...")
    cost_driver_analysis = scalability_tester.analyze_scaling_behavior(
        cost_driver_results,
    )
    if "error" in cost_driver_analysis:
        raise RuntimeError(cost_driver_analysis["error"])
    logger.info("%s", f"Scaling behavior: {cost_driver_analysis['scaling_behavior']}")
    logger.info(
        "%s",
        f"Average scaling factor: {cost_driver_analysis['average_scaling_factor']:.2f}",
    )

    logger.info("%s", "\nAnalyzing data loading scaling behavior...")
    data_loading_analysis = scalability_tester.analyze_scaling_behavior(
        data_loading_results,
    )
    if "error" in data_loading_analysis:
        raise RuntimeError(data_loading_analysis["error"])
    logger.info("%s", f"Scaling behavior: {data_loading_analysis['scaling_behavior']}")
    logger.info(
        "%s",
        "Average scaling factor: "
        f"{data_loading_analysis['average_scaling_factor']:.2f}",
    )

    # Generate report
    report = scalability_tester.generate_scalability_report()
    logger.info("%s", f"\nGenerated {len(report)} test results")

    # Show summary
    logger.info("%s", "\nScalability Test Summary:")
    logger.info("%s", "=" * 50)
    for row in report.iter_rows(named=True):
        logger.info(
            "%s",
            f"{row['operation_name']:<25} {row['data_size']:<10} "
            f"{row['mean_execution_time']:<10.4f}s {row['mean_memory_usage']:<10.2f}MB",
        )


def test_failed_scalability_operation_is_not_successful() -> None:
    """Do not promote elapsed time from a failed callback into benchmark success."""

    def failure(_tables: dict[str, pl.DataFrame]) -> None:
        message = "synthetic benchmark failure"
        raise ValueError(message)

    result = ScalabilityTester().run_scalability_test(
        "failure",
        failure,
        [2],
        iterations=1,
    )
    if result[0]["success_rate"] != 0:
        raise AssertionError
