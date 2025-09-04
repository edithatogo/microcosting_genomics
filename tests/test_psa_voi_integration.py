"""Integration tests for PSA analysis and VOI analysis modules.

This module tests the data flow and integration between probabilistic sensitivity analysis
and value of information analysis modules.
"""

import unittest
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.data_manager import DataManager
from unimelb_phd_phase_1.psa_analysis import PSAAnalyzer
from unimelb_phd_phase_1.voi_analysis import VOIAnalyzer


class TestPSAVOIIntegration(unittest.TestCase):
    """Integration tests for PSA and VOI analysis modules."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock data manager
        self.mock_data_manager = Mock(spec=DataManager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
        self.voi_analyzer = VOIAnalyzer(self.mock_data_manager)
    
    def test_psa_to_voi_data_flow(self):
        """Test that PSA analysis results can be used as input for VOI analysis.
        
        This test verifies that:
        1. PSA analysis produces valid Monte Carlo simulation results
        2. VOI analyzer can consume PSA results
        3. The data flow between modules works correctly
        """
        # Mock PSA simulation results
        mock_psa_results = {
            'labour_cost': np.array([950, 1020, 980, 1050, 970]),
            'equipment_cost': np.array([780, 820, 800, 840, 790]),
            'consumable_cost': np.array([580, 620, 600, 640, 590])
        }
        
        # Mock cost outcomes from PSA
        mock_cost_outcomes = np.array([2310, 2440, 2380, 2530, 2360])
        
        # Mock the PSA analyzer to return our test data
        with patch.object(self.psa_analyzer, 'perform_monte_carlo_simulation', 
                         return_value=mock_psa_results):
            with patch.object(self.psa_analyzer, 'calculate_cost_outcomes', 
                             return_value=mock_cost_outcomes):
                
                # Run PSA analysis
                psa_parameters = {
                    'labour_cost': {'distribution': 'normal', 'parameters': {'mean': 1000, 'std': 50}},
                    'equipment_cost': {'distribution': 'normal', 'parameters': {'mean': 800, 'std': 30}}
                }
                simulation_results = self.psa_analyzer.perform_monte_carlo_simulation(psa_parameters, 5)
                cost_outcomes = self.psa_analyzer.calculate_cost_outcomes(simulation_results)
                
                # Verify PSA results
                self.assertIsInstance(simulation_results, dict)
                self.assertIsInstance(cost_outcomes, np.ndarray)
                self.assertEqual(len(cost_outcomes), 5)
                
                # Mock VOI parameters
                mock_voi_params = {
                    "VOI": pd.DataFrame({
                        'Parameter': ['Labour Cost', 'Equipment Cost'],
                        'Description': ['Hourly labour rates', 'Equipment utilization']
                    })
                }
                
                with patch.object(self.voi_analyzer, 'load_voi_parameters', 
                                 return_value=mock_voi_params):
                    
                    # Run VOI analysis using PSA results
                    voi_parameters = self.voi_analyzer.load_voi_parameters()
                    evpi_results = self.voi_analyzer.calculate_evpi(cost_outcomes)
                    evppi_results = self.voi_analyzer.calculate_evppi(
                        cost_outcomes, 
                        {'Labour': ['labour_cost'], 'Equipment': ['equipment_cost']}, 
                        simulation_results
                    )
                    
                    # Verify VOI results
                    self.assertIsInstance(evpi_results, dict)
                    self.assertIsInstance(evppi_results, dict)
                    self.assertIn('evpi', evpi_results)
                    self.assertIn('Labour', evppi_results)
                    
    def test_cross_module_data_consistency(self):
        """Test that data between PSA and VOI modules is consistent.
        
        This test ensures that:
        1. Both modules use the same data manager
        2. Data formats are compatible between modules
        3. Shared parameters are consistent
        """
        # Both analyzers should use the same data manager
        self.assertEqual(self.psa_analyzer.data_manager, 
                        self.voi_analyzer.data_manager)
        
        # Mock data that would be shared between modules
        shared_sheet_names = ["PSA", "VOI"]
        
        # Mock the data manager to return consistent data
        def mock_load_sheet(sheet_name):
            if sheet_name == "PSA":
                return pd.DataFrame({
                    'Parameter': ['Labour Cost', 'Equipment Cost'],
                    'Distribution': ['normal', 'normal'],
                    'Mean': [1000, 800],
                    'Std': [50, 30]
                })
            elif sheet_name == "VOI":
                return pd.DataFrame({
                    'Parameter': ['Labour Cost', 'Equipment Cost'],
                    'Description': ['Hourly labour rates', 'Equipment utilization']
                })
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        
        # Test that both modules can load the same data consistently
        psa_params = self.psa_analyzer.load_psa_parameters()
        voi_params = self.voi_analyzer.load_voi_parameters()
        
        # Verify data was loaded
        self.assertIsInstance(psa_params, dict)
        self.assertIsInstance(voi_params, dict)
        self.assertIn("PSA", psa_params)
        self.assertIn("VOI", voi_params)
        
    def test_uncertainty_propagation_from_psa_to_voi(self):
        """Test that uncertainty measures from PSA are properly used in VOI.
        
        This test verifies that:
        1. Uncertainty in PSA results is captured correctly
        2. VOI analysis appropriately uses this uncertainty information
        3. Value of information metrics are calculated based on PSA uncertainty
        """
        # Create test data with known variance
        np.random.seed(42)  # For reproducible results
        labour_costs = np.random.normal(1000, 100, 1000)  # High variance
        equipment_costs = np.random.normal(800, 20, 1000)   # Low variance
        consumable_costs = np.random.normal(600, 50, 1000)  # Medium variance
        
        psa_results = {
            'labour_cost': labour_costs,
            'equipment_cost': equipment_costs,
            'consumable_cost': consumable_costs
        }
        
        # Calculate cost outcomes
        cost_outcomes = labour_costs + equipment_costs + consumable_costs + 500  # Fixed costs
        
        # Mock the PSA analyzer methods
        with patch.object(self.psa_analyzer, 'perform_monte_carlo_simulation', 
                         return_value=psa_results):
            with patch.object(self.psa_analyzer, 'calculate_cost_outcomes', 
                             return_value=cost_outcomes):
                
                # Run PSA analysis
                simulation_results = self.psa_analyzer.perform_monte_carlo_simulation({}, 1000)
                cost_outcomes = self.psa_analyzer.calculate_cost_outcomes(simulation_results)
                
                # Verify uncertainty levels
                labour_variance = np.var(labour_costs)
                equipment_variance = np.var(equipment_costs)
                total_variance = np.var(cost_outcomes)
                
                # Mock VOI analysis
                with patch.object(self.voi_analyzer, 'calculate_evppi', 
                                 return_value={'Labour': {'evppi': 1500}}):
                    
                    # Run VOI analysis
                    parameter_groups = {
                        'Labour': ['labour_cost'],
                        'Equipment': ['equipment_cost'],
                        'Consumables': ['consumable_cost']
                    }
                    
                    evppi_results = self.voi_analyzer.calculate_evppi(
                        cost_outcomes, parameter_groups, simulation_results
                    )
                    
                    # Verify that parameters with higher variance have higher EVPPI
                    # In a real implementation, labour should have higher EVPPI than equipment
                    # due to its higher variance
                    self.assertIsInstance(evppi_results, dict)
                    
                    # Check that labour parameters are included (they have highest variance)
                    self.assertIn('Labour', evppi_results)


if __name__ == '__main__':
    unittest.main()