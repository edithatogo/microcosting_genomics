# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Benchmarking Analysis module for microcosting analysis.

This module provides functionality to perform benchmarking analysis
including comparison against published benchmarks, performance benchmarking,
and efficiency metrics evaluation.
"""

import logging
from pathlib import Path
from typing import Any
lazy from collections.abc import Mapping

import polars as pl

from .data_manager import DataManager
from .logging_config import get_logger
from .sensitivity_evidence import markdown_table

logger = get_logger(__name__)


class BenchmarkingAnalyzer:
    """Analyzer for performing Benchmarking Analysis."""

    def __init__(self, data_manager: DataManager) -> None:
        """Initialize the BenchmarkingAnalyzer.

        Args:
            data_manager: DataManager instance for accessing prepared data

        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def load_benchmark_data(self) -> dict[str, pl.DataFrame]:
        """Load benchmark data from prepared sheets.

        Returns:
            Dictionary of benchmark data sheets

        """
        self.logger.info("Loading benchmark data...")

        benchmark_sheets: dict[str, pl.DataFrame] = {}
        benchmark_sheet_names = [
            "Benchmarking",
            "benchmarking",
            "Published Benchmarks",
            "published_benchmarks",
            "Literature Review",
            "literature_review",
        ]

        for sheet_name in benchmark_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    benchmark_sheets[sheet_name] = df
                    self.logger.info("  Loaded %s with shape %s", sheet_name, df.shape)
                else:
                    self.logger.debug("  Could not load %s", sheet_name)
            except OSError, ValueError, pl.exceptions.PolarsError:
                self.logger.debug("  Error loading %s", sheet_name, exc_info=True)

        return benchmark_sheets

    def load_published_benchmarks(self) -> dict[str, dict[str, Any]]:
        """Load published benchmark data for comparison.

        Returns:
            Dictionary of published benchmark data

        """
        self.logger.info("Loading published benchmark data...")

        # These are example benchmarks from the literature
        # In a real implementation, this would be loaded from actual data sources
        return {
            "Panel Testing": {
                "cost_per_test": 1500.0,  # USD
                "turnaround_time": 5,  # days
                "throughput_per_day": 20,  # tests per day
                "accuracy": 0.95,  # 95% accuracy
                "source": "Smith et al., 2020",
            },
            "WES Testing": {
                "cost_per_test": 2500.0,  # USD
                "turnaround_time": 10,  # days
                "throughput_per_day": 15,  # tests per day
                "accuracy": 0.92,  # 92% accuracy
                "source": "Johnson et al., 2019",
            },
            "WGS Testing": {
                "cost_per_test": 4000.0,  # USD
                "turnaround_time": 18,  # days
                "throughput_per_day": 8,  # tests per day
                "accuracy": 0.90,  # 90% accuracy
                "source": "Brown et al., 2021",
            },
        }

    def compare_against_benchmarks(
        self,
        current_performance: Mapping[str, Mapping[str, float]],
        benchmarks: Mapping[str, Mapping[str, object]],
    ) -> pl.DataFrame:
        """Compare current performance against published benchmarks.

        Args:
            current_performance: Dictionary with current performance data by model
            benchmarks: Dictionary with published benchmark data

        Returns:
            DataFrame with benchmark comparison results

        """
        self.logger.info("Comparing performance against benchmarks...")

        results: list[dict[str, object]] = []
        metrics = (
            ("cost_per_test", "Cost per Test", -1),
            ("turnaround_time", "Turnaround Time", -1),
            ("throughput_per_day", "Throughput per Day", 1),
            ("accuracy", "Accuracy", 1),
        )
        for model_name, current_data in current_performance.items():
            benchmark_data = benchmarks.get(model_name)
            if benchmark_data is None:
                continue
            for key, label, direction in metrics:
                current = current_data.get(key, 0)
                benchmark = benchmark_data.get(key, 0)
                if not isinstance(benchmark, (int, float)):
                    message = f"Benchmark {key} for {model_name} must be numeric"
                    raise TypeError(message)
                ratio = current / benchmark if benchmark > 0 else 0
                performance = (
                    direction * (int(current > benchmark) - int(current < benchmark))
                    if benchmark > 0
                    else 0
                )
                results.append(
                    {
                        "Model": model_name,
                        "Metric": label,
                        "Current": current,
                        "Benchmark": benchmark,
                        "Ratio": ratio,
                        "Performance": performance,
                        "Source": benchmark_data.get("source", "N/A"),
                    },
                )

        return pl.DataFrame(results)

    def calculate_efficiency_metrics(
        self,
        observed_output: float,
        observed_input: float,
        best_practice_output: float,
        best_practice_input: float,
    ) -> dict[str, float]:
        """Calculate efficiency metrics relative to best practices.

        Args:
            observed_output: Observed output level
            observed_input: Observed input level
            best_practice_output: Best practice output level
            best_practice_input: Best practice input level

        Returns:
            Dictionary with efficiency metrics

        """
        self.logger.info("Calculating efficiency metrics...")

        # Technical efficiency = (Observed output / Best practice output) /
        #                        (Observed input / Best practice input)
        if observed_input > 0 and best_practice_input > 0 and best_practice_output > 0:
            technical_efficiency = (observed_output / best_practice_output) / (
                observed_input / best_practice_input
            )
        else:
            technical_efficiency = 0

        # Cost efficiency = Observed cost / Best practice cost
        observed_cost = observed_input  # Simplified assumption
        best_practice_cost = best_practice_input  # Simplified assumption
        cost_efficiency = (
            observed_cost / best_practice_cost if best_practice_cost > 0 else 0
        )

        # Express productivity per unit of input.
        observed_productivity = (
            observed_output / observed_input if observed_input > 0 else 0
        )
        best_practice_productivity = (
            best_practice_output / best_practice_input if best_practice_input > 0 else 0
        )

        return {
            "technical_efficiency": technical_efficiency,
            "cost_efficiency": cost_efficiency,
            "observed_productivity": observed_productivity,
            "best_practice_productivity": best_practice_productivity,
            "productivity_ratio": observed_productivity / best_practice_productivity
            if best_practice_productivity > 0
            else 0,
            "observed_output": observed_output,
            "observed_input": observed_input,
            "best_practice_output": best_practice_output,
            "best_practice_input": best_practice_input,
        }

    def benchmark_performance_over_time(
        self,
        historical_data: list[dict[str, Any]],
    ) -> pl.DataFrame:
        """Benchmark performance trends over time.

        Args:
            historical_data: List of historical performance data

        Returns:
            DataFrame with performance trends

        """
        self.logger.info("Benchmarking performance over time...")

        return pl.DataFrame(historical_data)

    def generate_benchmarking_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive benchmarking analysis report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        try:
            # Load benchmark data
            self.load_benchmark_data()

            # Load published benchmarks
            published_benchmarks = self.load_published_benchmarks()

            # Define current performance data (example values)
            current_performance = {
                "Panel Testing": {
                    "cost_per_test": 1800.0,
                    "turnaround_time": 7,  # days
                    "throughput_per_day": 25,  # tests per day
                    "accuracy": 0.94,  # 94% accuracy
                },
                "WES Testing": {
                    "cost_per_test": 3000.0,
                    "turnaround_time": 14,  # days
                    "throughput_per_day": 12,  # tests per day
                    "accuracy": 0.91,  # 91% accuracy
                },
                "WGS Testing": {
                    "cost_per_test": 4500.0,
                    "turnaround_time": 21,  # days
                    "throughput_per_day": 6,  # tests per day
                    "accuracy": 0.89,  # 89% accuracy
                },
            }

            # Compare against benchmarks
            benchmark_comparison = self.compare_against_benchmarks(
                current_performance,
                published_benchmarks,
            )

            # Calculate efficiency metrics
            efficiency_metrics = self.calculate_efficiency_metrics(
                observed_output=1000,
                observed_input=2000000,
                best_practice_output=1200,
                best_practice_input=1800000,
            )

            # Generate report
            report: list[str] = []
            report.append("# Benchmarking Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append(
                "This report presents the results of benchmarking analysis, "
                "comparing current performance "
                "against published benchmarks and evaluating efficiency metrics.\n",
            )

            report.append("## Benchmark Comparison\n")
            report.append(
                "Comparison of current performance against published benchmarks:\n",
            )
            report.append(markdown_table(benchmark_comparison))
            report.append("\n")

            report.append("## Efficiency Metrics\n")
            report.append(
                (
                    f"Technical efficiency: "
                    f"{efficiency_metrics['technical_efficiency']:.4f}\n"
                ),
            )
            report.append(
                f"Cost efficiency: {efficiency_metrics['cost_efficiency']:.4f}\n",
            )
            report.append(
                (
                    f"Observed productivity: "
                    f"{efficiency_metrics['observed_productivity']:.8f}\n"
                ),
            )
            report.append(
                (
                    f"Best practice productivity: "
                    f"{efficiency_metrics['best_practice_productivity']:.8f}\n"
                ),
            )
            report.append(
                f"Productivity ratio: {efficiency_metrics['productivity_ratio']:.4f}\n",
            )
            report.append(f"Observed output: {efficiency_metrics['observed_output']}\n")
            report.append(f"Observed input: {efficiency_metrics['observed_input']}\n")
            report.append(
                f"Best practice output: {efficiency_metrics['best_practice_output']}\n",
            )
            report.append(
                f"Best practice input: {efficiency_metrics['best_practice_input']}\n",
            )

            report.append("\n## Key Findings\n")
            report.append(
                (
                    "- Benchmark comparison identifies areas where "
                    "performance exceeds or lags behind published benchmarks\n"
                ),
            )
            report.append(
                (
                    "- Efficiency metrics quantify "
                    "performance relative to best practices\n"
                ),
            )
            report.append(
                (
                    "- Results can inform process improvement "
                    "initiatives and resource allocation decisions\n"
                ),
            )
            report.append(
                (
                    "- Regular benchmarking enables tracking "
                    "of performance improvements over time\n"
                ),
            )

            report_str = "\n".join(report)

            if output_file:
                with Path(output_file).open("w") as f:
                    f.write(report_str)

        except Exception:
            self.logger.exception("Error generating benchmarking report")
            raise
        else:
            return report_str


def main() -> None:
    """Run a demonstration of the benchmarking analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = BenchmarkingAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_benchmarking_report()
        logger.info("%s", report)

    except Exception:
        logger.exception("Error in benchmarking analysis")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
