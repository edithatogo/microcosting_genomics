# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Budget Impact Analysis module."""

import unittest
from unittest.mock import Mock

import polars as pl

from genomics_microcosting.budget_impact_analysis import BudgetImpactAnalyzer
from genomics_microcosting.data_manager import DataManager
from tests.checks import require_equal, require_runtime_instance


class TestBudgetImpactAnalyzer(unittest.TestCase):
    """Test cases for the BudgetImpactAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BudgetImpactAnalyzer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test BudgetImpactAnalyzer initialization."""
        require_runtime_instance(self.analyzer, BudgetImpactAnalyzer)
        if not ((self.analyzer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_load_budget_parameters(self) -> None:
        """Test loading budget parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet_polars.return_value = None

        result = self.analyzer.load_budget_parameters()
        require_runtime_instance(result, dict)
        # Should return an empty dict since all loads return None
        if not ((len(result)) == (0)):
            raise AssertionError

    def test_perform_volume_sensitivity_analysis(self) -> None:
        """Test volume sensitivity analysis."""
        baseline_volume = 1000
        # Test with default parameters
        result = self.analyzer.perform_volume_sensitivity_analysis()

        require_runtime_instance(result, pl.DataFrame)
        if not ((len(result)) > (0)):
            raise AssertionError
        if ("Volume") not in (result.columns):
            raise AssertionError
        if ("Total_Cost") not in (result.columns):
            raise AssertionError
        if ("Volume_Change_Pct") not in (result.columns):
            raise AssertionError
        if ("Cost_Change_Pct") not in (result.columns):
            raise AssertionError

        # Check that base volume (1000) has 0% change
        base_row = result.filter(pl.col("Volume") == baseline_volume)
        if not ((len(base_row)) == (1)):
            raise AssertionError
        if not ((base_row["Volume_Change_Pct"][0]) == (0.0)):
            raise AssertionError
        if not ((base_row["Cost_Change_Pct"][0]) == (0.0)):
            raise AssertionError

    def test_perform_volume_sensitivity_analysis_custom(self) -> None:
        """Test volume sensitivity analysis with custom parameters."""
        first_scenario_volume = 500
        result = self.analyzer.perform_volume_sensitivity_analysis(
            base_volume=500,
            volume_range=[400, 500, 600],
            cost_per_test=1500.0,
        )

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 3)
        if (first_scenario_volume) not in (result["Volume"].to_list()):
            raise AssertionError
        require_equal(
            result.filter(pl.col("Volume") == first_scenario_volume)["Total_Cost"][0],
            500 * 1500.0,
        )

    def test_perform_time_horizon_analysis(self) -> None:
        """Test time horizon analysis."""
        expected_years = 5
        result = self.analyzer.perform_time_horizon_analysis()

        require_runtime_instance(result, pl.DataFrame)
        if not ((len(result)) == (expected_years)):
            raise AssertionError  # Default 5 years
        if ("Year") not in (result.columns):
            raise AssertionError
        if ("Volume") not in (result.columns):
            raise AssertionError
        if ("Cost_Per_Test") not in (result.columns):
            raise AssertionError
        if ("Total_Cost") not in (result.columns):
            raise AssertionError

        # Check that values change over time due to growth and cost reduction
        if not (
            (result.row(-1, named=True)["Volume"])
            > (result.row(0, named=True)["Volume"])
        ):
            raise AssertionError
        if not (
            (result.row(-1, named=True)["Cost_Per_Test"])
            < (result.row(0, named=True)["Cost_Per_Test"])
        ):
            raise AssertionError

    def test_perform_time_horizon_analysis_custom(self) -> None:
        """Test time horizon analysis with custom parameters."""
        result = self.analyzer.perform_time_horizon_analysis(
            initial_volume=800,
            growth_rate=0.1,
            years=3,
            cost_per_test=1800.0,
            annual_cost_reduction=0.01,
        )

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 3)
        if not ((result.row(0, named=True)["Year"]) == (1)):
            raise AssertionError
        require_equal(result.row(0, named=True)["Volume"], 800)

    def test_perform_scenario_analysis(self) -> None:
        """Test scenario analysis."""
        result = self.analyzer.perform_scenario_analysis()

        require_runtime_instance(result, pl.DataFrame)
        if not ((len(result)) > (0)):
            raise AssertionError
        if ("Scenario") not in (result.columns):
            raise AssertionError
        if ("Volume") not in (result.columns):
            raise AssertionError
        if ("Cost_Per_Test") not in (result.columns):
            raise AssertionError
        if ("Total_Cost") not in (result.columns):
            raise AssertionError

    def test_perform_scenario_analysis_custom(self) -> None:
        """Test scenario analysis with custom scenarios."""
        custom_scenarios = {
            "Low Volume": {
                "volume": 500,
                "cost_per_test": 2500.0,
            },
            "High Volume": {
                "volume": 2000,
                "cost_per_test": 1500.0,
            },
        }

        result = self.analyzer.perform_scenario_analysis(custom_scenarios)

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 2)
        if ("Low Volume") not in (result["Scenario"].to_list()):
            raise AssertionError
        if ("High Volume") not in (result["Scenario"].to_list()):
            raise AssertionError

    def test_calculate_economies_of_scale(self) -> None:
        """Test economies of scale calculation."""
        volume_range = [500, 1000, 1500]
        result = self.analyzer.calculate_economies_of_scale(volume_range)

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 3)
        if ("Volume") not in (result.columns):
            raise AssertionError
        if ("Fixed_Costs") not in (result.columns):
            raise AssertionError
        if ("Variable_Costs") not in (result.columns):
            raise AssertionError
        if ("Total_Costs") not in (result.columns):
            raise AssertionError
        if ("Cost_Per_Test") not in (result.columns):
            raise AssertionError

        # Check that cost per test decreases with volume (economies of scale)
        if not (
            (result.row(0, named=True)["Cost_Per_Test"])
            > (result.row(-1, named=True)["Cost_Per_Test"])
        ):
            raise AssertionError

    def test_generate_budget_impact_report(self) -> None:
        """Test budget impact report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet_polars.return_value = None

        # Generate report
        report = self.analyzer.generate_budget_impact_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Budget Impact Analysis") not in (report):
            raise AssertionError
        if ("Volume Sensitivity Analysis") not in (report):
            raise AssertionError
        if ("Time Horizon Analysis") not in (report):
            raise AssertionError
        if ("Scenario Analysis") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
