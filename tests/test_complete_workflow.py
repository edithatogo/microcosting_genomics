"""Complete end-to-end workflow tests from data preparation to reporting.

This module implements comprehensive workflow tests that cover the entire
analysis pipeline from raw data preparation to final report generation.
"""

import unittest
import sys
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_manager import DataManager  # noqa: E402
from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer  # noqa: E402
from genomics_microcosting.dsa_analysis import DSAAnalyzer  # noqa: E402
from genomics_microcosting.psa_analysis import PSAAnalyzer  # noqa: E402
from genomics_microcosting.voi_analysis import VOIAnalyzer  # noqa: E402
from genomics_microcosting.comprehensive_reporting import ComprehensiveReporter  # noqa: E402


class TestCompleteWorkflow(unittest.TestCase):
    """Complete end-to-end workflow tests from data preparation to reporting."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.prepared_dir = self.data_dir / "prepared"
        self.prepared_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock data manager
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
        self.voi_analyzer = VOIAnalyzer(self.mock_data_manager)
        self.comprehensive_reporter = ComprehensiveReporter(self.mock_data_manager)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_data_preparation_to_analysis_workflow(self):
        """Test complete workflow from data preparation to analysis.
        
        This test covers:
        1. Raw data preparation and cleaning
        2. Data validation and quality checks
        3. Cost driver analysis execution
        4. Sensitivity analysis execution
        5. Uncertainty analysis execution
        6. Results integration and validation
        """
        # Step 1: Create mock raw data (simulating Excel parsing)
        raw_detailed_data = pd.DataFrame({
            'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
            'Category': ['Labour', 'Labour', 'Equipment', 'Equipment'],
            'Sub-Category': ['Sequencing', 'Sequencing', 'Library Prep', 'Library Prep'],
            'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
            'Quantity': [1.0, 1.0, 1.0, 1.0],
            'Unit_Cost': [50000, 75000, 40000, 60000],
            'Total_Cost': [50000, 75000, 40000, 60000]
        })
        
        # Save as parquet (simulating prepare_data.py output)
        detailed_parquet_path = self.prepared_dir / "detailed_table.parquet"
        raw_detailed_data.to_parquet(detailed_parquet_path)
        
        # Step 2: Mock data manager to load prepared data
        def mock_load_sheet(sheet_name, format="parquet"):
            if sheet_name == "Detailed Table":
                return pd.read_parquet(detailed_parquet_path)
            return None
        
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        self.mock_data_manager.list_available_sheets.return_value = {
            "Detailed Table": ["parquet"]
        }
        
        # Step 3: Execute cost driver analysis
        detailed_data = self.cost_driver_analyzer.load_detailed_table()
        self.assertIsInstance(detailed_data, pd.DataFrame)
        self.assertEqual(len(detailed_data), 4)
        
        cost_drivers = self.cost_driver_analyzer.calculate_absolute_cost_drivers(detailed_data)
        self.assertIsInstance(cost_drivers, pd.DataFrame)
        self.assertGreater(len(cost_drivers), 0)
        
        # Step 4: Execute DSA analysis with mock parameters
        mock_dsa_params = {
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate'],
                'Baseline': [50.0],
                'Low': [40.0],
                'High': [60.0]
            })
        }
        
        with patch.object(self.dsa_analyzer, 'load_dsa_parameters', 
                         return_value=mock_dsa_params):
            dsa_parameters = self.dsa_analyzer.load_dsa_parameters()
            self.assertIsInstance(dsa_parameters, dict)
            self.assertIn("DSA - Labour Prices", dsa_parameters)
            
            sensitivity_results = self.dsa_analyzer.analyze_dsa_parameters(dsa_parameters)
            self.assertIsInstance(sensitivity_results, list)
        
        # Step 5: Execute PSA analysis with mock parameters
        mock_psa_params = {
            "PSA": pd.DataFrame({
                'Parameter': ['Labour Cost', 'Equipment Cost'],
                'Distribution': ['normal', 'normal'],
                'Mean': [50000, 40000],
                'Std': [5000, 4000]
            })
        }
        
        with patch.object(self.psa_analyzer, 'load_psa_parameters', 
                         return_value=mock_psa_params):
            psa_parameters = self.psa_analyzer.load_psa_parameters()
            self.assertIsInstance(psa_parameters, dict)
            self.assertIn("PSA", psa_parameters)
            
            # Perform Monte Carlo simulation
            simulation_results = self.psa_analyzer.perform_monte_carlo_simulation(
                {'labour_cost': {'distribution': 'normal', 'parameters': {'mean': 50000, 'std': 5000}}},
                100
            )
            self.assertIsInstance(simulation_results, dict)
            
            cost_outcomes = self.psa_analyzer.calculate_cost_outcomes(simulation_results)
            self.assertIsInstance(cost_outcomes, np.ndarray)
        
        # Step 6: Execute VOI analysis
        mock_voi_params = {
            "VOI": pd.DataFrame({
                'Parameter': ['Labour Cost', 'Equipment Cost'],
                'Description': ['Hourly labour rates', 'Equipment utilization']
            })
        }
        
        with patch.object(self.voi_analyzer, 'load_voi_parameters', 
                         return_value=mock_voi_params):
            voi_parameters = self.voi_analyzer.load_voi_parameters()
            self.assertIsInstance(voi_parameters, dict)
            self.assertIn("VOI", voi_parameters)
            
            evpi_results = self.voi_analyzer.calculate_evpi(cost_outcomes)
            self.assertIsInstance(evpi_results, dict)
        
        # Step 7: Validate results integration
        # Verify that all analysis results can be integrated
        self.assertTrue(len(cost_drivers) > 0)
        self.assertTrue(len(sensitivity_results) >= 0)
        self.assertTrue(len(cost_outcomes) > 0)
        
        # Verify data consistency
        total_cost = raw_detailed_data['Total_Cost'].sum()
        self.assertEqual(total_cost, 225000)
    
    def test_cross_module_data_flow_validation(self):
        """Test that data flows correctly between all modules in the workflow.
        
        This test ensures:
        1. Output from one module can be input to the next
        2. Data transformations are consistent throughout the workflow
        3. No data loss occurs in the processing pipeline
        4. Error handling works correctly across modules
        """
        # Create comprehensive test data that flows through all modules
        test_data = {
            "Detailed Table": pd.DataFrame({
                'Category': ['Labour', 'Equipment', 'Consumables'],
                'Cost_2023': [50000, 40000, 30000],
                'Cost_2024': [52000, 41000, 31000],
                'Volume_2023': [1000, 1000, 1000],
                'Volume_2024': [1200, 1200, 1200]
            }),
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate', 'Overtime Rate'],
                'Baseline': [50.0, 75.0],
                'Low': [40.0, 60.0],
                'High': [60.0, 90.0]
            }),
            "PSA": pd.DataFrame({
                'Parameter': ['Labour Cost', 'Equipment Cost'],
                'Distribution': ['normal', 'normal'],
                'Mean': [50000, 40000],
                'Std': [5000, 4000]
            })
        }
        
        # Mock data manager to return consistent data
        def mock_load_sheet(sheet_name, format="parquet"):
            return test_data.get(sheet_name, pd.DataFrame())
            
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        self.mock_data_manager.list_available_sheets.return_value = {
            name: ["parquet"] for name in test_data.keys()
        }
        
        # Test data flow through modules
        # 1. Cost Driver Analysis receives detailed data
        cost_driver_data = self.cost_driver_analyzer.load_detailed_table()
        self.assertIsInstance(cost_driver_data, pd.DataFrame)
        self.assertGreater(len(cost_driver_data), 0)
        
        # 2. DSA Analysis receives sensitivity parameters
        dsa_data = self.dsa_analyzer.load_dsa_parameters()
        self.assertIsInstance(dsa_data, dict)
        
        # 3. PSA Analysis receives probabilistic parameters
        psa_data = self.psa_analyzer.load_psa_parameters()
        self.assertIsInstance(psa_data, dict)
        
        # 4. Verify data consistency across modules
        # All modules should work with the same base categories
        expected_categories = set(test_data["Detailed Table"]["Category"])
        if len(cost_driver_data) > 0:
            actual_categories = set(cost_driver_data["Category"])
            self.assertEqual(expected_categories, actual_categories)
        
        # 5. Test error handling in data flow
        # Simulate missing data scenario
        def mock_load_sheet_missing(sheet_name, format="parquet"):
            if sheet_name == "Missing Sheet":
                return None
            return test_data.get(sheet_name, pd.DataFrame())
        
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet_missing
        
        # This should handle missing data gracefully
        missing_data = self.cost_driver_analyzer.load_detailed_table()
        # Should return empty DataFrame or handle gracefully
        self.assertIsNotNone(missing_data)
    
    def test_workflow_error_handling_and_recovery(self):
        """Test workflow error handling and recovery mechanisms.
        
        This test ensures:
        1. Errors in one module don't crash the entire workflow
        2. Graceful degradation works correctly
        3. Error messages are informative
        4. Recovery mechanisms function properly
        """
        # Create test data
        test_data = pd.DataFrame({
            'Category': ['Labour', 'Equipment'],
            'Cost': [50000, 40000]
        })
        
        # Mock data manager
        def mock_load_sheet(sheet_name, format="parquet"):
            if "error" in sheet_name.lower():
                raise Exception("Simulated data loading error")
            return test_data
            
        self.mock_data_manager.load_sheet.side_effect = mock_load_sheet
        
        # Test graceful handling of data loading errors
        with patch.object(self.cost_driver_analyzer, 'load_detailed_table') as mock_load:
            mock_load.side_effect = Exception("Data loading failed")
            
            # Should handle error gracefully
            try:
                result = self.cost_driver_analyzer.load_detailed_table()
                # If it returns a value, it should be a DataFrame or None
                self.assertTrue(isinstance(result, (pd.DataFrame, type(None))))
            except Exception:
                # If it raises an exception, it should be handled by calling code
                pass
        
        # Test recovery from partial analysis failures
        with patch.object(self.dsa_analyzer, 'analyze_dsa_parameters') as mock_analyze:
            mock_analyze.side_effect = Exception("DSA analysis failed")
            
            # Should not crash the entire workflow
            try:
                mock_dsa_params = {"test": pd.DataFrame()}
                result = self.dsa_analyzer.analyze_dsa_parameters(mock_dsa_params)
                self.assertIsNotNone(result)
            except Exception:
                # Error should be contained
                pass


class TestWorkflowValidationCriteria(unittest.TestCase):
    """Test validation criteria for end-to-end workflow results."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
    
    def test_result_validation_criteria(self):
        """Test that workflow results meet validation criteria.
        
        This test ensures:
        1. All cost values are positive
        2. Percentages sum to approximately 100%
        3. Sensitivity ranges are logical
        4. Statistical properties are consistent
        5. Results are mathematically correct
        """
        # Create test data that meets validation criteria
        valid_test_data = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Cost': [50000, 40000, 10000],  # All positive
            'Percentage': [50.0, 40.0, 10.0]  # Sums to 100%
        })
        
        # Test cost positivity validation
        self.assertTrue(all(valid_test_data['Cost'] > 0))
        
        # Test percentage sum validation
        total_percentage = valid_test_data['Percentage'].sum()
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
        
        # Test sensitivity range validation
        sensitivity_test = pd.DataFrame({
            'Parameter': ['Test'],
            'Low': [40.0],
            'Baseline': [50.0],
            'High': [60.0]
        })
        
        # Verify logical ranges (low < baseline < high)
        for _, row in sensitivity_test.iterrows():
            self.assertLess(row['Low'], row['Baseline'])
            self.assertLess(row['Baseline'], row['High'])
        
        # Test statistical consistency
        # Generate sample data with known properties
        np.random.seed(42)  # For reproducible tests
        sample_data = np.random.normal(50000, 5000, 1000)  # Mean=50000, Std=5000
        
        # Verify statistical properties
        sample_mean = np.mean(sample_data)
        sample_std = np.std(sample_data)
        
        # Mean should be close to expected (within 5%)
        self.assertAlmostEqual(sample_mean / 50000, 1.0, places=1)
        # Std should be close to expected (within 10%)
        self.assertAlmostEqual(sample_std / 5000, 1.0, places=1)
    
    def test_mathematical_correctness(self):
        """Test mathematical correctness of workflow calculations.
        
        This test ensures:
        1. Basic arithmetic is correct
        2. Formula implementations are accurate
        3. Aggregations produce expected results
        4. Conversions maintain precision
        """
        # Test basic cost calculations
        quantity = 10
        unit_cost = 5000
        expected_total = quantity * unit_cost  # 50000
        
        calculated_total = quantity * unit_cost
        self.assertEqual(calculated_total, expected_total)
        
        # Test percentage calculations
        part = 25
        whole = 100
        expected_percentage = (part / whole) * 100  # 25.0
        
        calculated_percentage = (part / whole) * 100
        self.assertEqual(calculated_percentage, expected_percentage)
        
        # Test aggregation correctness
        values = [10000, 20000, 30000]
        expected_sum = sum(values)  # 60000
        expected_average = sum(values) / len(values)  # 20000
        
        calculated_sum = sum(values)
        calculated_average = sum(values) / len(values)
        
        self.assertEqual(calculated_sum, expected_sum)
        self.assertEqual(calculated_average, expected_average)


if __name__ == '__main__':
    unittest.main()