"""Test cases for the Budget Impact Analysis module."""

import unittest
import pandas as pd
from unittest.mock import Mock

from src.genomics_microcosting.budget_impact_analysis import BudgetImpactAnalyzer
from src.genomics_microcosting.data_manager import DataManager


class TestBudgetImpactAnalyzer(unittest.TestCase):
    """Test cases for the BudgetImpactAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BudgetImpactAnalyzer(self.mock_data_manager)

    def test_init(self):
        """Test BudgetImpactAnalyzer initialization."""
        self.assertIsInstance(self.analyzer, BudgetImpactAnalyzer)
        self.assertEqual(self.analyzer.data_manager, self.mock_data_manager)

    def test_load_budget_parameters(self):
        """Test loading budget parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None
        
        result = self.analyzer.load_budget_parameters()
        self.assertIsInstance(result, dict)
        # Should return an empty dict since all loads return None
        self.assertEqual(len(result), 0)

    def test_perform_volume_sensitivity_analysis(self):
        """Test volume sensitivity analysis."""
        # Test with default parameters
        result = self.analyzer.perform_volume_sensitivity_analysis()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('Volume', result.columns)
        self.assertIn('Total_Cost', result.columns)
        self.assertIn('Volume_Change_Pct', result.columns)
        self.assertIn('Cost_Change_Pct', result.columns)
        
        # Check that base volume (1000) has 0% change
        base_row = result[result['Volume'] == 1000]
        self.assertEqual(len(base_row), 1)
        self.assertEqual(base_row['Volume_Change_Pct'].iloc[0], 0.0)
        self.assertEqual(base_row['Cost_Change_Pct'].iloc[0], 0.0)

    def test_perform_volume_sensitivity_analysis_custom(self):
        """Test volume sensitivity analysis with custom parameters."""
        result = self.analyzer.perform_volume_sensitivity_analysis(
            base_volume=500,
            volume_range=[400, 500, 600],
            cost_per_test=1500.0
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn(500, result['Volume'].values)
        self.assertEqual(result[result['Volume'] == 500]['Total_Cost'].iloc[0], 500 * 1500.0)

    def test_perform_time_horizon_analysis(self):
        """Test time horizon analysis."""
        result = self.analyzer.perform_time_horizon_analysis()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 5)  # Default 5 years
        self.assertIn('Year', result.columns)
        self.assertIn('Volume', result.columns)
        self.assertIn('Cost_Per_Test', result.columns)
        self.assertIn('Total_Cost', result.columns)
        
        # Check that values change over time due to growth and cost reduction
        self.assertGreater(result.iloc[-1]['Volume'], result.iloc[0]['Volume'])
        self.assertLess(result.iloc[-1]['Cost_Per_Test'], result.iloc[0]['Cost_Per_Test'])

    def test_perform_time_horizon_analysis_custom(self):
        """Test time horizon analysis with custom parameters."""
        result = self.analyzer.perform_time_horizon_analysis(
            initial_volume=800,
            growth_rate=0.1,
            years=3,
            cost_per_test=1800.0,
            annual_cost_reduction=0.01
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.iloc[0]['Year'], 1)
        self.assertEqual(result.iloc[0]['Volume'], 800)

    def test_perform_scenario_analysis(self):
        """Test scenario analysis."""
        result = self.analyzer.perform_scenario_analysis()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('Scenario', result.columns)
        self.assertIn('Volume', result.columns)
        self.assertIn('Cost_Per_Test', result.columns)
        self.assertIn('Total_Cost', result.columns)

    def test_perform_scenario_analysis_custom(self):
        """Test scenario analysis with custom scenarios."""
        custom_scenarios = {
            'Low Volume': {
                'volume': 500,
                'cost_per_test': 2500.0
            },
            'High Volume': {
                'volume': 2000,
                'cost_per_test': 1500.0
            }
        }
        
        result = self.analyzer.perform_scenario_analysis(custom_scenarios)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('Low Volume', result['Scenario'].values)
        self.assertIn('High Volume', result['Scenario'].values)

    def test_calculate_economies_of_scale(self):
        """Test economies of scale calculation."""
        volume_range = [500, 1000, 1500]
        result = self.analyzer.calculate_economies_of_scale(volume_range)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn('Volume', result.columns)
        self.assertIn('Fixed_Costs', result.columns)
        self.assertIn('Variable_Costs', result.columns)
        self.assertIn('Total_Costs', result.columns)
        self.assertIn('Cost_Per_Test', result.columns)
        
        # Check that cost per test decreases with volume (economies of scale)
        self.assertGreater(result.iloc[0]['Cost_Per_Test'], result.iloc[-1]['Cost_Per_Test'])

    def test_generate_budget_impact_report(self):
        """Test budget impact report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None
        
        # Generate report
        report = self.analyzer.generate_budget_impact_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Budget Impact Analysis", report)
        self.assertIn("Volume Sensitivity Analysis", report)
        self.assertIn("Time Horizon Analysis", report)
        self.assertIn("Scenario Analysis", report)


if __name__ == '__main__':
    unittest.main()