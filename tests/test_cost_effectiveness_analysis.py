# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Cost-Effectiveness Analysis module."""

import unittest
from unittest.mock import Mock

import polars as pl

from genomics_microcosting.cost_effectiveness_analysis import (
    CostEffectivenessAnalyzer,
)
from genomics_microcosting.data_manager import DataManager
from tests.checks import require_equal, require_rounded_equal, require_runtime_instance


class TestCostEffectivenessAnalyzer(unittest.TestCase):
    """Test cases for the CostEffectivenessAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = CostEffectivenessAnalyzer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test CostEffectivenessAnalyzer initialization."""
        require_runtime_instance(self.analyzer, CostEffectivenessAnalyzer)
        if not ((self.analyzer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_load_cost_effectiveness_parameters(self) -> None:
        """Test loading cost-effectiveness parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None

        result = self.analyzer.load_cost_effectiveness_parameters()
        require_runtime_instance(result, dict)
        # Should return an empty dict since all loads return None
        if not ((len(result)) == (0)):
            raise AssertionError

    def test_calculate_cost_per_diagnostic_yield(self) -> None:
        """Test cost per diagnostic yield calculation."""
        # Test normal case
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=0.3,
        )

        # Cost per diagnostic yield = Cost per test / Diagnostic yield rate
        # = 3000 / 0.3 = 10000
        require_equal(result, 10000.0)

        # Test case with zero diagnostic yield rate
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=0.0,
        )

        # Should return infinity when diagnostic yield rate is zero
        if not ((result) == (float("inf"))):
            raise AssertionError

        # Test case with negative diagnostic yield rate
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=-0.1,
        )

        # Should return infinity when diagnostic yield rate is negative
        if not ((result) == (float("inf"))):
            raise AssertionError

    def test_compare_cost_effectiveness_across_models(self) -> None:
        """Test cost-effectiveness comparison across models."""
        expected_cost_per_yield = 5000.0
        model_data = {
            "Test Model": {
                "cost_per_test": 1000.0,
                "diagnostic_yield_rate": 0.2,
                "turnaround_time": 5,
            },
        }

        result = self.analyzer.compare_cost_effectiveness_across_models(model_data)

        require_runtime_instance(result, pl.DataFrame)
        if not ((len(result)) == (1)):
            raise AssertionError
        if ("Model") not in (result.columns):
            raise AssertionError
        if ("Cost_Per_Test") not in (result.columns):
            raise AssertionError
        if ("Diagnostic_Yield_Rate") not in (result.columns):
            raise AssertionError
        if ("Turnaround_Time") not in (result.columns):
            raise AssertionError
        if ("Cost_Per_Diagnostic_Yield") not in (result.columns):
            raise AssertionError
        if ("Efficiency_Score") not in (result.columns):
            raise AssertionError

        # Check calculations
        first_row = result.row(0, named=True)
        if not ((first_row["Model"]) == ("Test Model")):
            raise AssertionError
        require_equal(first_row["Cost_Per_Test"], 1000.0)
        require_equal(first_row["Diagnostic_Yield_Rate"], 0.2)
        require_equal(first_row["Turnaround_Time"], 5)
        if not ((first_row["Cost_Per_Diagnostic_Yield"]) == (expected_cost_per_yield)):
            raise AssertionError  # 1000 / 0.2
        require_rounded_equal(
            first_row["Efficiency_Score"],
            0.00004,
            places=8,
        )  # 1 / (5000 * 5)

    def test_calculate_technical_efficiency_metrics(self) -> None:
        """Test technical efficiency metrics calculation."""
        result = self.analyzer.calculate_technical_efficiency_metrics(
            observed_output=100,
            observed_input=200,
            best_practice_output=120,
            best_practice_input=180,
        )

        require_runtime_instance(result, dict)
        if ("technical_efficiency") not in (result):
            raise AssertionError
        if ("cost_efficiency") not in (result):
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
        # = (100 / 120) / (200 / 180) = (0.8333) / (1.1111) = 0.75
        require_rounded_equal(result["technical_efficiency"], 0.75, places=4)

        # Cost efficiency = Observed cost / Best practice cost
        # = 200 / 180 = 1.1111
        require_rounded_equal(result["cost_efficiency"], 1.1111, places=4)

    def test_assess_productivity_improvements(self) -> None:
        """Test productivity improvements assessment."""
        baseline_data = {
            "tests_completed": 800,
            "total_cost": 1600000,
            "total_time": 30,
        }

        current_data = {
            "tests_completed": 1000,
            "total_cost": 1800000,
            "total_time": 30,
        }

        result = self.analyzer.assess_productivity_improvements(
            baseline_data,
            current_data,
        )

        require_runtime_instance(result, dict)
        if ("test_volume_improvement_pct") not in (result):
            raise AssertionError
        if ("cost_efficiency_improvement_pct") not in (result):
            raise AssertionError
        if ("productivity_improvement_pct") not in (result):
            raise AssertionError
        if ("cost_per_test_improvement_pct") not in (result):
            raise AssertionError

        # Check calculations
        # Test volume improvement = ((1000 - 800) / 800) * 100 = 25%
        require_rounded_equal(result["test_volume_improvement_pct"], 25.0, places=10)

        # Cost efficiency improvement = ((1600000 - 1800000) / 1600000) * 100 = -12.5%
        require_rounded_equal(
            result["cost_efficiency_improvement_pct"],
            -12.5,
            places=10,
        )

        # Baseline productivity = 800 / 30 = 26.6667
        # Current productivity = 1000 / 30 = 33.3333
        # Productivity improvement = ((33.3333 - 26.6667) / 26.6667) * 100 = 25%
        require_rounded_equal(result["productivity_improvement_pct"], 25.0, places=10)

        # Baseline cost per test = 1600000 / 800 = 2000
        # Current cost per test = 1800000 / 1000 = 1800
        # Cost per test improvement = ((2000 - 1800) / 2000) * 100 = 10%
        require_rounded_equal(result["cost_per_test_improvement_pct"], 10.0, places=10)

    def test_perform_incremental_cost_effectiveness_analysis(self) -> None:
        """Test incremental cost-effectiveness analysis."""
        result = self.analyzer.perform_incremental_cost_effectiveness_analysis(
            intervention_cost=5000.0,
            intervention_effectiveness=0.5,
            comparator_cost=3000.0,
            comparator_effectiveness=0.3,
        )

        require_runtime_instance(result, dict)
        if ("incremental_cost") not in (result):
            raise AssertionError
        if ("incremental_effectiveness") not in (result):
            raise AssertionError
        if ("icer") not in (result):
            raise AssertionError
        if ("is_intervention_dominant") not in (result):
            raise AssertionError
        if ("is_comparator_dominant") not in (result):
            raise AssertionError

        # Check calculations
        # Incremental cost = 5000 - 3000 = 2000
        require_equal(result["incremental_cost"], 2000.0)

        # Incremental effectiveness = 0.5 - 0.3 = 0.2
        require_equal(result["incremental_effectiveness"], 0.2)

        # ICER = 2000 / 0.2 = 10000
        require_equal(result["icer"], 10000.0)

        # Intervention is not dominant (more costly and more effective)
        if result["is_intervention_dominant"]:
            raise AssertionError

        # Comparator is not dominant (less costly and less effective)
        if result["is_comparator_dominant"]:
            raise AssertionError

    def test_generate_cost_effectiveness_report(self) -> None:
        """Test cost-effectiveness report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None

        # Generate report
        report = self.analyzer.generate_cost_effectiveness_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Cost-Effectiveness Analysis") not in (report):
            raise AssertionError
        if ("Cost-Effectiveness Comparison Across Models") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
