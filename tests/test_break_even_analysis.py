"""Test cases for the Break-even Analysis module."""

import unittest
import pandas as pd
from unittest.mock import Mock

from src.genomics_microcosting.break_even_analysis import BreakEvenAnalyzer
from src.genomics_microcosting.data_manager import DataManager


class TestBreakEvenAnalyzer(unittest.TestCase):
    """Test cases for the BreakEvenAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BreakEvenAnalyzer(self.mock_data_manager)

    def test_init(self):
        """Test BreakEvenAnalyzer initialization."""
        self.assertIsInstance(self.analyzer, BreakEvenAnalyzer)
        self.assertEqual(self.analyzer.data_manager, self.mock_data_manager)

    def test_load_break_even_parameters(self):
        """Test loading break-even parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None
        
        result = self.analyzer.load_break_even_parameters()
        self.assertIsInstance(result, dict)
        # Should return an empty dict since all loads return None
        self.assertEqual(len(result), 0)

    def test_calculate_break_even_volume(self):
        """Test break-even volume calculation."""
        # Test normal case
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=100.0,
            variable_cost_per_test=50.0
        )
        
        # Break-even volume = Fixed Costs / (Price - Variable Cost)
        # = 100000 / (100 - 50) = 100000 / 50 = 2000
        self.assertEqual(result, 2000.0)
        
        # Test case with zero contribution margin
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=50.0,
            variable_cost_per_test=50.0
        )
        
        # Should return infinity when contribution margin is zero
        self.assertEqual(result, float('inf'))
        
        # Test case with negative contribution margin
        result = self.analyzer.calculate_break_even_volume(
            fixed_costs=100000.0,
            price_per_test=40.0,
            variable_cost_per_test=50.0
        )
        
        # Should return infinity when contribution margin is negative
        self.assertEqual(result, float('inf'))

    def test_calculate_contribution_margin(self):
        """Test contribution margin calculation."""
        result = self.analyzer.calculate_contribution_margin(
            price_per_test=100.0,
            variable_cost_per_test=60.0
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('contribution_margin_per_test', result)
        self.assertIn('contribution_margin_ratio', result)
        self.assertIn('price_per_test', result)
        self.assertIn('variable_cost_per_test', result)
        
        # Check calculations
        self.assertEqual(result['contribution_margin_per_test'], 40.0)  # 100 - 60
        self.assertEqual(result['contribution_margin_ratio'], 40.0)     # (40 / 100) * 100
        self.assertEqual(result['price_per_test'], 100.0)
        self.assertEqual(result['variable_cost_per_test'], 60.0)
        
        # Test with zero price
        result = self.analyzer.calculate_contribution_margin(
            price_per_test=0.0,
            variable_cost_per_test=60.0
        )
        
        self.assertEqual(result['contribution_margin_per_test'], -60.0)
        self.assertEqual(result['contribution_margin_ratio'], 0.0)

    def test_perform_sensitivity_analysis(self):
        """Test sensitivity analysis."""
        result = self.analyzer.perform_sensitivity_analysis(
            fixed_costs=100000.0,
            price_per_test=100.0,
            variable_cost_range=[50.0, 60.0],
            volume_range=[1000, 2000]
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 4)  # 2 variable costs × 2 volumes
        self.assertIn('Variable_Cost_Per_Test', result.columns)
        self.assertIn('Volume', result.columns)
        self.assertIn('Revenue', result.columns)
        self.assertIn('Variable_Costs', result.columns)
        self.assertIn('Fixed_Costs', result.columns)
        self.assertIn('Total_Costs', result.columns)
        self.assertIn('Profit', result.columns)
        self.assertIn('Break_Even_Volume', result.columns)
        
        # Check calculations for first row
        first_row = result.iloc[0]
        self.assertEqual(first_row['Variable_Cost_Per_Test'], 50.0)
        self.assertEqual(first_row['Volume'], 1000)
        self.assertEqual(first_row['Revenue'], 100000.0)  # 100 * 1000
        self.assertEqual(first_row['Variable_Costs'], 50000.0)  # 50 * 1000
        self.assertEqual(first_row['Fixed_Costs'], 100000.0)
        self.assertEqual(first_row['Total_Costs'], 150000.0)  # 100000 + 50000
        self.assertEqual(first_row['Profit'], -50000.0)  # 100000 - 150000
        self.assertEqual(first_row['Break_Even_Volume'], 2000.0)  # 100000 / (100 - 50)

    def test_calculate_minimum_efficient_scale(self):
        """Test minimum efficient scale calculation."""
        result = self.analyzer.calculate_minimum_efficient_scale(
            fixed_costs=100000.0,
            variable_cost_per_test=50.0,
            price_per_test=100.0,
            efficiency_threshold=0.95
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('minimum_efficient_volume', result)
        self.assertIn('break_even_volume', result)
        self.assertIn('cost_per_test_at_efficiency', result)
        self.assertIn('efficiency_threshold', result)
        
        # Check that break-even volume is calculated correctly
        self.assertEqual(result['break_even_volume'], 2000.0)  # 100000 / (100 - 50)
        
        # Check that minimum efficient volume is greater than break-even volume
        self.assertGreater(result['minimum_efficient_volume'], result['break_even_volume'])

    def test_analyze_service_lines(self):
        """Test service line analysis."""
        service_line_data = {
            'Test Service': {
                'fixed_costs': 50000.0,
                'price_per_test': 100.0,
                'variable_cost_per_test': 60.0
            }
        }
        
        result = self.analyzer.analyze_service_lines(service_line_data)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIn('Service_Line', result.columns)
        self.assertIn('Fixed_Costs', result.columns)
        self.assertIn('Price_Per_Test', result.columns)
        self.assertIn('Variable_Cost_Per_Test', result.columns)
        self.assertIn('Break_Even_Volume', result.columns)
        self.assertIn('Contribution_Margin_Per_Test', result.columns)
        self.assertIn('Contribution_Margin_Ratio', result.columns)
        self.assertIn('Minimum_Efficient_Volume', result.columns)
        
        # Check calculations
        first_row = result.iloc[0]
        self.assertEqual(first_row['Service_Line'], 'Test Service')
        self.assertEqual(first_row['Fixed_Costs'], 50000.0)
        self.assertEqual(first_row['Price_Per_Test'], 100.0)
        self.assertEqual(first_row['Variable_Cost_Per_Test'], 60.0)
        self.assertEqual(first_row['Break_Even_Volume'], 1250.0)  # 50000 / (100 - 60)
        self.assertEqual(first_row['Contribution_Margin_Per_Test'], 40.0)  # 100 - 60
        self.assertEqual(first_row['Contribution_Margin_Ratio'], 40.0)     # (40 / 100) * 100

    def test_generate_break_even_report(self):
        """Test break-even report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None
        
        # Generate report
        report = self.analyzer.generate_break_even_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Break-even Analysis", report)
        self.assertIn("Break-even Volume Calculation", report)
        self.assertIn("Contribution Margin Analysis", report)


if __name__ == '__main__':
    unittest.main()