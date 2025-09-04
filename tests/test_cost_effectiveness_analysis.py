"""Test cases for the Cost-Effectiveness Analysis module."""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.unimelb_phd_phase_1.cost_effectiveness_analysis import CostEffectivenessAnalyzer
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestCostEffectivenessAnalyzer(unittest.TestCase):
    """Test cases for the CostEffectivenessAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = CostEffectivenessAnalyzer(self.mock_data_manager)

    def test_init(self):
        """Test CostEffectivenessAnalyzer initialization."""
        self.assertIsInstance(self.analyzer, CostEffectivenessAnalyzer)
        self.assertEqual(self.analyzer.data_manager, self.mock_data_manager)

    def test_load_cost_effectiveness_parameters(self):
        """Test loading cost-effectiveness parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None
        
        result = self.analyzer.load_cost_effectiveness_parameters()
        self.assertIsInstance(result, dict)
        # Should return an empty dict since all loads return None
        self.assertEqual(len(result), 0)

    def test_calculate_cost_per_diagnostic_yield(self):
        """Test cost per diagnostic yield calculation."""
        # Test normal case
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=0.3
        )
        
        # Cost per diagnostic yield = Cost per test / Diagnostic yield rate
        # = 3000 / 0.3 = 10000
        self.assertEqual(result, 10000.0)
        
        # Test case with zero diagnostic yield rate
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=0.0
        )
        
        # Should return infinity when diagnostic yield rate is zero
        self.assertEqual(result, float('inf'))
        
        # Test case with negative diagnostic yield rate
        result = self.analyzer.calculate_cost_per_diagnostic_yield(
            cost_per_test=3000.0,
            diagnostic_yield_rate=-0.1
        )
        
        # Should return infinity when diagnostic yield rate is negative
        self.assertEqual(result, float('inf'))

    def test_compare_cost_effectiveness_across_models(self):
        """Test cost-effectiveness comparison across models."""
        model_data = {
            'Test Model': {
                'cost_per_test': 1000.0,
                'diagnostic_yield_rate': 0.2,
                'turnaround_time': 5
            }
        }
        
        result = self.analyzer.compare_cost_effectiveness_across_models(model_data)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIn('Model', result.columns)
        self.assertIn('Cost_Per_Test', result.columns)
        self.assertIn('Diagnostic_Yield_Rate', result.columns)
        self.assertIn('Turnaround_Time', result.columns)
        self.assertIn('Cost_Per_Diagnostic_Yield', result.columns)
        self.assertIn('Efficiency_Score', result.columns)
        
        # Check calculations
        first_row = result.iloc[0]
        self.assertEqual(first_row['Model'], 'Test Model')
        self.assertEqual(first_row['Cost_Per_Test'], 1000.0)
        self.assertEqual(first_row['Diagnostic_Yield_Rate'], 0.2)
        self.assertEqual(first_row['Turnaround_Time'], 5)
        self.assertEqual(first_row['Cost_Per_Diagnostic_Yield'], 5000.0)  # 1000 / 0.2
        self.assertAlmostEqual(first_row['Efficiency_Score'], 0.00004, places=8)  # 1 / (5000 * 5)

    def test_calculate_technical_efficiency_metrics(self):
        """Test technical efficiency metrics calculation."""
        result = self.analyzer.calculate_technical_efficiency_metrics(
            observed_output=100,
            observed_input=200,
            best_practice_output=120,
            best_practice_input=180
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('technical_efficiency', result)
        self.assertIn('cost_efficiency', result)
        self.assertIn('observed_output', result)
        self.assertIn('observed_input', result)
        self.assertIn('best_practice_output', result)
        self.assertIn('best_practice_input', result)
        
        # Check calculations
        # Technical efficiency = (Observed output / Best practice output) / 
        #                        (Observed input / Best practice input)
        # = (100 / 120) / (200 / 180) = (0.8333) / (1.1111) = 0.75
        self.assertAlmostEqual(result['technical_efficiency'], 0.75, places=4)
        
        # Cost efficiency = Observed cost / Best practice cost
        # = 200 / 180 = 1.1111
        self.assertAlmostEqual(result['cost_efficiency'], 1.1111, places=4)

    def test_assess_productivity_improvements(self):
        """Test productivity improvements assessment."""
        baseline_data = {
            'tests_completed': 800,
            'total_cost': 1600000,
            'total_time': 30
        }
        
        current_data = {
            'tests_completed': 1000,
            'total_cost': 1800000,
            'total_time': 30
        }
        
        result = self.analyzer.assess_productivity_improvements(baseline_data, current_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('test_volume_improvement_pct', result)
        self.assertIn('cost_efficiency_improvement_pct', result)
        self.assertIn('productivity_improvement_pct', result)
        self.assertIn('cost_per_test_improvement_pct', result)
        
        # Check calculations
        # Test volume improvement = ((1000 - 800) / 800) * 100 = 25%
        self.assertAlmostEqual(result['test_volume_improvement_pct'], 25.0, places=10)
        
        # Cost efficiency improvement = ((1600000 - 1800000) / 1600000) * 100 = -12.5%
        self.assertAlmostEqual(result['cost_efficiency_improvement_pct'], -12.5, places=10)
        
        # Baseline productivity = 800 / 30 = 26.6667
        # Current productivity = 1000 / 30 = 33.3333
        # Productivity improvement = ((33.3333 - 26.6667) / 26.6667) * 100 = 25%
        self.assertAlmostEqual(result['productivity_improvement_pct'], 25.0, places=10)
        
        # Baseline cost per test = 1600000 / 800 = 2000
        # Current cost per test = 1800000 / 1000 = 1800
        # Cost per test improvement = ((2000 - 1800) / 2000) * 100 = 10%
        self.assertAlmostEqual(result['cost_per_test_improvement_pct'], 10.0, places=10)

    def test_perform_incremental_cost_effectiveness_analysis(self):
        """Test incremental cost-effectiveness analysis."""
        result = self.analyzer.perform_incremental_cost_effectiveness_analysis(
            intervention_cost=5000.0,
            intervention_effectiveness=0.5,
            comparator_cost=3000.0,
            comparator_effectiveness=0.3
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('incremental_cost', result)
        self.assertIn('incremental_effectiveness', result)
        self.assertIn('icer', result)
        self.assertIn('is_intervention_dominant', result)
        self.assertIn('is_comparator_dominant', result)
        
        # Check calculations
        # Incremental cost = 5000 - 3000 = 2000
        self.assertEqual(result['incremental_cost'], 2000.0)
        
        # Incremental effectiveness = 0.5 - 0.3 = 0.2
        self.assertEqual(result['incremental_effectiveness'], 0.2)
        
        # ICER = 2000 / 0.2 = 10000
        self.assertEqual(result['icer'], 10000.0)
        
        # Intervention is not dominant (more costly and more effective)
        self.assertFalse(result['is_intervention_dominant'])
        
        # Comparator is not dominant (less costly and less effective)
        self.assertFalse(result['is_comparator_dominant'])

    def test_generate_cost_effectiveness_report(self):
        """Test cost-effectiveness report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None
        
        # Generate report
        report = self.analyzer.generate_cost_effectiveness_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Cost-Effectiveness Analysis", report)
        self.assertIn("Cost-Effectiveness Comparison Across Models", report)


if __name__ == '__main__':
    unittest.main()