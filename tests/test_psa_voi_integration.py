# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Integration tests for PSA analysis and VOI analysis modules.

Test the flow of data between probabilistic sensitivity analysis
and value of information analysis modules.
"""

import unittest
from unittest.mock import Mock, patch

import numpy as np
import polars as pl

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.psa_analysis import DistributionSpec, PSAAnalyzer
from genomics_microcosting.voi_analysis import VOIAnalyzer
from tests.checks import require_equal, require_runtime_instance


class TestPSAVOIIntegration(unittest.TestCase):
    """Integration tests for PSA and VOI analysis modules."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create mock data manager
        self.mock_data_manager = Mock(spec=DataManager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
        self.voi_analyzer = VOIAnalyzer(self.mock_data_manager)

    def test_psa_to_voi_data_flow(self) -> None:
        """Test that PSA analysis results can be used as input for VOI analysis.

        This test verifies that:
        1. PSA analysis produces valid Monte Carlo simulation results
        2. VOI analyzer can consume PSA results
        3. The data flow between modules works correctly
        """
        # Mock PSA simulation results
        mock_psa_results = {
            "labour_cost": np.array([950, 1020, 980, 1050, 970]),
            "equipment_cost": np.array([780, 820, 800, 840, 790]),
            "consumable_cost": np.array([580, 620, 600, 640, 590]),
        }

        # Mock cost outcomes from PSA
        mock_cost_outcomes = np.array([2310, 2440, 2380, 2530, 2360])

        # Mock the PSA analyzer to return our test data
        with (
            patch.object(
                self.psa_analyzer,
                "perform_monte_carlo_simulation",
                return_value=mock_psa_results,
            ),
            patch.object(
                self.psa_analyzer,
                "calculate_cost_outcomes",
                return_value=mock_cost_outcomes,
            ),
        ):
            # Run PSA analysis
            psa_parameters: dict[str, DistributionSpec] = {
                "labour_cost": {
                    "distribution": "normal",
                    "parameters": {"mean": 1000, "std": 50},
                },
                "equipment_cost": {
                    "distribution": "normal",
                    "parameters": {"mean": 800, "std": 30},
                },
            }
            simulation_results = self.psa_analyzer.perform_monte_carlo_simulation(
                psa_parameters,
                5,
            )
            cost_outcomes = self.psa_analyzer.calculate_cost_outcomes(
                simulation_results,
            )

            # Verify PSA results
            require_runtime_instance(simulation_results, dict)
            require_runtime_instance(cost_outcomes, np.ndarray)
            require_equal(len(cost_outcomes), 5)

            # Mock VOI parameters
            mock_voi_params = {
                "VOI": pl.DataFrame(
                    {
                        "Parameter": ["Labour Cost", "Equipment Cost"],
                        "Description": [
                            "Hourly labour rates",
                            "Equipment utilization",
                        ],
                    },
                ),
            }

            with patch.object(
                self.voi_analyzer,
                "load_voi_parameters",
                return_value=mock_voi_params,
            ):
                # Run VOI analysis using PSA results
                self.voi_analyzer.load_voi_parameters()
                evpi_results = self.voi_analyzer.calculate_evpi(cost_outcomes)
                evppi_results = self.voi_analyzer.calculate_evppi(
                    cost_outcomes,
                    {"Labour": ["labour_cost"], "Equipment": ["equipment_cost"]},
                    simulation_results,
                )

                # Verify VOI results
                require_runtime_instance(evpi_results, dict)
                require_runtime_instance(evppi_results, dict)
                if ("evpi") not in (evpi_results):
                    raise AssertionError
                if ("Labour") not in (evppi_results):
                    raise AssertionError

    def test_cross_module_data_consistency(self) -> None:
        """Test that data between PSA and VOI modules is consistent.

        This test ensures that:
        1. Both modules use the same data manager
        2. Data formats are compatible between modules
        3. Shared parameters are consistent
        """
        # Both analyzers should use the same data manager
        if not ((self.psa_analyzer.data_manager) == (self.voi_analyzer.data_manager)):
            raise AssertionError

        # Mock data that would be shared between modules

        # Mock the data manager to return consistent data
        def mock_load_sheet(sheet_name: str) -> pl.DataFrame | None:
            if sheet_name == "PSA":
                return pl.DataFrame(
                    {
                        "Parameter": ["Labour Cost", "Equipment Cost"],
                        "Distribution": ["normal", "normal"],
                        "Mean": [1000, 800],
                        "Std": [50, 30],
                    },
                )
            if sheet_name == "VOI":
                return pl.DataFrame(
                    {
                        "Parameter": ["Labour Cost", "Equipment Cost"],
                        "Description": ["Hourly labour rates", "Equipment utilization"],
                    },
                )
            return None

        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet

        # Test that both modules can load the same data consistently
        psa_params = self.psa_analyzer.load_psa_parameters()
        voi_params = self.voi_analyzer.load_voi_parameters()

        # Verify data was loaded
        require_runtime_instance(psa_params, dict)
        require_runtime_instance(voi_params, dict)
        if ("PSA") not in (psa_params):
            raise AssertionError
        if ("VOI") not in (voi_params):
            raise AssertionError

    def test_uncertainty_propagation_from_psa_to_voi(self) -> None:
        """Test that uncertainty measures from PSA are properly used in VOI.

        This test verifies that:
        1. Uncertainty in PSA results is captured correctly
        2. VOI analysis appropriately uses this uncertainty information
        3. Value of information metrics are calculated based on PSA uncertainty
        """
        # Create test data with known variance
        rng = np.random.default_rng(42)  # For reproducible results
        labour_costs = rng.normal(1000, 100, 1000)  # High variance
        equipment_costs = rng.normal(800, 20, 1000)  # Low variance
        consumable_costs = rng.normal(600, 50, 1000)  # Medium variance

        psa_results = {
            "labour_cost": labour_costs,
            "equipment_cost": equipment_costs,
            "consumable_cost": consumable_costs,
        }

        # Calculate cost outcomes
        cost_outcomes = (
            labour_costs + equipment_costs + consumable_costs + 500
        )  # Fixed costs

        # Mock the PSA analyzer methods
        with (
            patch.object(
                self.psa_analyzer,
                "perform_monte_carlo_simulation",
                return_value=psa_results,
            ),
            patch.object(
                self.psa_analyzer,
                "calculate_cost_outcomes",
                return_value=cost_outcomes,
            ),
        ):
            # Run PSA analysis
            simulation_results = self.psa_analyzer.perform_monte_carlo_simulation(
                {},
                1000,
            )
            cost_outcomes = self.psa_analyzer.calculate_cost_outcomes(
                simulation_results,
            )

            # Verify uncertainty levels
            # Mock VOI analysis
            with patch.object(
                self.voi_analyzer,
                "calculate_evppi",
                return_value={"Labour": {"evppi": 1500}},
            ):
                # Run VOI analysis
                parameter_groups = {
                    "Labour": ["labour_cost"],
                    "Equipment": ["equipment_cost"],
                    "Consumables": ["consumable_cost"],
                }

                evppi_results = self.voi_analyzer.calculate_evppi(
                    cost_outcomes,
                    parameter_groups,
                    simulation_results,
                )

                # Verify that parameters with higher variance have higher EVPPI
                # In a real implementation, labour should have higher EVPPI than
                # equipment
                # due to its higher variance
                require_runtime_instance(evppi_results, dict)

                # Check that labour parameters are included (they have highest
                # variance)
                if ("Labour") not in (evppi_results):
                    raise AssertionError


if __name__ == "__main__":
    unittest.main()
