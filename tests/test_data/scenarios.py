# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test data sets representing various genomics microcosting scenarios.

This module provides standardized test data for different scenarios to ensure
consistent testing across all analytical modules.
"""

import logging
from typing import cast

import numpy as np
import polars as pl
lazy from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class TestScenarios:
    """Collection of test scenarios for genomics microcosting analysis."""

    @staticmethod
    def base_case_scenario() -> dict[str, pl.DataFrame]:
        """Build a base case scenario with standard parameters.

        Returns:
            Dictionary of DataFrames representing the base case scenario

        """
        return {
            "Detailed Table": pl.DataFrame(
                {
                    "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                    "Category": ["Labour", "Labour", "Labour", "Labour"],
                    "Sub-Category": [
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                    ],
                    "Step": [
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                    ],
                    "Quantity": [1.0, 1.0, 1.0, 1.0],
                    "Unit_Cost": [50.0, 75.0, 75.0, 100.0],
                    "Total_Cost": [50.0, 75.0, 75.0, 100.0],
                },
            ),
            "DSA - Labour Prices": pl.DataFrame(
                {
                    "Parameter": ["Hourly Rate"],
                    "Baseline": [50.0],
                    "Low": [40.0],
                    "High": [60.0],
                },
            ),
            "PSA": pl.DataFrame(
                {
                    "Parameter": ["Labour Cost", "Equipment Cost"],
                    "Distribution": ["normal", "normal"],
                    "Mean": [50000, 40000],
                    "Std": [5000, 4000],
                },
            ),
        }

    @staticmethod
    def high_volume_scenario() -> dict[str, pl.DataFrame]:
        """High volume scenario with increased test volumes.

        Returns:
            Dictionary of DataFrames representing the high volume scenario

        """
        return {
            "Detailed Table": pl.DataFrame(
                {
                    "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                    "Category": ["Labour", "Labour", "Labour", "Labour"],
                    "Sub-Category": [
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                    ],
                    "Step": [
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                    ],
                    "Quantity": [5.0, 5.0, 5.0, 5.0],  # 5x volume
                    "Unit_Cost": [50.0, 75.0, 75.0, 100.0],
                    "Total_Cost": [250.0, 375.0, 375.0, 500.0],
                },
            ),
            "DSA - Labour Prices": pl.DataFrame(
                {
                    "Parameter": ["Hourly Rate"],
                    "Baseline": [50.0],
                    "Low": [40.0],
                    "High": [60.0],
                },
            ),
            "Budget Impact": pl.DataFrame(
                {
                    "Year": [1, 2, 3],
                    "Volume": [5000, 10000, 15000],  # High volume projection
                    "Cost_Per_Test": [200, 190, 180],
                },
            ),
        }

    @staticmethod
    def cost_pressure_scenario() -> dict[str, pl.DataFrame]:
        """Cost pressure scenario with increased input costs.

        Returns:
            Dictionary of DataFrames representing the cost pressure scenario

        """
        return {
            "Detailed Table": pl.DataFrame(
                {
                    "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                    "Category": ["Labour", "Labour", "Labour", "Labour"],
                    "Sub-Category": [
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                    ],
                    "Step": [
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                    ],
                    "Quantity": [1.0, 1.0, 1.0, 1.0],
                    "Unit_Cost": [75.0, 112.5, 112.5, 150.0],  # 50% increase
                    "Total_Cost": [75.0, 112.5, 112.5, 150.0],
                },
            ),
            "DSA - Labour Prices": pl.DataFrame(
                {
                    "Parameter": ["Hourly Rate"],
                    "Baseline": [75.0],  # 50% increase
                    "Low": [60.0],
                    "High": [90.0],
                },
            ),
            "PSA": pl.DataFrame(
                {
                    "Parameter": ["Labour Cost", "Equipment Cost"],
                    "Distribution": ["normal", "normal"],
                    "Mean": [75000, 60000],  # 50% increase
                    "Std": [7500, 6000],
                },
            ),
        }

    @staticmethod
    def technology_advancement_scenario() -> dict[str, pl.DataFrame]:
        """Technology advancement scenario with improved efficiency.

        Returns:
            Dictionary of DataFrames representing the technology advancement scenario

        """
        return {
            "Detailed Table": pl.DataFrame(
                {
                    "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                    "Category": ["Labour", "Labour", "Labour", "Labour"],
                    "Sub-Category": [
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                    ],
                    "Step": [
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                    ],
                    "Quantity": [0.5, 0.5, 0.5, 0.5],  # 50% reduction due to efficiency
                    "Unit_Cost": [50.0, 75.0, 75.0, 100.0],
                    "Total_Cost": [25.0, 37.5, 37.5, 50.0],
                },
            ),
            "DSA - Equipment Throughput": pl.DataFrame(
                {
                    "Parameter": ["Utilization Rate"],
                    "Baseline": [0.95],  # Improved utilization
                    "Low": [0.8],
                    "High": [0.99],
                },
            ),
            "Break Even": pl.DataFrame(
                {
                    "Parameter": ["Efficiency_Gain"],
                    "Value": [0.5],
                    "Description": ["50% reduction in labour hours due to automation"],
                },
            ),
        }

    @staticmethod
    def regulatory_compliance_scenario() -> dict[str, pl.DataFrame]:
        """Regulatory compliance scenario with additional compliance costs.

        Returns:
            Dictionary of DataFrames representing the regulatory compliance scenario

        """
        return {
            "Detailed Table": pl.DataFrame(
                {
                    "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                    "Category": ["Labour", "Labour", "Labour", "Compliance"],
                    "Sub-Category": [
                        "Sequencing",
                        "Sequencing",
                        "Sequencing",
                        "Quality Control",
                    ],
                    "Step": [
                        "Sample Prep",
                        "Sample Prep",
                        "Sample Prep",
                        "Documentation",
                    ],
                    "Quantity": [1.0, 1.0, 1.0, 1.0],
                    "Unit_Cost": [50.0, 75.0, 75.0, 25.0],  # Additional compliance cost
                    "Total_Cost": [50.0, 75.0, 75.0, 25.0],
                },
            ),
            "DSA - Compliance Costs": pl.DataFrame(
                {
                    "Parameter": ["Compliance Hours"],
                    "Baseline": [10.0],
                    "Low": [5.0],
                    "High": [15.0],
                },
            ),
        }

    @staticmethod
    def all_scenarios() -> dict[str, dict[str, pl.DataFrame]]:
        """Get all test scenarios.

        Returns:
            Dictionary mapping scenario names to their data

        """
        return {
            "base_case": TestScenarios.base_case_scenario(),
            "high_volume": TestScenarios.high_volume_scenario(),
            "cost_pressure": TestScenarios.cost_pressure_scenario(),
            "technology_advancement": TestScenarios.technology_advancement_scenario(),
            "regulatory_compliance": TestScenarios.regulatory_compliance_scenario(),
        }


def generate_monte_carlo_samples(
    scenario_data: dict[str, pl.DataFrame],
    iterations: int = 1000,
) -> dict[str, NDArray[np.float64]]:
    """Generate Monte Carlo samples for PSA based on scenario data.

    Args:
        scenario_data: Dictionary of scenario data
        iterations: Number of Monte Carlo iterations

    Returns:
        Dictionary of parameter samples

    """
    samples: dict[str, NDArray[np.float64]] = {}
    rng = np.random.default_rng()

    # If PSA data exists, use it to generate samples
    if "PSA" in scenario_data:
        psa_data = scenario_data["PSA"]
        for row in psa_data.iter_rows(named=True):
            param_name = str(row["Parameter"])
            if row["Distribution"] == "normal":
                samples[param_name] = rng.normal(row["Mean"], row["Std"], iterations)
            elif row["Distribution"] == "uniform":
                low = row["Low"] if "Low" in row else row["Mean"] - row["Std"]
                high = row["High"] if "High" in row else row["Mean"] + row["Std"]
                samples[param_name] = rng.uniform(low, high, iterations)

    # If no PSA data, generate samples based on detailed table
    elif "Detailed Table" in scenario_data:
        detailed_data = scenario_data["Detailed Table"]
        for category in detailed_data["Category"].unique(maintain_order=True):
            category_data = detailed_data.filter(pl.col("Category") == category)
            costs = category_data["Total_Cost"].cast(pl.Float64).fill_nan(None)
            observed_mean = cast("float | None", costs.mean())
            mean_cost = float("nan") if observed_mean is None else observed_mean
            observed_std = cast("float | None", costs.std(ddof=1))
            std_cost = float("nan") if observed_std is None else observed_std
            std_cost = std_cost or mean_cost * 0.1
            samples[f"{category}_Cost"] = rng.normal(
                mean_cost,
                std_cost,
                iterations,
            )

    return samples


# Example usage:
if __name__ == "__main__":
    # Generate all scenarios
    scenarios = TestScenarios.all_scenarios()

    # Print scenario information
    for scenario_name, scenario_data in scenarios.items():
        logger.info("%s", f"\n{scenario_name.upper()} SCENARIO:")
        for sheet_name, data in scenario_data.items():
            logger.info(
                "%s",
                f"  {sheet_name}: {data.shape[0]} rows, {data.shape[1]} columns",
            )
