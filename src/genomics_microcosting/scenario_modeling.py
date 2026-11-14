# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Scenario modeling tools for what-if analysis in microcosting."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
lazy from decimal import Decimal

import polars as pl

from .sensitivity_evidence import markdown_table

logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    """Represents a scenario with specific parameter adjustments."""

    name: str
    description: str
    parameters: dict[str, Any]
    adjustments: dict[str, float]  # column -> multiplier or absolute value


class ScenarioManager:
    """Manages scenario creation, comparison, and analysis."""

    def __init__(self, base_data: dict[str, pl.DataFrame]) -> None:
        """Initialize the scenario manager with base data.

        Args:
            base_data: Dictionary of DataFrames representing the base case data

        """
        self.base_data = base_data
        self.scenarios: dict[str, Scenario] = {}
        self.results: dict[str, dict[str, pl.DataFrame]] = {}

    def add_scenario(self, scenario: Scenario) -> None:
        """Add a scenario to the manager.

        Args:
            scenario: Scenario object to add

        """
        self.scenarios[scenario.name] = scenario

    def add_scenario_from_dict(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        adjustments: dict[str, float],
    ) -> None:
        """Add a scenario from dictionary parameters.

        Args:
            name: Name of the scenario
            description: Description of the scenario
            parameters: Parameters for the scenario
            adjustments: Column adjustments for the scenario

        """
        scenario = Scenario(name, description, parameters, adjustments)
        self.add_scenario(scenario)

    def apply_scenario(self, scenario_name: str, table_name: str) -> pl.DataFrame:
        """Apply a scenario to a specific table.

        Args:
            scenario_name: Name of the scenario to apply
            table_name: Name of the table to apply the scenario to

        Returns:
            DataFrame with scenario adjustments applied

        """
        if scenario_name not in self.scenarios:
            message = f"Scenario '{scenario_name}' not found"
            raise ValueError(message)

        if table_name not in self.base_data:
            message = f"Table '{table_name}' not found in base data"
            raise ValueError(message)

        return self._apply_adjustments(
            self.base_data[table_name],
            self.scenarios[scenario_name].adjustments,
        )

    @staticmethod
    def _apply_adjustments(
        frame: pl.DataFrame,
        adjustments: dict[str, float],
    ) -> pl.DataFrame:
        base_df = frame.clone()

        # Apply adjustments
        for column, adjustment in adjustments.items():
            if column in base_df.columns:
                # If adjustment is > 1, treat as multiplier
                # If adjustment is <= 1, treat as absolute value (if positive)
                if adjustment > 1 or adjustment < 0:
                    base_df = base_df.with_columns(
                        (pl.col(column) * adjustment).alias(column),
                    )
                else:
                    base_df = base_df.with_columns(pl.lit(adjustment).alias(column))

        return base_df

    def run_scenario_analysis(self, scenario_name: str) -> dict[str, pl.DataFrame]:
        """Run analysis for a specific scenario across all tables.

        Args:
            scenario_name: Name of the scenario to run

        Returns:
            Dictionary of DataFrames with scenario applied to each table

        """
        if scenario_name not in self.scenarios:
            message = f"Scenario '{scenario_name}' not found"
            raise ValueError(message)

        results: dict[str, pl.DataFrame] = {}
        for table_name in self.base_data:
            results[table_name] = self.apply_scenario(scenario_name, table_name)

        self.results[scenario_name] = results
        return results

    def compare_scenarios(
        self,
        scenario_names: list[str],
        table_name: str,
        columns: list[str] | None = None,
    ) -> pl.DataFrame:
        """Compare multiple scenarios for a specific table.

        Args:
            scenario_names: List of scenario names to compare
            table_name: Name of the table to compare
            columns: Specific columns to compare (if None, compare all numeric columns)

        Returns:
            DataFrame with scenario comparisons

        """
        # Check that all scenarios exist
        for name in scenario_names:
            if name not in self.scenarios:
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

        # Determine columns to compare
        if columns is None:
            # Select numeric columns
            columns = [
                name for name, dtype in base_df.schema.items() if dtype.is_numeric()
            ]

        # Create comparison DataFrame
        comparison_data: list[dict[str, str | int | float | Decimal]] = []
        for column in columns:
            if column in base_df.columns:
                row: dict[str, str | int | float | Decimal] = {
                    "Column": column,
                    "Base Case": base_df[column].sum(),
                }
                for scenario_name in scenario_names:
                    scenario_df = self.results[scenario_name][table_name].with_columns(
                        pl.selectors.float().fill_nan(None),
                    )
                    if column in scenario_df.columns:
                        row[scenario_name] = scenario_df[column].sum()
                    else:
                        row[scenario_name] = 0
                comparison_data.append(row)

        return pl.DataFrame(comparison_data)

    def generate_scenario_report(
        self,
        scenario_names: list[str],
        output_file: str | None = None,
    ) -> str:
        """Generate a report comparing multiple scenarios.

        Args:
            scenario_names: List of scenario names to compare
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        report: list[str] = []
        report.append("# Scenario Analysis Report\n")
        report.append("## Scenario Definitions\n")

        # Add scenario definitions
        for name in scenario_names:
            if name in self.scenarios:
                scenario = self.scenarios[name]
                report.append(f"### {scenario.name}\n")
                report.append(f"**Description:** {scenario.description}\n")
                report.append("**Adjustments:**\n")
                for column, adjustment in scenario.adjustments.items():
                    report.append(f"  - {column}: {adjustment}\n")
                report.append("\n")

        # Add comparison results
        report.append("## Scenario Comparisons\n")

        for table_name in self.base_data:
            report.append(f"### {table_name}\n")
            try:
                comparison_df = self.compare_scenarios(scenario_names, table_name)
                if not comparison_df.is_empty():
                    report.append(markdown_table(comparison_df))
                    report.append("\n")
            except (KeyError, ValueError, TypeError, pl.exceptions.PolarsError) as e:
                report.append(f"Error comparing scenarios for {table_name}: {e}\n")

        report_str = "\n".join(report)

        if output_file:
            with Path(output_file).open("w") as f:
                f.write(report_str)

        return report_str


def create_common_scenarios() -> dict[str, Scenario]:
    """Create common scenarios for microcosting analysis.

    Returns:
        Dictionary of common scenarios

    """
    scenarios: dict[str, Scenario] = {}

    # Inflation scenario
    scenarios["inflation_5"] = Scenario(
        name="inflation_5",
        description="5% inflation across all cost components",
        parameters={"inflation_rate": 0.05},
        adjustments={
            "unit_cost_aud_per_unit": 1.05,
            "price_aud_per_unit": 1.05,
            "hourly_rate_aud": 1.05,
        },
    )

    # Cost reduction scenario
    scenarios["cost_reduction_10"] = Scenario(
        name="cost_reduction_10",
        description="10% reduction in all costs through efficiency improvements",
        parameters={"reduction_rate": 0.10},
        adjustments={
            "unit_cost_aud_per_unit": 0.90,
            "price_aud_per_unit": 0.90,
            "hourly_rate_aud": 0.90,
        },
    )

    # High throughput scenario
    scenarios["high_throughput"] = Scenario(
        name="high_throughput",
        description="50% increase in throughput reducing per-unit equipment costs",
        parameters={"throughput_increase": 0.50},
        adjustments={
            "equipment_unit_cost_aud": 0.67,  # 1/(1+0.50)
            "equipment_price_aud": 0.67,
        },
    )

    # Labor cost increase scenario
    scenarios["labor_cost_increase"] = Scenario(
        name="labor_cost_increase",
        description="15% increase in labor costs due to market conditions",
        parameters={"labor_increase": 0.15},
        adjustments={
            "hourly_rate_aud": 1.15,
            "labor_unit_cost_aud": 1.15,
        },
    )

    return scenarios


# Example usage function
def example_usage() -> None:
    """Demonstrate the scenario modeling tools."""
    logger.info("%s", "Loading data for scenario analysis...")

    # This would typically load actual data
    # For demonstration, we'll create sample data
    sample_data = {
        "detailed_table": pl.DataFrame(
            {
                "step": ["A", "B", "C"],
                "unit_cost_aud_per_unit": [100.0, 200.0, 150.0],
                "price_aud_per_unit": [120.0, 220.0, 170.0],
                "hours": [2.0, 3.0, 1.5],
            },
        ),
        "labor_prices": pl.DataFrame(
            {
                "labor_type": ["Tech", "Manager", "Assistant"],
                "hourly_rate_aud": [50.0, 80.0, 30.0],
            },
        ),
    }

    # Create scenario manager
    scenario_manager = ScenarioManager(sample_data)

    # Add common scenarios
    common_scenarios = create_common_scenarios()
    for scenario in common_scenarios.values():
        scenario_manager.add_scenario(scenario)

    # Run a scenario analysis
    logger.info("%s", "Running inflation scenario...")
    scenario_manager.run_scenario_analysis("inflation_5")

    # Compare scenarios
    logger.info("%s", "Comparing scenarios...")
    comparison = scenario_manager.compare_scenarios(
        ["inflation_5", "cost_reduction_10"],
        "detailed_table",
    )
    logger.info("%s", comparison)

    # Generate report
    logger.info("%s", "Generating report...")
    report = scenario_manager.generate_scenario_report(
        ["inflation_5", "cost_reduction_10", "high_throughput"],
    )
    logger.info("%s", report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
