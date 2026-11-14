# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Break-even Analysis module."""

import unittest
from unittest.mock import Mock

import polars as pl

from genomics_microcosting.break_even_analysis import BreakEvenAnalyzer
from genomics_microcosting.data_manager import DataManager
from tests.checks import require_equal, require_keys, require_runtime_instance


class TestBreakEvenAnalyzer(unittest.TestCase):
    """Test cases for the BreakEvenAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BreakEvenAnalyzer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test BreakEvenAnalyzer initialization."""
        require_runtime_instance(self.analyzer, BreakEvenAnalyzer)
        if not ((self.analyzer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_load_break_even_parameters(self) -> None:
        """Test loading break-even parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet_polars.return_value = None

        result = self.analyzer.load_break_even_parameters()
        require_runtime_instance(result, dict)
        # Should return an empty dict since all loads return None
        if not ((len(result)) == (0)):
            raise AssertionError

    def test_calculate_break_even_volume(self) -> None:
        """Test break-even volume calculation."""
        # Test normal case
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=100.0,
            variable_cost_per_test=50.0,
        )

        # Break-even volume = Fixed Costs / (Price - Variable Cost)
        # = 100000 / (100 - 50) = 100000 / 50 = 2000
        require_equal(result, 2000.0)

        # Test case with zero contribution margin
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=50.0,
            variable_cost_per_test=50.0,
        )

        # Should return infinity when contribution margin is zero
        if not ((result) == (float("inf"))):
            raise AssertionError

        # Test case with negative contribution margin
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=40.0,
            variable_cost_per_test=50.0,
        )

        # Should return infinity when contribution margin is negative
        if not ((result) == (float("inf"))):
            raise AssertionError

    def test_calculate_contribution_margin(self) -> None:
        """Test contribution margin calculation."""
        expected_margin_per_test = 40.0
        expected_margin_percent = 40.0
        result = self.analyzer.calculate_contribution_margin(
            price_per_test=100.0,
            variable_cost_per_test=60.0,
        )

        require_runtime_instance(result, dict)
        if ("contribution_margin_per_test") not in (result):
            raise AssertionError
        if ("contribution_margin_ratio") not in (result):
            raise AssertionError
        if ("price_per_test") not in (result):
            raise AssertionError
        if ("variable_cost_per_test") not in (result):
            raise AssertionError

        # Check calculations
        if not ((result["contribution_margin_per_test"]) == (expected_margin_per_test)):
            raise AssertionError  # 100 - 60
        if not ((result["contribution_margin_ratio"]) == (expected_margin_percent)):
            raise AssertionError  # (40 / 100) * 100
        require_equal(result["price_per_test"], 100.0)
        require_equal(result["variable_cost_per_test"], 60.0)

        # Test with zero price
        result = self.analyzer.calculate_contribution_margin(
            price_per_test=0.0,
            variable_cost_per_test=60.0,
        )

        require_equal(result["contribution_margin_per_test"], -60.0)
        if not ((result["contribution_margin_ratio"]) == (0.0)):
            raise AssertionError

    def test_perform_sensitivity_analysis(self) -> None:
        """Test sensitivity analysis."""
        expected_scenario_count = 4
        expected_revenue = 100000.0
        expected_variable_cost = 50000.0
        expected_total_cost = 150000.0
        expected_profit = -50000.0
        expected_break_even_volume = 2000.0
        result = self.analyzer.perform_sensitivity_analysis(
            fixed_costs=100000.0,
            price_per_test=100.0,
            variable_cost_range=[50.0, 60.0],
            volume_range=[1000, 2000],
        )

        require_runtime_instance(result, pl.DataFrame)
        require_equal(
            len(result),
            expected_scenario_count,
        )  # 2 variable costs x 2 volumes
        require_keys(result.columns, ("Variable_Cost_Per_Test",))
        require_keys(result.columns, ("Volume",))
        require_keys(result.columns, ("Revenue",))
        require_keys(result.columns, ("Variable_Costs",))
        require_keys(result.columns, ("Fixed_Costs",))
        require_keys(result.columns, ("Total_Costs",))
        require_keys(result.columns, ("Profit",))
        require_keys(result.columns, ("Break_Even_Volume",))

        # Check calculations for first row
        first_row = result.row(0, named=True)
        require_equal(first_row["Variable_Cost_Per_Test"], 50.0)
        require_equal(first_row["Volume"], 1000)
        require_equal(first_row["Revenue"], expected_revenue)  # 100 * 1000
        require_equal(first_row["Variable_Costs"], expected_variable_cost)  # 50 * 1000
        require_equal(first_row["Fixed_Costs"], 100000.0)
        require_equal(first_row["Total_Costs"], expected_total_cost)  # 100000 + 50000
        require_equal(first_row["Profit"], expected_profit)  # 100000 - 150000
        require_equal(
            first_row["Break_Even_Volume"],
            expected_break_even_volume,
        )  # 100000 / (100 - 50)

    def test_calculate_minimum_efficient_scale(self) -> None:
        """Test minimum efficient scale calculation."""
        expected_break_even_volume = 2000.0
        result = self.analyzer.calculate_minimum_efficient_scale(
            fixed_costs=100000.0,
            variable_cost_per_test=50.0,
            price_per_test=100.0,
            efficiency_threshold=0.95,
        )

        require_runtime_instance(result, dict)
        if ("minimum_efficient_volume") not in (result):
            raise AssertionError
        if ("break_even_volume") not in (result):
            raise AssertionError
        if ("cost_per_test_at_efficiency") not in (result):
            raise AssertionError
        if ("efficiency_threshold") not in (result):
            raise AssertionError

        # Check that break-even volume is calculated correctly
        if not ((result["break_even_volume"]) == (expected_break_even_volume)):
            raise AssertionError  # 100000 / (100 - 50)

        # Check that minimum efficient volume is greater than break-even volume
        if not ((result["minimum_efficient_volume"]) > (result["break_even_volume"])):
            raise AssertionError

    def test_analyze_service_lines(self) -> None:
        """Test service line analysis."""
        expected_break_even_volume = 1250.0
        expected_margin_per_test = 40.0
        expected_margin_percent = 40.0
        service_line_data = {
            "Test Service": {
                "fixed_costs": 50000.0,
                "price_per_test": 100.0,
                "variable_cost_per_test": 60.0,
            },
        }

        result = self.analyzer.analyze_service_lines(service_line_data)

        require_runtime_instance(result, pl.DataFrame)
        require_equal(len(result), 1)
        require_keys(result.columns, ("Service_Line",))
        require_keys(result.columns, ("Fixed_Costs",))
        require_keys(result.columns, ("Price_Per_Test",))
        require_keys(result.columns, ("Variable_Cost_Per_Test",))
        require_keys(result.columns, ("Break_Even_Volume",))
        require_keys(result.columns, ("Contribution_Margin_Per_Test",))
        require_keys(result.columns, ("Contribution_Margin_Ratio",))
        require_keys(result.columns, ("Minimum_Efficient_Volume",))

        # Check calculations
        first_row = result.row(0, named=True)
        require_equal(first_row["Service_Line"], "Test Service")
        require_equal(first_row["Fixed_Costs"], 50000.0)
        require_equal(first_row["Price_Per_Test"], 100.0)
        require_equal(first_row["Variable_Cost_Per_Test"], 60.0)
        require_equal(
            first_row["Break_Even_Volume"],
            expected_break_even_volume,
        )  # 50000 / (100 - 60)
        require_equal(
            first_row["Contribution_Margin_Per_Test"],
            expected_margin_per_test,
        )  # 100 - 60
        require_equal(
            first_row["Contribution_Margin_Ratio"],
            expected_margin_percent,
        )  # (40 / 100) * 100

    def test_generate_break_even_report(self) -> None:
        """Test break-even report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet_polars.return_value = None

        # Generate report
        report = self.analyzer.generate_break_even_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Break-even Analysis") not in (report):
            raise AssertionError
        if ("Break-even Volume Calculation") not in (report):
            raise AssertionError
        if ("Contribution Margin Analysis") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
