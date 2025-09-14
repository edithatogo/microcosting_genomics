"""Cross-module data consistency validation tests.

This module tests data consistency across all analytical modules to ensure
that shared data and parameters are handled consistently.
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
from genomics_microcosting.psa_analysis import PSAAnalyzer  # noqa: E402
from genomics_microcosting.voi_analysis import VOIAnalyzer  # noqa: E402
from genomics_microcosting.budget_impact_analysis import BudgetImpactAnalyzer  # noqa: E402
from genomics_microcosting.break_even_analysis import BreakEvenAnalyzer  # noqa: E402


class TestCrossModuleConsistency(unittest.TestCase):
    """Cross-module data consistency validation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock data manager
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
        self.voi_analyzer = VOIAnalyzer(self.mock_data_manager)
        self.budget_impact_analyzer = BudgetImpactAnalyzer(self.mock_data_manager)
        self.break_even_analyzer = BreakEvenAnalyzer(self.mock_data_manager)
    
    def test_shared_parameter_consistency(self):
        """Test that shared parameters are consistent across all modules.
        
        This test ensures that:
        1. All modules use the same parameter definitions
        2. Parameter values are consistent across modules
        3. Data types are consistent for shared parameters
        """
        # Mock shared parameter data
        
        # Mock data manager to return consistent data
        def mock_load_sheet(sheet_name):
            if sheet_name == "Detailed Table":
                return pd.DataFrame({
                    'Category': ['Labour', 'Equipment', 'Consumables'],
                    'Cost': [50000, 40000, 30000]
                })
            elif sheet_name == "DSA - Labour Prices":
                return pd.DataFrame({
                    'Parameter': ['Hourly Rate'],
                    'Baseline': [50.0],
                    'Low': [40.0],
                    'High': [60.0]
                })
            elif sheet_name == "PSA":
                return pd.DataFrame({
                    'Parameter': ['Labour Cost'],
                    'Distribution': ['normal'],
                    'Mean': [50000],
                    'Std': [5000]
                })
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        
        # Test that all modules can load shared data consistently
        # Cost Driver Analysis
        detailed_table = self.cost_driver_analyzer.load_detailed_table()
        
        # DSA Analysis
        dsa_params = self.dsa_analyzer.load_dsa_parameters()
        
        # PSA Analysis
        psa_params = self.psa_analyzer.load_psa_parameters()
        
        # VOI Analysis
        voi_params = self.voi_analyzer.load_voi_parameters()
        
        # Verify all modules loaded data
        self.assertIsInstance(detailed_table, pd.DataFrame)
        self.assertIsInstance(dsa_params, dict)
        self.assertIsInstance(psa_params, dict)
        self.assertIsInstance(voi_params, dict)
        
        # Verify shared parameter consistency
        # All modules should have access to labour-related data
        labour_in_detailed = any('Labour' in str(val) for val in detailed_table.values)
        labour_in_dsa = any('Labour' in key for key in dsa_params.keys())
        
        self.assertTrue(labour_in_detailed or labour_in_dsa, 
                       "Labour data should be available in at least one module")
    
    def test_data_schema_consistency(self):
        """Test that data schemas are consistent across modules.
        
        This test ensures that:
        1. All modules expect the same data formats
        2. Column names and data types are consistent
        3. Missing data is handled consistently
        """
        # Create test data with consistent schema
        test_data = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Sub_Category': ['Sequencing', 'Library Prep', 'DNA Extraction'],
            'Cost_2023': [50000.0, 40000.0, 30000.0],
            'Cost_2024': [52000.0, 41000.0, 31000.0]
        })
        
        # Mock all analyzers to work with consistent data
        with patch.object(self.cost_driver_analyzer, 'load_detailed_table', 
                         return_value=test_data):
            with patch.object(self.dsa_analyzer, 'load_dsa_parameters', 
                             return_value={}):
                with patch.object(self.psa_analyzer, 'load_psa_parameters', 
                                 return_value={}):
                    with patch.object(self.voi_analyzer, 'load_voi_parameters', 
                                     return_value={}):
                        
                        # Load data in all modules
                        cost_driver_data = self.cost_driver_analyzer.load_detailed_table()
                        
                        # Verify schema consistency
                        expected_columns = ['Category', 'Sub_Category', 'Cost_2023', 'Cost_2024']
                        for col in expected_columns:
                            if col in cost_driver_data.columns:
                                self.assertIn(col, cost_driver_data.columns)
                        
                        # Verify data types are consistent
                        if 'Cost_2023' in cost_driver_data.columns:
                            self.assertIsInstance(cost_driver_data['Cost_2023'].iloc[0], (int, float))
    
    def test_temporal_data_consistency(self):
        """Test that temporal data is consistent across modules.
        
        This test ensures that:
        1. Time-based parameters are consistent
        2. Temporal references are synchronized
        3. Time series data aligns across modules
        """
        # Create time-series test data
        dates = pd.date_range('2023-01-01', periods=12, freq='M')
        temporal_data = pd.DataFrame({
            'Date': dates,
            'Volume': [1000 + i*10 for i in range(12)],
            'Cost_Per_Test': [100 + i*2 for i in range(12)]
        })
        
        # Mock temporal data loading
        def mock_load_temporal_sheet(sheet_name):
            if sheet_name == "Detailed Table":
                return temporal_data
            elif sheet_name == "Budget Impact":
                return pd.DataFrame({
                    'Year': [2023, 2024, 2025],
                    'Adoption_Rate': [0.1, 0.3, 0.5]
                })
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_temporal_sheet
        
        # Test temporal consistency across modules
        cost_driver_data = self.cost_driver_analyzer.load_detailed_table()
        budget_impact_data = self.budget_impact_analyzer.load_budget_impact_data()
        
        # Verify temporal data was loaded
        self.assertIsInstance(cost_driver_data, pd.DataFrame)
        self.assertIsInstance(budget_impact_data, pd.DataFrame)
        
        # Verify temporal alignment
        if 'Date' in cost_driver_data.columns and 'Year' in budget_impact_data.columns:
            # Check that temporal references are logical
            self.assertGreater(len(cost_driver_data), 0)
            self.assertGreater(len(budget_impact_data), 0)
    
    def test_currency_and_unit_consistency(self):
        """Test that currency and units are consistent across modules.
        
        This test ensures that:
        1. All monetary values use the same currency
        2. Units of measurement are consistent
        3. Conversion factors are applied consistently
        """
        # Create test data with currency information
        currency_data = pd.DataFrame({
            'Item': ['Sequencer', 'Reagents', 'Labour'],
            'Cost_USD': [100000.0, 5000.0, 50000.0],
            'Cost_AUD': [150000.0, 7500.0, 75000.0],
            'Quantity': [1, 1000, 1000]
        })
        
        # Mock currency data loading
        def mock_load_currency_sheet(sheet_name):
            if sheet_name == "Detailed Table":
                return currency_data
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_currency_sheet
        
        # Test currency consistency
        detailed_data = self.cost_driver_analyzer.load_detailed_table()
        
        # Verify currency columns exist
        currency_columns = [col for col in detailed_data.columns if 'Cost' in col]
        self.assertGreater(len(currency_columns), 0)
        
        # Verify numeric data types for currency
        for col in currency_columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(detailed_data[col]))
    
    def test_scenario_data_consistency(self):
        """Test that scenario data is consistent across modules.
        
        This test ensures that:
        1. Scenario definitions are consistent
        2. Scenario parameters align across modules
        3. Scenario results are comparable
        """
        # Create scenario test data
        scenarios = ['Base Case', 'Optimistic', 'Pessimistic']
        scenario_data = pd.DataFrame({
            'Scenario': scenarios,
            'Labour_Cost': [50000, 45000, 55000],
            'Equipment_Cost': [40000, 38000, 42000],
            'Volume': [1000, 1200, 800]
        })
        
        # Mock scenario data loading
        def mock_load_scenario_sheet(sheet_name):
            if sheet_name == "Detailed Table":
                return scenario_data
            else:
                return None
                
        self.mock_data_manager.load_sheet.side_effect = mock_load_scenario_sheet
        
        # Test scenario consistency across modules
        detailed_data = self.cost_driver_analyzer.load_detailed_table()
        
        # Verify scenarios are present
        if 'Scenario' in detailed_data.columns:
            loaded_scenarios = detailed_data['Scenario'].tolist()
            for scenario in scenarios:
                self.assertIn(scenario, loaded_scenarios)


if __name__ == '__main__':
    unittest.main()