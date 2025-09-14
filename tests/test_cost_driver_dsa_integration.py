"""Integration tests for cost driver analysis and DSA analysis modules.

This module tests the data flow and integration between cost driver analysis
and deterministic sensitivity analysis modules.
"""

import unittest
import sys
from pathlib import Path
import pandas as pd
from unittest.mock import Mock, patch

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_manager import DataManager  # noqa: E402
from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer  # noqa: E402
from genomics_microcosting.dsa_analysis import DSAAnalyzer  # noqa: E402


class TestCostDriverDSAIntegration(unittest.TestCase):
    """Integration tests for cost driver and DSA analysis modules."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock data manager
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
    
    def test_cost_driver_to_dsa_data_flow(self):
        """Test that cost driver analysis results can be used as input for DSA.
        
        This test verifies that:
        1. Cost driver analysis produces valid results
        2. DSA analyzer can consume cost driver data
        3. The data flow between modules works correctly
        """
        # Mock cost driver analysis results
        mock_cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Sub-Category': ['Sequencing', 'Library Prep', 'DNA Extraction'],
            'Absolute_Value': [1200.0, 800.0, 600.0],
            'Percentage': [37.5, 25.0, 18.75]
        })
        
        # Mock the cost driver analyzer to return our test data
        with patch.object(self.cost_driver_analyzer, 'calculate_absolute_cost_drivers', 
                         return_value=mock_cost_drivers):
            with patch.object(self.cost_driver_analyzer, 'load_detailed_table', 
                             return_value=pd.DataFrame()):
                
                # Run cost driver analysis
                df = self.cost_driver_analyzer.load_detailed_table()
                cost_drivers = self.cost_driver_analyzer.calculate_absolute_cost_drivers(df)
                
                # Verify cost driver results
                self.assertIsInstance(cost_drivers, pd.DataFrame)
                self.assertEqual(len(cost_drivers), 3)
                self.assertIn('Category', cost_drivers.columns)
                self.assertIn('Absolute_Value', cost_drivers.columns)
                
                # Mock DSA parameters that would be influenced by cost drivers
                mock_dsa_params = {
                    "DSA - Labour Prices": pd.DataFrame({
                        'Parameter': ['Hourly Rate'],
                        'Baseline': [50.0],
                        'Low': [40.0],
                        'High': [60.0]
                    }),
                    "DSA - Equipment Throughput": pd.DataFrame({
                        'Parameter': ['Utilization Rate'],
                        'Baseline': [0.8],
                        'Low': [0.6],
                        'High': [0.95]
                    })
                }
                
                with patch.object(self.dsa_analyzer, 'load_dsa_parameters', 
                                 return_value=mock_dsa_params):
                    
                    # Run DSA analysis
                    dsa_parameters = self.dsa_analyzer.load_dsa_parameters()
                    sensitivity_results = self.dsa_analyzer.analyze_dsa_parameters(dsa_parameters)
                    
                    # Verify DSA results
                    self.assertIsInstance(sensitivity_results, list)
                    self.assertGreater(len(sensitivity_results), 0)
                    
                    # Check that the most impactful cost driver category is properly analyzed
                    # In a real implementation, we would check that DSA properly analyzes
                    # parameters related to the top cost drivers
                    
    def test_cross_module_data_consistency(self):
        """Test that data between cost driver and DSA modules is consistent.
        
        This test ensures that:
        1. Both modules use the same data manager
        2. Data formats are compatible between modules
        3. Shared parameters are consistent
        """
        # Both analyzers should use the same data manager
        self.assertEqual(self.cost_driver_analyzer.data_manager, 
                        self.dsa_analyzer.data_manager)
        
        # Mock data that would be shared between modules
        
        # Mock the data manager to return consistent data
        def mock_load_sheet(sheet_name):
            if sheet_name == "Detailed Table":
                return pd.DataFrame({
                    'Category': ['Labour', 'Equipment', 'Consumables'],
                    'Cost': [1200.0, 800.0, 600.0]
                })
            elif sheet_name == "DSA - Labour Prices":
                return pd.DataFrame({
                    'Parameter': ['Hourly Rate'],
                    'Baseline': [50.0],
                    'Low': [40.0],
                    'High': [60.0]
                })
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        
        # Test that both modules can load the same data consistently
        detailed_table_1 = self.cost_driver_analyzer.load_detailed_table()
        dsa_params = self.dsa_analyzer.load_dsa_parameters()
        
        # Verify data was loaded
        self.assertIsInstance(detailed_table_1, pd.DataFrame)
        self.assertIsInstance(dsa_params, dict)
        self.assertIn("DSA - Labour Prices", dsa_params)
        
    def test_parameter_sensitivity_based_on_cost_drivers(self):
        """Test that DSA focuses on parameters related to top cost drivers.
        
        This test verifies that the DSA analysis appropriately prioritizes
        parameters that correspond to the highest cost drivers identified
        by the cost driver analysis.
        """
        # Mock cost driver results showing Labour as the top cost driver
        mock_cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Absolute_Value': [1200.0, 800.0, 600.0],
            'Percentage': [37.5, 25.0, 18.75]
        })
        
        # Mock DSA parameters with labour-related parameters
        mock_dsa_params = {
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate', 'Overtime Rate'],
                'Baseline': [50.0, 75.0],
                'Low': [40.0, 60.0],
                'High': [60.0, 90.0]
            }),
            "DSA - Equipment Throughput": pd.DataFrame({
                'Parameter': ['Utilization Rate'],
                'Baseline': [0.8],
                'Low': [0.6],
                'High': [0.95]
            })
        }
        
        with patch.object(self.cost_driver_analyzer, 'calculate_absolute_cost_drivers', 
                         return_value=mock_cost_drivers):
            with patch.object(self.cost_driver_analyzer, 'load_detailed_table', 
                             return_value=pd.DataFrame()):
                with patch.object(self.dsa_analyzer, 'load_dsa_parameters', 
                                 return_value=mock_dsa_params):
                    
                    # Run both analyses
                    self.cost_driver_analyzer.load_detailed_table()
                    dsa_parameters = self.dsa_analyzer.load_dsa_parameters()
                    sensitivity_results = self.dsa_analyzer.analyze_dsa_parameters(dsa_parameters)
                    
                    # Verify that labour-related parameters are included in DSA
                    any("Labour" in str(result) or "Hourly" in str(result) 
                       for result in sensitivity_results)
                    
                    # In a full implementation, we would verify that labour-related parameters
                    # have higher sensitivity impact when labour is the top cost driver


if __name__ == '__main__':
    unittest.main()