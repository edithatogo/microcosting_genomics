# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test result validation criteria for genomics microcosting analysis.

This module defines and tests the validation criteria for ensuring analysis
results meet required standards and quality thresholds.
"""

import unittest
from typing import TypedDict
from unittest.mock import Mock

import numpy as np
import polars as pl

from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer
from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.dsa_analysis import DSAAnalyzer
from genomics_microcosting.psa_analysis import PSAAnalyzer
from tests.checks import require_close, require_runtime_instance

PARAMETER_NAME_LENGTH_THRESHOLD = 5
PSA_SAMPLE_COUNT = 1000
MAXIMUM_REASONABLE_COST = 10000
MINIMUM_NORMAL_COVERAGE = 0.95
EXPECTED_CATEGORY_COUNT = 3
MAXIMUM_PERCENT_IMPACT = 100.0


class DSACriterion(TypedDict):
    """Synthetic DSA fields checked by the unchanged validation predicates."""

    parameter: str
    baseline: float
    low_value: float
    high_value: float
    low_change_pct: float
    high_change_pct: float
    low_impact: float
    high_impact: float
    max_impact: float


class DriverCriterion(TypedDict):
    """A component's numeric driver result."""

    value: float
    percentage: float


class ModuleCriterion(TypedDict):
    """Shared synthetic measurements compared across analysis consumers."""

    cost_driver: DriverCriterion
    dsa_baseline: float
    psa_mean: float
    psa_std: float


class TestValidationCriteria(unittest.TestCase):
    """Test result validation criteria for analysis results."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)

    def test_cost_driver_validation_criteria(self) -> None:
        """Test validation criteria for cost driver analysis results.

        Validation criteria:
        1. All cost drivers should have positive values
        2. Percentages should sum to approximately 100%
        3. Rankings should be consistent with values
        4. No missing categories
        """
        # Create test cost driver results
        cost_drivers = pl.DataFrame(
            {
                "Category": [
                    "Labour",
                    "Equipment",
                    "Consumables",
                    "Compute",
                    "Storage",
                ],
                "Absolute_Value": [1200.0, 800.0, 600.0, 400.0, 200.0],
                "Percentage": [37.5, 25.0, 18.75, 12.5, 6.25],
            },
        )

        # Validation 1: All cost drivers should have positive values
        _check_message_60 = "All cost driver values should be positive"
        if not (all(cost_drivers["Absolute_Value"] > 0)):
            raise AssertionError(_check_message_60)

        # Validation 2: Percentages should sum to approximately 100%
        total_percentage = float(cost_drivers["Percentage"].sum())
        require_close(
            total_percentage,
            100.0,
            delta=1.0,
            message="Percentages should sum to approximately 100%",
        )

        # Validation 3: Rankings should be consistent with values
        sorted_by_value = cost_drivers.sort("Absolute_Value", descending=True)
        sorted_by_percentage = cost_drivers.sort("Percentage", descending=True)

        # Top category should be the same when sorted by value or percentage
        _check_message_79 = "Rankings should be consistent between value and percentage"
        if not (
            (sorted_by_value.item(0, "Category"))
            == (sorted_by_percentage.item(0, "Category"))
        ):
            raise AssertionError(_check_message_79)

        # Validation 4: No missing categories
        expected_categories = [
            "Labour",
            "Equipment",
            "Consumables",
            "Compute",
            "Storage",
        ]
        actual_categories = cost_drivers["Category"].to_list()
        for category in expected_categories:
            _check_message_95 = f"Expected category {category} not found"
            if (category) not in (actual_categories):
                raise AssertionError(_check_message_95)

    def test_dsa_validation_criteria(self) -> None:
        """Test validation criteria for DSA analysis results.

        Validation criteria:
        1. Sensitivity ranges should be logical (low < baseline < high)
        2. Impact values should be non-negative
        3. Parameter names should be descriptive
        4. Results should be consistent with input parameters
        """
        # Create test DSA results
        dsa_results: list[DSACriterion] = [
            {
                "parameter": "Labour Hourly Rate",
                "baseline": 50.0,
                "low_value": 40.0,
                "high_value": 60.0,
                "low_change_pct": -20.0,
                "high_change_pct": 20.0,
                "low_impact": 20.0,
                "high_impact": 20.0,
                "max_impact": 20.0,
            },
            {
                "parameter": "Equipment Utilization",
                "baseline": 0.8,
                "low_value": 0.6,
                "high_value": 0.95,
                "low_change_pct": -25.0,
                "high_change_pct": 18.75,
                "low_impact": 25.0,
                "high_impact": 18.75,
                "max_impact": 25.0,
            },
        ]

        for result in dsa_results:
            # Validation 1: Sensitivity ranges should be logical
            _check_message_138 = "Low value should be less than baseline"
            if not ((result["low_value"]) < (result["baseline"])):
                raise AssertionError(_check_message_138)
            _check_message_143 = "High value should be greater than baseline"
            if not ((result["high_value"]) > (result["baseline"])):
                raise AssertionError(_check_message_143)

            # Validation 2: Impact values should be non-negative
            _check_message_150 = "Impact values should be non-negative"
            if not ((result["low_impact"]) >= (0)):
                raise AssertionError(_check_message_150)
            _check_message_155 = "Impact values should be non-negative"
            if not ((result["high_impact"]) >= (0)):
                raise AssertionError(_check_message_155)
            _check_message_160 = "Impact values should be non-negative"
            if not ((result["max_impact"]) >= (0)):
                raise AssertionError(_check_message_160)

            # Validation 3: Parameter names should be descriptive
            require_runtime_instance(
                result["parameter"],
                str,
                message="Parameter names should be strings",
            )
            _check_message_172 = "Parameter names should be descriptive"
            if not ((len(result["parameter"])) > (PARAMETER_NAME_LENGTH_THRESHOLD)):
                raise AssertionError(_check_message_172)

            # Validation 4: Percentage changes should be calculated correctly
            expected_low_change = (
                (result["low_value"] - result["baseline"]) / result["baseline"]
            ) * 100
            expected_high_change = (
                (result["high_value"] - result["baseline"]) / result["baseline"]
            ) * 100

            require_close(
                result["low_change_pct"],
                expected_low_change,
                delta=0.01,
                message="Low percentage change calculated incorrectly",
            )
            require_close(
                result["high_change_pct"],
                expected_high_change,
                delta=0.01,
                message="High percentage change calculated incorrectly",
            )

    def test_psa_validation_criteria(self) -> None:
        """Test validation criteria for PSA analysis results.

        Validation criteria:
        1. Monte Carlo samples should have correct distribution properties
        2. Cost outcomes should be realistic
        3. Confidence intervals should be logical
        4. Statistical properties should be consistent
        """
        # Create test PSA results
        rng = np.random.RandomState(
            42,
        )  # Preserve the legacy draws without global state
        labour_costs = rng.normal(1000, 100, 1000)
        equipment_costs = rng.normal(800, 50, 1000)
        cost_outcomes = labour_costs + equipment_costs + 500  # Fixed costs

        # Validation 1: Monte Carlo samples should have correct distribution properties
        _check_message_215 = "Should have 1000 samples"
        if not ((len(labour_costs)) == (PSA_SAMPLE_COUNT)):
            raise AssertionError(_check_message_215)
        _check_message_216 = "Should have 1000 samples"
        if not ((len(equipment_costs)) == (PSA_SAMPLE_COUNT)):
            raise AssertionError(_check_message_216)
        _check_message_217 = "Should have 1000 outcomes"
        if not ((len(cost_outcomes)) == (PSA_SAMPLE_COUNT)):
            raise AssertionError(_check_message_217)

        # Check mean and std are reasonable
        require_close(
            np.mean(labour_costs),
            1000,
            delta=10,
            message="Labour cost mean should be close to 1000",
        )
        require_close(
            np.std(labour_costs),
            100,
            delta=10,
            message="Labour cost std should be close to 100",
        )

        # Validation 2: Cost outcomes should be realistic
        _check_message_234 = "All cost outcomes should be positive"
        if not (all(cost_outcomes > 0)):
            raise AssertionError(_check_message_234)
        _check_message_235 = "Cost outcomes should be reasonable"
        if not (all(cost_outcomes < MAXIMUM_REASONABLE_COST)):
            raise AssertionError(_check_message_235)

        # Validation 3: Confidence intervals should be logical
        percentiles = [2.5, 25, 50, 75, 97.5]
        confidence_intervals: dict[str, float] = {}
        for percentile in percentiles:
            confidence_intervals[f"{percentile}%"] = float(
                np.percentile(
                    cost_outcomes,
                    percentile,
                ),
            )

        self._check_confidence_intervals(confidence_intervals)

        # Validation 4: Statistical properties should be consistent
        mean_cost = np.mean(cost_outcomes)
        std_cost = np.std(cost_outcomes)

        # Most values should be within 3 standard deviations
        within_3_std = np.sum(np.abs(cost_outcomes - mean_cost) <= 3 * std_cost)
        proportion_within_3_std = within_3_std / len(cost_outcomes)
        _check_message_271 = "Most values should be within 3 standard deviations"
        if not ((proportion_within_3_std) > (MINIMUM_NORMAL_COVERAGE)):
            raise AssertionError(_check_message_271)

    @staticmethod
    def _check_confidence_intervals(confidence_intervals: dict[str, float]) -> None:
        """Retain the percentile ordering and interquartile median predicates."""
        # Check that percentiles are in ascending order
        percentile_values = list(confidence_intervals.values())
        _check_message_251 = "Percentiles should be in ascending order"
        if not ((percentile_values) == (sorted(percentile_values))):
            raise AssertionError(_check_message_251)

        # Check that median is between 25th and 75th percentiles
        median = confidence_intervals["50%"]
        q1 = confidence_intervals["25%"]
        q3 = confidence_intervals["75%"]
        _check_message_261 = "Median should be >= 25th percentile"
        if not ((median) >= (q1)):
            raise AssertionError(_check_message_261)
        _check_message_262 = "Median should be <= 75th percentile"
        if not ((median) <= (q3)):
            raise AssertionError(_check_message_262)

    def test_cross_module_validation_criteria(self) -> None:
        """Test validation criteria for cross-module consistency.

        Validation criteria:
        1. Results should be consistent between related modules
        2. Shared parameters should have consistent values
        3. Aggregated results should match component results
        4. Temporal consistency should be maintained
        """
        # Create test data that should be consistent across modules
        labour_data: ModuleCriterion = {
            "cost_driver": {"value": 1200.0, "percentage": 37.5},
            "dsa_baseline": 1200.0,
            "psa_mean": 1200.0,
            "psa_std": 120.0,
        }

        equipment_data: ModuleCriterion = {
            "cost_driver": {"value": 800.0, "percentage": 25.0},
            "dsa_baseline": 800.0,
            "psa_mean": 800.0,
            "psa_std": 80.0,
        }

        # Validation 1: Results should be consistent between related modules
        # Cost driver value should match DSA baseline
        _check_message_303 = "Cost driver value should match DSA baseline"
        if not ((labour_data["cost_driver"]["value"]) == (labour_data["dsa_baseline"])):
            raise AssertionError(_check_message_303)
        _check_message_308 = "Cost driver value should match DSA baseline"
        if not (
            (equipment_data["cost_driver"]["value"]) == (equipment_data["dsa_baseline"])
        ):
            raise AssertionError(_check_message_308)

        # Validation 2: Shared parameters should have consistent values
        # PSA mean should be close to cost driver value and DSA baseline
        require_close(
            labour_data["psa_mean"],
            labour_data["cost_driver"]["value"],
            delta=50,
            message="PSA mean should be close to cost driver value",
        )
        require_close(
            equipment_data["psa_mean"],
            equipment_data["cost_driver"]["value"],
            delta=50,
            message="PSA mean should be close to cost driver value",
        )

        # Validation 3: Statistical relationships should be logical
        # Higher cost driver values should generally have higher uncertainty
        labour_cv = (
            labour_data["psa_std"] / labour_data["psa_mean"]
        )  # Coefficient of variation
        equipment_cv = equipment_data["psa_std"] / equipment_data["psa_mean"]

        # This is a simplified check - in reality, the relationship between cost driver
        # magnitude and uncertainty would depend on many factors
        _check_message_338 = "Coefficient of variation should be positive"
        if not ((labour_cv) > (0)):
            raise AssertionError(_check_message_338)
        _check_message_339 = "Coefficient of variation should be positive"
        if not ((equipment_cv) > (0)):
            raise AssertionError(_check_message_339)

    def test_boundary_condition_validation(self) -> None:
        """Test validation criteria for boundary conditions and edge cases.

        Validation criteria:
        1. Zero values should be handled correctly
        2. Extreme values should not cause errors
        3. Missing data should be handled gracefully
        4. Empty datasets should be handled appropriately
        """
        # Test with zero values
        zero_cost_drivers = pl.DataFrame(
            {
                "Category": ["Labour", "Equipment", "Consumables"],
                "Absolute_Value": [0.0, 0.0, 0.0],
                "Percentage": [0.0, 0.0, 0.0],
            },
        )

        # Even with zero values, structure should be maintained
        _check_message_364 = "Should maintain row count"
        if not ((len(zero_cost_drivers)) == (EXPECTED_CATEGORY_COUNT)):
            raise AssertionError(_check_message_364)
        _check_message_365 = "Should maintain columns"
        if ("Category") not in (zero_cost_drivers.columns):
            raise AssertionError(_check_message_365)

        # Test with extreme values
        extreme_dsa: DSACriterion = {
            "parameter": "Extreme Parameter",
            "baseline": 1000000.0,  # Very large baseline
            "low_value": 0.001,  # Very small low value
            "high_value": 1000000000.0,  # Very large high value
            "low_change_pct": -99.9999999,  # Near -100%
            "high_change_pct": 99999.0,  # Very large percentage increase
            "low_impact": 99.9999999,  # Near maximum impact
            "high_impact": 100.0,  # Maximum impact
            "max_impact": 100.0,
        }

        # Should handle extreme values without error
        if not ((extreme_dsa["high_value"]) > (extreme_dsa["baseline"])):
            raise AssertionError
        if not ((extreme_dsa["low_value"]) < (extreme_dsa["baseline"])):
            raise AssertionError
        _check_message_383 = "Impact should not exceed 100%"
        if not ((extreme_dsa["max_impact"]) <= (MAXIMUM_PERCENT_IMPACT)):
            raise AssertionError(_check_message_383)

        # Test with missing data (represented as NaN)
        nan_data = pl.DataFrame(
            {
                "Category": ["Labour", "Equipment", "Consumables"],
                "Absolute_Value": [1200.0, np.nan, 600.0],
                "Percentage": [37.5, 18.75, np.nan],
            },
        )

        # Should identify missing data
        nan_count = (
            nan_data.with_columns(pl.selectors.float().fill_nan(None))
            .null_count()
            .sum_horizontal()
            .item()
        )
        _check_message_400 = "Should detect missing data"
        if not ((nan_count) > (0)):
            raise AssertionError(_check_message_400)

        # Test with empty dataset
        empty_data = pl.DataFrame()
        _check_message_404 = "Should correctly identify empty data"
        if not (empty_data.is_empty()):
            raise AssertionError(_check_message_404)


if __name__ == "__main__":
    unittest.main()
