# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the VOI analysis module."""

import unittest
from unittest.mock import Mock, patch

import numpy as np

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.voi_analysis import VOIAnalyzer
from tests.checks import require_rounded_equal, require_runtime_instance


class TestVOIAnalyzer(unittest.TestCase):
    """Test cases for the VOIAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = VOIAnalyzer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test VOIAnalyzer initialization."""
        require_runtime_instance(self.analyzer, VOIAnalyzer)
        if not ((self.analyzer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_load_voi_parameters(self) -> None:
        """Test loading VOI parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None

        result = self.analyzer.load_voi_parameters()
        require_runtime_instance(result, dict)
        # Should return an empty dict since all loads return None
        if not ((len(result)) == (0)):
            raise AssertionError

    def test_calculate_evpi_cost_only(self) -> None:
        """Test EVPI calculation for cost-only analysis."""
        expected_mean_cost = 1000
        # Create sample cost outcomes
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])

        result = self.analyzer.calculate_evpi(cost_outcomes)

        if ("evpi") not in (result):
            raise AssertionError
        if ("evpi_as_percentage_of_mean") not in (result):
            raise AssertionError
        if ("mean_cost") not in (result):
            raise AssertionError
        if ("std_cost") not in (result):
            raise AssertionError

        # Check that values are reasonable
        if not ((result["evpi"]) >= (0)):
            raise AssertionError
        if not ((result["evpi_as_percentage_of_mean"]) >= (0)):
            raise AssertionError
        if not ((result["mean_cost"]) == (expected_mean_cost)):
            raise AssertionError  # Mean of [900, 950, 1000, 1050, 1100]
        require_rounded_equal(
            result["std_cost"],
            70.71067811865476,
            places=10,
        )  # Std dev

    def test_calculate_evpi_cost_effectiveness(self) -> None:
        """Test EVPI calculation for cost-effectiveness analysis."""
        # Create sample cost and effectiveness outcomes
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])
        willingness_to_pay = 50000

        result = self.analyzer.calculate_evpi(
            cost_outcomes,
            effectiveness_outcomes,
            willingness_to_pay,
        )

        if ("evpi") not in (result):
            raise AssertionError
        if ("evpi_as_percentage_of_mean_cost") not in (result):
            raise AssertionError
        if ("mean_cost") not in (result):
            raise AssertionError
        if ("mean_effectiveness") not in (result):
            raise AssertionError
        if ("willingness_to_pay") not in (result):
            raise AssertionError

    def test_calculate_evppi(self) -> None:
        """Test EVPPI calculation."""
        # Create sample data
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        parameter_groups = {
            "group1": ["param1", "param2"],
            "group2": ["param3"],
        }
        parameter_values = {
            "param1": np.array([1, 2, 3, 4, 5]),
            "param2": np.array([2, 3, 4, 5, 6]),
            "param3": np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        }

        result = self.analyzer.calculate_evppi(
            cost_outcomes,
            parameter_groups,
            parameter_values,
        )

        require_runtime_instance(result, dict)
        if ("group1") not in (result):
            raise AssertionError
        if ("group2") not in (result):
            raise AssertionError

        # Check structure of results
        for group_results in result.values():
            if ("evppi") not in (group_results):
                raise AssertionError
            if ("evppi_as_percentage_of_total_variance") not in (group_results):
                raise AssertionError
            if ("parameters") not in (group_results):
                raise AssertionError
            if not ((group_results["evppi"]) >= (0)):
                raise AssertionError

    def test_generate_net_benefit_curve_cost_only(self) -> None:
        """Test net benefit curve generation for cost-only analysis."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])

        result = self.analyzer.generate_net_benefit_curve(cost_outcomes)

        require_runtime_instance(result, dict)
        if not (result["cost_only"]):
            raise AssertionError
        if not ((len(result["wtp_values"])) == (0)):
            raise AssertionError
        if not ((len(result["net_benefits"])) == (0)):
            raise AssertionError

    def test_generate_net_benefit_curve_cost_effectiveness(self) -> None:
        """Test net benefit curve generation for cost-effectiveness analysis."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])

        result = self.analyzer.generate_net_benefit_curve(
            cost_outcomes,
            effectiveness_outcomes,
        )

        require_runtime_instance(result, dict)
        if result["cost_only"]:
            raise AssertionError
        if ("wtp_values") not in (result):
            raise AssertionError
        if ("net_benefits") not in (result):
            raise AssertionError
        if not ((len(result["wtp_values"])) > (0)):
            raise AssertionError
        if not ((len(result["net_benefits"])) > (0)):
            raise AssertionError
        if not ((len(result["wtp_values"])) == (len(result["net_benefits"]))):
            raise AssertionError

    def test_generate_ceac(self) -> None:
        """Test CEAC generation."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])

        result = self.analyzer.generate_ceac(cost_outcomes, effectiveness_outcomes)

        require_runtime_instance(result, dict)
        if ("wtp_values") not in (result):
            raise AssertionError
        if ("ceac_probabilities") not in (result):
            raise AssertionError
        if not ((len(result["wtp_values"])) > (0)):
            raise AssertionError
        if not ((len(result["ceac_probabilities"])) > (0)):
            raise AssertionError
        if not ((len(result["wtp_values"])) == (len(result["ceac_probabilities"]))):
            raise AssertionError

    @patch("genomics_microcosting.voi_analysis.PSAAnalyzer")
    def test_generate_voi_report(self, mock_psa_analyzer: Mock) -> None:
        """Test VOI report generation."""
        # Mock the PSA analyzer
        mock_psa_instance = Mock()
        mock_psa_analyzer.return_value = mock_psa_instance

        # Mock the Monte Carlo simulation results
        mock_simulation_results = {
            "labour_cost": np.array([750, 800, 850]),
            "equipment_cost": np.array([500, 600, 700]),
            "consumable_cost": np.array([250, 300, 350]),
        }
        mock_psa_instance.perform_monte_carlo_simulation.return_value = (
            mock_simulation_results
        )

        # Mock the cost outcomes calculation
        mock_psa_instance.calculate_cost_outcomes.return_value = np.array(
            [1500, 1700, 1900],
        )

        # Mock loading VOI parameters
        self.mock_data_manager.load_sheet.return_value = None

        # Generate report
        report = self.analyzer.generate_voi_report(iterations=3)

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Value of Information") not in (report):
            raise AssertionError
        if ("EVPI") not in (report):
            raise AssertionError
        if ("EVPPI") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
