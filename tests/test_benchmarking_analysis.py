# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Benchmarking Analysis module."""

import unittest
from unittest.mock import Mock

import polars as pl

from genomics_microcosting.benchmarking_analysis import BenchmarkingAnalyzer
from genomics_microcosting.data_manager import DataManager
from tests.checks import (
    require,
    require_equal,
    require_keys,
    require_rounded_equal,
    require_runtime_instance,
)


class TestBenchmarkingAnalyzer(unittest.TestCase):
    """Test cases for the BenchmarkingAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BenchmarkingAnalyzer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test BenchmarkingAnalyzer initialization."""
        require_runtime_instance(self.analyzer, BenchmarkingAnalyzer)
        if not ((self.analyzer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_load_benchmark_data(self) -> None:
        """Test loading benchmark data."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None

        result = self.analyzer.load_benchmark_data()
        require_runtime_instance(result, dict)
        # Should return an empty dict since all loads return None
        if not ((len(result)) == (0)):
            raise AssertionError

    def test_load_published_benchmarks(self) -> None:
        """Test loading published benchmark data."""
        result = self.analyzer.load_published_benchmarks()

        require_runtime_instance(result, dict)
        if ("Panel Testing") not in (result):
            raise AssertionError
        if ("WES Testing") not in (result):
            raise AssertionError
        if ("WGS Testing") not in (result):
            raise AssertionError

        # Check that each benchmark has the expected keys
        for benchmark_data in result.values():
            if ("cost_per_test") not in (benchmark_data):
                raise AssertionError
            if ("turnaround_time") not in (benchmark_data):
                raise AssertionError
            if ("throughput_per_day") not in (benchmark_data):
                raise AssertionError
            if ("accuracy") not in (benchmark_data):
                raise AssertionError
            if ("source") not in (benchmark_data):
                raise AssertionError

    def test_compare_against_benchmarks(self) -> None:
        """Test comparison against benchmarks."""
        expected_cost_ratio = 1.2
        expected_turnaround_ratio = 1.4
        expected_throughput_ratio = 1.25
        current_performance = {
            "Panel Testing": {
                "cost_per_test": 1800.0,
                "turnaround_time": 7,
                "throughput_per_day": 25,
                "accuracy": 0.94,
            },
        }

        benchmarks = {
            "Panel Testing": {
                "cost_per_test": 1500.0,
                "turnaround_time": 5,
                "throughput_per_day": 20,
                "accuracy": 0.95,
                "source": "Smith et al., 2020",
            },
        }

        result = self.analyzer.compare_against_benchmarks(
            current_performance,
            benchmarks,
        )

        require_runtime_instance(result, pl.DataFrame)
        require(condition=len(result) > 0)
        require_keys(result.columns, ("Model",))
        require_keys(result.columns, ("Metric",))
        require_keys(result.columns, ("Current",))
        require_keys(result.columns, ("Benchmark",))
        require_keys(result.columns, ("Ratio",))
        require_keys(result.columns, ("Performance",))
        require_keys(result.columns, ("Source",))

        # Check that we have 4 rows for the 4 metrics
        panel_rows = result.filter(pl.col("Model") == "Panel Testing")
        require_equal(len(panel_rows), 4)

        # Check specific calculations
        cost_row = panel_rows.filter(pl.col("Metric") == "Cost per Test").row(
            0,
            named=True,
        )
        require_equal(cost_row["Current"], 1800.0)
        require_equal(cost_row["Benchmark"], 1500.0)
        require_equal(cost_row["Ratio"], expected_cost_ratio)  # 1800/1500
        require_equal(cost_row["Performance"], -1)  # Worse performance (higher cost)

        turnaround_row = panel_rows.filter(pl.col("Metric") == "Turnaround Time").row(
            0,
            named=True,
        )
        require_equal(turnaround_row["Current"], 7)
        require_equal(turnaround_row["Benchmark"], 5)
        require_equal(turnaround_row["Ratio"], expected_turnaround_ratio)  # 7/5
        require_equal(
            turnaround_row["Performance"],
            -1,
        )  # Worse performance (longer time)

        throughput_row = panel_rows.filter(
            pl.col("Metric") == "Throughput per Day",
        ).row(0, named=True)
        require_equal(throughput_row["Current"], 25)
        require_equal(throughput_row["Benchmark"], 20)
        require_equal(throughput_row["Ratio"], expected_throughput_ratio)  # 25/20
        require_equal(
            throughput_row["Performance"],
            1,
        )  # Better performance (higher throughput)

        accuracy_row = panel_rows.filter(pl.col("Metric") == "Accuracy").row(
            0,
            named=True,
        )
        require_equal(accuracy_row["Current"], 0.94)
        require_equal(accuracy_row["Benchmark"], 0.95)
        require_rounded_equal(accuracy_row["Ratio"], 0.989, places=3)  # 0.94/0.95
        require_equal(
            accuracy_row["Performance"],
            -1,
        )  # Worse performance (lower accuracy)

    def test_calculate_efficiency_metrics(self) -> None:
        """Test efficiency metrics calculation."""
        result = self.analyzer.calculate_efficiency_metrics(
            observed_output=1000,
            observed_input=2000000,
            best_practice_output=1200,
            best_practice_input=1800000,
        )

        require_runtime_instance(result, dict)
        if ("technical_efficiency") not in (result):
            raise AssertionError
        if ("cost_efficiency") not in (result):
            raise AssertionError
        if ("observed_productivity") not in (result):
            raise AssertionError
        if ("best_practice_productivity") not in (result):
            raise AssertionError
        if ("productivity_ratio") not in (result):
            raise AssertionError
        if ("observed_output") not in (result):
            raise AssertionError
        if ("observed_input") not in (result):
            raise AssertionError
        if ("best_practice_output") not in (result):
            raise AssertionError
        if ("best_practice_input") not in (result):
            raise AssertionError

        # Check calculations
        # Technical efficiency = (Observed output / Best practice output) /
        #                        (Observed input / Best practice input)
        # = (1000 / 1200) / (2000000 / 1800000) = (0.8333) / (1.1111) = 0.75
        require_rounded_equal(result["technical_efficiency"], 0.75, places=4)

        # Cost efficiency = Observed cost / Best practice cost
        # = 2000000 / 1800000 = 1.1111
        require_rounded_equal(result["cost_efficiency"], 1.1111, places=4)

        # Observed productivity = 1000 / 2000000 = 0.0005
        require_rounded_equal(result["observed_productivity"], 0.0005, places=8)

        # Best practice productivity = 1200 / 1800000 = 0.0006667
        require_rounded_equal(
            result["best_practice_productivity"],
            0.0006666666666666666,
            places=10,
        )

        # Productivity ratio = 0.0005 / (1200/1800000) = 0.75
        require_rounded_equal(result["productivity_ratio"], 0.75, places=4)

    def test_benchmark_performance_over_time(self) -> None:
        """Test benchmarking performance over time."""
        historical_data = [
            {"date": "2023-01-01", "tests_completed": 800, "total_cost": 1600000},
            {"date": "2023-02-01", "tests_completed": 900, "total_cost": 1700000},
            {"date": "2023-03-01", "tests_completed": 1000, "total_cost": 1800000},
        ]

        result = self.analyzer.benchmark_performance_over_time(historical_data)

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 3)
        if ("date") not in (result.columns):
            raise AssertionError
        if ("tests_completed") not in (result.columns):
            raise AssertionError
        if ("total_cost") not in (result.columns):
            raise AssertionError

    def test_generate_benchmarking_report(self) -> None:
        """Test benchmarking report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None

        # Generate report
        report = self.analyzer.generate_benchmarking_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Benchmarking Analysis") not in (report):
            raise AssertionError
        if ("Benchmark Comparison") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
