# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Advanced scenario modeling tools with sophisticated comparison features."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
lazy from collections.abc import Sequence
lazy from decimal import Decimal

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
lazy from matplotlib.figure import Figure

from .scenario_modeling import Scenario, ScenarioManager
from .sensitivity_evidence import markdown_table
lazy from .dsa_analysis import TornadoPlotter

logger = logging.getLogger(__name__)

type _SensitivityTotal = int | float | Decimal


@dataclass
class AdvancedScenario(Scenario):
    """Enhanced scenario with more sophisticated parameter adjustments."""

    sensitivity_parameters: dict[str, tuple[float, float]] | None = (
        None  # parameter -> (min, max) for sensitivity analysis
    )
    probability_distributions: dict[str, dict[str, Any]] | None = (
        None  # parameter -> distribution info
    )
    dependencies: dict[str, list[str]] | None = (
        None  # parameter -> list of dependent parameters
    )


class AdvancedScenarioManager(ScenarioManager):
    """Enhanced scenario manager with advanced comparison and analysis features."""

    def __init__(
        self,
        base_data: dict[str, pl.DataFrame],
        *,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Initialize the advanced scenario manager with base data.

        Args:
            base_data: Dictionary of DataFrames representing the base case data
            rng: Optional generator for reproducible probabilistic scenarios

        """
        super().__init__(base_data)
        self.rng = rng if rng is not None else np.random.default_rng()
        self.advanced_scenarios: dict[str, AdvancedScenario] = {}
        self.sensitivity_results: dict[str, dict[str, list[_SensitivityTotal]]] = {}
        self.probabilistic_results: dict[str, list[dict[str, pl.DataFrame]]] = {}

    def add_advanced_scenario(self, scenario: AdvancedScenario) -> None:
        """Add an advanced scenario to the manager.

        Args:
            scenario: AdvancedScenario object to add

        """
        self.advanced_scenarios[scenario.name] = scenario
        # Also add to parent class scenarios dict for compatibility
        self.scenarios[scenario.name] = scenario

    def run_sensitivity_analysis(
        self,
        scenario_name: str,
        parameter: str,
        range_min: float,
        range_max: float,
        steps: int = 10,
    ) -> dict[str, list[float] | dict[str, list[_SensitivityTotal]]]:
        """Run sensitivity analysis for a specific parameter.

        Args:
            scenario_name: Name of the scenario to analyze
            parameter: Parameter to vary
            range_min: Minimum value for the parameter
            range_max: Maximum value for the parameter
            steps: Number of steps to test

        Returns:
            Dictionary with parameter values and corresponding results

        """
        if scenario_name not in self.advanced_scenarios:
            message = f"Advanced scenario '{scenario_name}' not found"
            raise ValueError(message)

        scenario = self.advanced_scenarios[scenario_name]
        parameter_values = np.linspace(range_min, range_max, steps)
        results: dict[str, list[_SensitivityTotal]] = {}

        # Initialize results for each table
        for table_name in self.base_data:
            results[table_name] = []

        # Run analysis for each parameter value
        for param_value in parameter_values:
            # Create a modified scenario with the current parameter value
            modified_adjustments = scenario.adjustments.copy()
            modified_adjustments[parameter] = param_value

            modified_scenario = Scenario(
                name=f"{scenario_name}_sensitivity_{param_value:.3f}",
                description=(
                    f"{scenario.description} - sensitivity "
                    f"analysis for {parameter}={param_value:.3f}"
                ),
                parameters={**scenario.parameters, parameter: param_value},
                adjustments=modified_adjustments,
            )

            self.add_scenario(modified_scenario)

            # Run the modified scenario
            scenario_results: dict[str, pl.DataFrame] = {}
            for table_name in self.base_data:
                scenario_results[table_name] = self.apply_scenario(
                    modified_scenario.name,
                    table_name,
                )
                results[table_name].append(
                    scenario_results[table_name][parameter].sum()
                    if parameter in scenario_results[table_name].columns
                    else 0,
                )

        self.sensitivity_results[scenario_name] = results
        return {parameter: list(parameter_values), "results": results}

    def run_probabilistic_analysis(
        self,
        scenario_name: str,
        iterations: int = 1000,
    ) -> list[dict[str, pl.DataFrame]]:
        """Run probabilistic analysis using Monte Carlo simulation.

        Args:
            scenario_name: Name of the scenario to analyze
            iterations: Number of Monte Carlo iterations

        Returns:
            Dictionary with probabilistic results

        """
        if scenario_name not in self.advanced_scenarios:
            message = f"Advanced scenario '{scenario_name}' not found"
            raise ValueError(message)

        scenario = self.advanced_scenarios[scenario_name]
        results: list[dict[str, pl.DataFrame]] = []

        # Run Monte Carlo simulation
        for i in range(iterations):
            # Sample from probability distributions
            sampled_parameters = {}
            modified_adjustments = scenario.adjustments.copy()

            if scenario.probability_distributions:
                for param, dist_info in scenario.probability_distributions.items():
                    dist_type = dist_info.get("type", "normal")
                    if dist_type == "normal":
                        mean = dist_info.get("mean", 0)
                        std = dist_info.get("std", 1)
                        sampled_value = self.rng.normal(mean, std)
                    elif dist_type == "uniform":
                        low = dist_info.get("low", 0)
                        high = dist_info.get("high", 1)
                        sampled_value = self.rng.uniform(low, high)
                    else:
                        # Default to normal distribution
                        sampled_value = self.rng.normal(0, 1)

                    sampled_parameters[param] = sampled_value
                    modified_adjustments[param] = sampled_value

            # Create modified scenario
            modified_scenario = Scenario(
                name=f"{scenario_name}_prob_{i}",
                description=f"{scenario.description} - probabilistic iteration {i}",
                parameters={**scenario.parameters, **sampled_parameters},
                adjustments=modified_adjustments,
            )

            self.add_scenario(modified_scenario)

            # Run the modified scenario
            iteration_results: dict[str, pl.DataFrame] = {}
            for table_name in self.base_data:
                iteration_results[table_name] = self.apply_scenario(
                    modified_scenario.name,
                    table_name,
                )

            results.append(iteration_results)

        self.probabilistic_results[scenario_name] = results
        return results

    def compare_scenarios_detailed(
        self,
        scenario_names: list[str],
        table_name: str,
        metrics: list[str] | None = None,
    ) -> dict[str, pl.DataFrame]:
        """Perform detailed comparison of scenarios with multiple metrics.

        Args:
            scenario_names: List of scenario names to compare
            table_name: Name of the table to compare
            metrics: List of metrics to calculate (mean, std, min, max, etc.)

        Returns:
            Dictionary with detailed comparison results

        """
        if metrics is None:
            metrics = [
                "mean",
                "std",
                "min",
                "max",
                "median",
                "percentile_25",
                "percentile_75",
            ]

        # Check that all scenarios exist
        for name in scenario_names:
            if name not in self.scenarios and name not in self.advanced_scenarios:
                message = f"Scenario '{name}' not found"
                raise ValueError(message)

        # Run scenarios that haven't been run yet
        for name in scenario_names:
            if name not in self.results:
                self.run_scenario_analysis(name)

        # Get base data for comparison
        base_df = self.base_data[table_name].with_columns(
            pl.selectors.float().fill_nan(None),
        )

        # Select numeric columns
        numeric_columns = [
            name for name, dtype in base_df.schema.items() if dtype.is_numeric()
        ]

        # Create detailed comparison results
        comparison_results: dict[str, pl.DataFrame] = {}

        for column in numeric_columns:
            data = {
                "Base Case": [
                    base_df[column].mean(),
                    base_df[column].std(),
                    base_df[column].min(),
                    base_df[column].max(),
                    base_df[column].median(),
                    base_df[column].quantile(0.25, interpolation="linear"),
                    base_df[column].quantile(0.75, interpolation="linear"),
                ],
            }

            for scenario_name in scenario_names:
                scenario_df = self.results[scenario_name][table_name].with_columns(
                    pl.selectors.float().fill_nan(None),
                )
                if column in scenario_df.columns:
                    data[scenario_name] = [
                        scenario_df[column].mean(),
                        scenario_df[column].std(),
                        scenario_df[column].min(),
                        scenario_df[column].max(),
                        scenario_df[column].median(),
                        scenario_df[column].quantile(0.25, interpolation="linear"),
                        scenario_df[column].quantile(0.75, interpolation="linear"),
                    ]
                else:
                    data[scenario_name] = [0] * len(metrics)

            comparison_results[column] = pl.DataFrame(
                data,
                schema=None,
            ).insert_column(
                0,
                pl.Series(
                    "Metric",
                    [
                        "Mean",
                        "Std Dev",
                        "Min",
                        "Max",
                        "Median",
                        "25th Percentile",
                        "75th Percentile",
                    ],
                ),
            )

        return comparison_results

    def generate_tornado_chart(
        self,
        scenario_name: str,
        table_name: str,
        parameter_changes: dict[str, tuple[float, float]],
        base_column: str,
    ) -> Figure:
        """Generate a tornado chart for sensitivity analysis.

        Args:
            scenario_name: Name of the base scenario
            table_name: Name of the table to analyze
            parameter_changes: Dictionary of parameters and their (low, high) values
            base_column: Column to measure sensitivity for

        Returns:
            Matplotlib figure with tornado chart

        """
        if scenario_name not in self.scenarios:
            message = f"Scenario '{scenario_name}' not found"
            raise ValueError(message)

        # Get base case value
        base_df = self.base_data[table_name].with_columns(
            pl.selectors.float().fill_nan(None),
        )
        base_value = (
            float(base_df[base_column].sum()) if base_column in base_df.columns else 0.0
        )

        # Calculate sensitivity for each parameter
        sensitivities: list[float] = []
        parameters: list[str] = []

        for param, (low_val, high_val) in parameter_changes.items():
            adjustments = self.scenarios[scenario_name].adjustments
            low_df = self._apply_adjustments(base_df, {**adjustments, param: low_val})
            high_df = self._apply_adjustments(base_df, {**adjustments, param: high_val})
            low_value = (
                float(low_df[base_column].sum())
                if base_column in low_df.columns
                else 0.0
            )
            high_value = (
                float(high_df[base_column].sum())
                if base_column in high_df.columns
                else 0.0
            )

            # Calculate impact
            low_impact = abs(base_value - low_value)
            high_impact = abs(base_value - high_value)
            max_impact = max(low_impact, high_impact)

            sensitivities.append(max_impact)
            parameters.append(param)

        # Sort by impact
        sorted_indices = [int(index) for index in np.argsort(sensitivities)]
        sorted_sensitivities = [sensitivities[index] for index in sorted_indices]
        sorted_parameters = [parameters[index] for index in sorted_indices]

        # Create tornado chart
        plotter = cast("TornadoPlotter", plt)
        fig, ax = plotter.subplots(figsize=(10, max(6, len(parameters) * 0.5)))
        y_pos = range(len(parameters))
        ax.barh(y_pos, sorted_sensitivities, color="skyblue")
        ax.set_yticks(y_pos, labels=sorted_parameters)
        ax.set_xlabel(f"Impact on {base_column}")
        ax.set_title(f"Sensitivity Analysis Tornado Chart for {scenario_name}")
        ax.grid(visible=True, alpha=0.3)

        return fig

    def export_scenario_results(
        self,
        scenario_name: str,
        output_dir: str,
        formats: Sequence[str] = ("csv", "json"),
    ) -> None:
        """Export scenario results in multiple formats.

        Args:
            scenario_name: Name of the scenario to export
            output_dir: Directory to save results
            formats: Formats to export (csv, json, parquet)

        """
        if scenario_name not in self.results:
            message = (
                f"Scenario '{scenario_name}' results not found. Run analysis first."
            )
            raise ValueError(
                message,
            )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        scenario_results = self.results[scenario_name]

        for format_type in formats:
            format_dir = output_path / format_type
            format_dir.mkdir(exist_ok=True)

            for table_name, df in scenario_results.items():
                filename = f"{scenario_name}_{table_name}"

                if format_type == "csv":
                    df.write_csv(format_dir / f"{filename}.csv")
                elif format_type == "json":
                    df.write_json(format_dir / f"{filename}.json")
                elif format_type == "parquet":
                    df.write_parquet(format_dir / f"{filename}.parquet")

    def generate_advanced_report(
        self,
        scenario_names: list[str],
        output_file: str | None = None,
    ) -> str:
        """Generate an advanced report with detailed scenario analysis.

        Args:
            scenario_names: List of scenario names to include in report
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        report: list[str] = []
        report.append("# Advanced Scenario Analysis Report\n")
        generated_at = datetime.now(UTC).astimezone()
        report.append(f"Generated on: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("\n## Scenario Definitions\n")

        # Add scenario definitions
        for name in scenario_names:
            if name in self.scenarios:
                scenario = self.scenarios[name]
                report.append(f"### {scenario.name}\n")
                report.append(f"**Description:** {scenario.description}\n")
                report.append("**Parameters:**\n")
                for param, value in scenario.parameters.items():
                    report.append(f"  - {param}: {value}\n")
                report.append("**Adjustments:**\n")
                for column, adjustment in scenario.adjustments.items():
                    report.append(f"  - {column}: {adjustment}\n")
                report.append("\n")

        report.extend(self._detailed_comparisons(scenario_names))

        # Add probabilistic analysis results if available
        report.append("## Probabilistic Analysis Results\n")
        for scenario_name in scenario_names:
            if scenario_name in self.probabilistic_results:
                report.append(f"### {scenario_name}\n")
                results = self.probabilistic_results[scenario_name]
                report.append(f"Monte Carlo iterations: {len(results)}\n")
                # Add summary statistics
                report.append("Summary statistics from probabilistic analysis:\n")
                # This would be expanded with actual statistics
                report.append(
                    "(Detailed probabilistic results available in raw data)\n\n",
                )
            else:
                report.append(f"### {scenario_name}\n")
                report.append("No probabilistic analysis data available.\n\n")

        report_str = "\n".join(report)

        if output_file:
            with Path(output_file).open("w") as f:
                f.write(report_str)

        return report_str

    def _detailed_comparisons(self, scenario_names: list[str]) -> list[str]:
        sections = ["## Detailed Scenario Comparisons\n"]
        for table_name in self.base_data:
            sections.append(f"### {table_name}\n")
            try:
                comparison = self.compare_scenarios_detailed(scenario_names, table_name)
                for column, frame in comparison.items():
                    sections.extend((f"#### {column}\n", markdown_table(frame), "\n"))
            except (
                KeyError,
                ValueError,
                TypeError,
                pl.exceptions.PolarsError,
            ) as error:
                sections.append(
                    f"Error in detailed comparison for {table_name}: {error}\n",
                )
        return sections


def create_advanced_scenarios() -> dict[str, AdvancedScenario]:
    """Create advanced scenarios with sophisticated parameter adjustments.

    Returns:
        Dictionary of advanced scenarios

    """
    scenarios: dict[str, AdvancedScenario] = {}

    # Advanced inflation scenario with sensitivity analysis
    scenarios["advanced_inflation"] = AdvancedScenario(
        name="advanced_inflation",
        description=(
            "Advanced inflation scenario with sensitivity and probabilistic analysis"
        ),
        parameters={"inflation_rate": 0.05},
        adjustments={
            "unit_cost_aud_per_unit": 1.05,
            "price_aud_per_unit": 1.05,
            "hourly_rate_aud": 1.05,
        },
        sensitivity_parameters={
            "inflation_rate": (0.01, 0.15),  # 1% to 15% inflation
        },
        probability_distributions={
            "inflation_rate": {
                "type": "normal",
                "mean": 0.05,
                "std": 0.02,
            },
        },
    )

    # Advanced cost reduction scenario
    scenarios["advanced_cost_reduction"] = AdvancedScenario(
        name="advanced_cost_reduction",
        description="Advanced cost reduction scenario with dependencies",
        parameters={"reduction_rate": 0.10},
        adjustments={
            "unit_cost_aud_per_unit": 0.90,
            "price_aud_per_unit": 0.90,
            "hourly_rate_aud": 0.90,
        },
        dependencies={
            "unit_cost_aud_per_unit": ["price_aud_per_unit", "hourly_rate_aud"],
            "price_aud_per_unit": ["unit_cost_aud_per_unit"],
            "hourly_rate_aud": ["unit_cost_aud_per_unit"],
        },
    )

    # Advanced throughput scenario with probabilistic analysis
    scenarios["advanced_throughput"] = AdvancedScenario(
        name="advanced_throughput",
        description="Advanced throughput scenario with probabilistic analysis",
        parameters={"throughput_increase": 0.50},
        adjustments={
            "Equipment Unit Cost": 0.67,  # 1/(1+0.50)
            "Equipment Price": 0.67,
        },
        probability_distributions={
            "throughput_increase": {
                "type": "uniform",
                "low": 0.2,
                "high": 0.8,
            },
        },
    )

    return scenarios


# Example usage function
def example_usage() -> None:
    """Demonstrate the advanced scenario modeling tools."""
    logger.info("%s", "Loading data for advanced scenario analysis...")

    # This would typically load actual data
    # For demonstration, we'll create sample data
    sample_data = {
        "detailed_table": pl.DataFrame(
            {
                "Step": ["A", "B", "C"],
                "Unit Cost": [100.0, 200.0, 150.0],
                "Price": [120.0, 220.0, 170.0],
                "Hours": [2.0, 3.0, 1.5],
            },
        ),
        "labor_prices": pl.DataFrame(
            {
                "Category": ["Tech", "Manager", "Assistant"],
                "Hourly Rate": [50.0, 80.0, 30.0],
            },
        ),
    }

    # Create advanced scenario manager
    scenario_manager = AdvancedScenarioManager(sample_data)

    # Add advanced scenarios
    advanced_scenarios = create_advanced_scenarios()
    for scenario in advanced_scenarios.values():
        scenario_manager.add_advanced_scenario(scenario)

    # Run a scenario analysis
    logger.info("%s", "Running advanced inflation scenario...")
    scenario_manager.run_scenario_analysis("advanced_inflation")

    # Run sensitivity analysis
    logger.info("%s", "Running sensitivity analysis...")
    try:
        scenario_manager.run_sensitivity_analysis(
            "advanced_inflation",
            "Unit Cost",
            0.8,
            1.2,
            5,
        )
        logger.info("%s", "Sensitivity analysis completed")
    except KeyError, ValueError, TypeError, pl.exceptions.PolarsError:
        logger.exception("Error in sensitivity analysis")

    # Compare scenarios with detailed metrics
    logger.info("%s", "Comparing scenarios with detailed metrics...")
    try:
        detailed_comparison = scenario_manager.compare_scenarios_detailed(
            ["advanced_inflation", "advanced_cost_reduction"],
            "detailed_table",
        )
        logger.info("%s", "Detailed comparison completed")
        for column, df in detailed_comparison.items():
            logger.info("%s", f"\n{column}:")
            logger.info("%s", df)
    except KeyError, ValueError, TypeError, pl.exceptions.PolarsError:
        logger.exception("Error in detailed comparison")

    # Generate advanced report
    logger.info("%s", "Generating advanced report...")
    try:
        report = scenario_manager.generate_advanced_report(
            ["advanced_inflation", "advanced_cost_reduction", "advanced_throughput"],
        )
        logger.info("%s", "Advanced report generated")
        logger.info("%s", report[:500])  # Print first 500 characters
    except OSError, ValueError, TypeError, pl.exceptions.PolarsError:
        logger.exception("Error generating advanced report")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
