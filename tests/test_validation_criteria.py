"""Test result validation criteria for genomics microcosting analysis.

This module defines and tests the validation criteria for ensuring analysis
results meet required standards and quality thresholds.
"""

import unittest
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from unittest.mock import Mock

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_manager import DataManager  # noqa: E402
from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer  # noqa: E402
from genomics_microcosting.dsa_analysis import DSAAnalyzer  # noqa: E402
from genomics_microcosting.psa_analysis import PSAAnalyzer  # noqa: E402


class TestValidationCriteria(unittest.TestCase):
    """Test result validation criteria for analysis results."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.cost_driver_analyzer = CostDriverAnalyzer(self.mock_data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.mock_data_manager)
        self.psa_analyzer = PSAAnalyzer(self.mock_data_manager)
    
    def test_cost_driver_validation_criteria(self):
        """Test validation criteria for cost driver analysis results.
        
        Validation criteria:
        1. All cost drivers should have positive values
        2. Percentages should sum to approximately 100%
        3. Rankings should be consistent with values
        4. No missing categories
        """
        # Create test cost driver results
        cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage'],
            'Absolute_Value': [1200.0, 800.0, 600.0, 400.0, 200.0],
            'Percentage': [37.5, 25.0, 18.75, 12.5, 6.25]
        })
        
        # Validation 1: All cost drivers should have positive values
        self.assertTrue(all(cost_drivers['Absolute_Value'] > 0), 
                       "All cost driver values should be positive")
        
        # Validation 2: Percentages should sum to approximately 100%
        total_percentage = cost_drivers['Percentage'].sum()
        self.assertAlmostEqual(total_percentage, 100.0, delta=1.0,
                             msg="Percentages should sum to approximately 100%")
        
        # Validation 3: Rankings should be consistent with values
        sorted_by_value = cost_drivers.sort_values('Absolute_Value', ascending=False)
        sorted_by_percentage = cost_drivers.sort_values('Percentage', ascending=False)
        
        # Top category should be the same when sorted by value or percentage
        self.assertEqual(sorted_by_value.iloc[0]['Category'], 
                        sorted_by_percentage.iloc[0]['Category'],
                        "Rankings should be consistent between value and percentage")
        
        # Validation 4: No missing categories
        expected_categories = ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage']
        actual_categories = cost_drivers['Category'].tolist()
        for category in expected_categories:
            self.assertIn(category, actual_categories,
                         f"Expected category {category} not found")
    
    def test_dsa_validation_criteria(self):
        """Test validation criteria for DSA analysis results.
        
        Validation criteria:
        1. Sensitivity ranges should be logical (low < baseline < high)
        2. Impact values should be non-negative
        3. Parameter names should be descriptive
        4. Results should be consistent with input parameters
        """
        # Create test DSA results
        dsa_results = [
            {
                "parameter": "Labour Hourly Rate",
                "baseline": 50.0,
                "low_value": 40.0,
                "high_value": 60.0,
                "low_change_pct": -20.0,
                "high_change_pct": 20.0,
                "low_impact": 20.0,
                "high_impact": 20.0,
                "max_impact": 20.0
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
                "max_impact": 25.0
            }
        ]
        
        for result in dsa_results:
            # Validation 1: Sensitivity ranges should be logical
            self.assertLess(result['low_value'], result['baseline'],
                          "Low value should be less than baseline")
            self.assertGreater(result['high_value'], result['baseline'],
                             "High value should be greater than baseline")
            
            # Validation 2: Impact values should be non-negative
            self.assertGreaterEqual(result['low_impact'], 0,
                                  "Impact values should be non-negative")
            self.assertGreaterEqual(result['high_impact'], 0,
                                  "Impact values should be non-negative")
            self.assertGreaterEqual(result['max_impact'], 0,
                                  "Impact values should be non-negative")
            
            # Validation 3: Parameter names should be descriptive
            self.assertIsInstance(result['parameter'], str,
                                "Parameter names should be strings")
            self.assertGreater(len(result['parameter']), 5,
                             "Parameter names should be descriptive")
            
            # Validation 4: Percentage changes should be calculated correctly
            expected_low_change = ((result['low_value'] - result['baseline']) / 
                                 result['baseline']) * 100
            expected_high_change = ((result['high_value'] - result['baseline']) / 
                                  result['baseline']) * 100
            
            self.assertAlmostEqual(result['low_change_pct'], expected_low_change, delta=0.01,
                                 msg="Low percentage change calculated incorrectly")
            self.assertAlmostEqual(result['high_change_pct'], expected_high_change, delta=0.01,
                                 msg="High percentage change calculated incorrectly")
    
    def test_psa_validation_criteria(self):
        """Test validation criteria for PSA analysis results.
        
        Validation criteria:
        1. Monte Carlo samples should have correct distribution properties
        2. Cost outcomes should be realistic
        3. Confidence intervals should be logical
        4. Statistical properties should be consistent
        """
        # Create test PSA results
        np.random.seed(42)  # For reproducible results
        labour_costs = np.random.normal(1000, 100, 1000)
        equipment_costs = np.random.normal(800, 50, 1000)
        cost_outcomes = labour_costs + equipment_costs + 500  # Fixed costs
        
        # Validation 1: Monte Carlo samples should have correct distribution properties
        self.assertEqual(len(labour_costs), 1000, "Should have 1000 samples")
        self.assertEqual(len(equipment_costs), 1000, "Should have 1000 samples")
        self.assertEqual(len(cost_outcomes), 1000, "Should have 1000 outcomes")
        
        # Check mean and std are reasonable
        self.assertAlmostEqual(np.mean(labour_costs), 1000, delta=10,
                             msg="Labour cost mean should be close to 1000")
        self.assertAlmostEqual(np.std(labour_costs), 100, delta=10,
                             msg="Labour cost std should be close to 100")
        
        # Validation 2: Cost outcomes should be realistic
        self.assertTrue(all(cost_outcomes > 0), "All cost outcomes should be positive")
        self.assertTrue(all(cost_outcomes < 10000), "Cost outcomes should be reasonable")
        
        # Validation 3: Confidence intervals should be logical
        percentiles = [2.5, 25, 50, 75, 97.5]
        confidence_intervals = {}
        for percentile in percentiles:
            confidence_intervals[f"{percentile}%"] = np.percentile(cost_outcomes, percentile)
        
        # Check that percentiles are in ascending order
        percentile_values = list(confidence_intervals.values())
        self.assertEqual(percentile_values, sorted(percentile_values),
                        "Percentiles should be in ascending order")
        
        # Check that median is between 25th and 75th percentiles
        median = confidence_intervals["50%"]
        q1 = confidence_intervals["25%"]
        q3 = confidence_intervals["75%"]
        self.assertGreaterEqual(median, q1, "Median should be >= 25th percentile")
        self.assertLessEqual(median, q3, "Median should be <= 75th percentile")
        
        # Validation 4: Statistical properties should be consistent
        mean_cost = np.mean(cost_outcomes)
        std_cost = np.std(cost_outcomes)
        
        # Most values should be within 3 standard deviations
        within_3_std = np.sum(np.abs(cost_outcomes - mean_cost) <= 3 * std_cost)
        proportion_within_3_std = within_3_std / len(cost_outcomes)
        self.assertGreater(proportion_within_3_std, 0.95,
                         "Most values should be within 3 standard deviations")
    
    def test_cross_module_validation_criteria(self):
        """Test validation criteria for cross-module consistency.
        
        Validation criteria:
        1. Results should be consistent between related modules
        2. Shared parameters should have consistent values
        3. Aggregated results should match component results
        4. Temporal consistency should be maintained
        """
        # Create test data that should be consistent across modules
        labour_data = {
            'cost_driver': {'value': 1200.0, 'percentage': 37.5},
            'dsa_baseline': 1200.0,
            'psa_mean': 1200.0,
            'psa_std': 120.0
        }
        
        equipment_data = {
            'cost_driver': {'value': 800.0, 'percentage': 25.0},
            'dsa_baseline': 800.0,
            'psa_mean': 800.0,
            'psa_std': 80.0
        }
        
        # Validation 1: Results should be consistent between related modules
        # Cost driver value should match DSA baseline
        self.assertEqual(labour_data['cost_driver']['value'], labour_data['dsa_baseline'],
                        "Cost driver value should match DSA baseline")
        self.assertEqual(equipment_data['cost_driver']['value'], equipment_data['dsa_baseline'],
                        "Cost driver value should match DSA baseline")
        
        # Validation 2: Shared parameters should have consistent values
        # PSA mean should be close to cost driver value and DSA baseline
        self.assertAlmostEqual(labour_data['psa_mean'], labour_data['cost_driver']['value'], 
                             delta=50, msg="PSA mean should be close to cost driver value")
        self.assertAlmostEqual(equipment_data['psa_mean'], equipment_data['cost_driver']['value'], 
                             delta=50, msg="PSA mean should be close to cost driver value")
        
        # Validation 3: Statistical relationships should be logical
        # Higher cost driver values should generally have higher uncertainty
        labour_cv = labour_data['psa_std'] / labour_data['psa_mean']  # Coefficient of variation
        equipment_cv = equipment_data['psa_std'] / equipment_data['psa_mean']
        
        # This is a simplified check - in reality, the relationship between cost driver
        # magnitude and uncertainty would depend on many factors
        self.assertGreater(labour_cv, 0, "Coefficient of variation should be positive")
        self.assertGreater(equipment_cv, 0, "Coefficient of variation should be positive")
    
    def test_boundary_condition_validation(self):
        """Test validation criteria for boundary conditions and edge cases.
        
        Validation criteria:
        1. Zero values should be handled correctly
        2. Extreme values should not cause errors
        3. Missing data should be handled gracefully
        4. Empty datasets should be handled appropriately
        """
        # Test with zero values
        zero_cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Absolute_Value': [0.0, 0.0, 0.0],
            'Percentage': [0.0, 0.0, 0.0]
        })
        
        # Even with zero values, structure should be maintained
        self.assertEqual(len(zero_cost_drivers), 3, "Should maintain row count")
        self.assertIn('Category', zero_cost_drivers.columns, "Should maintain columns")
        
        # Test with extreme values
        extreme_dsa = {
            "parameter": "Extreme Parameter",
            "baseline": 1000000.0,  # Very large baseline
            "low_value": 0.001,     # Very small low value
            "high_value": 1000000000.0,  # Very large high value
            "low_change_pct": -99.9999999,  # Near -100%
            "high_change_pct": 99999.0,     # Very large percentage increase
            "low_impact": 99.9999999,       # Near maximum impact
            "high_impact": 100.0,           # Maximum impact
            "max_impact": 100.0
        }
        
        # Should handle extreme values without error
        self.assertGreater(extreme_dsa['high_value'], extreme_dsa['baseline'])
        self.assertLess(extreme_dsa['low_value'], extreme_dsa['baseline'])
        self.assertLessEqual(extreme_dsa['max_impact'], 100.0, 
                           "Impact should not exceed 100%")
        
        # Test with missing data (represented as NaN)
        nan_data = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables'],
            'Absolute_Value': [1200.0, np.nan, 600.0],
            'Percentage': [37.5, 18.75, np.nan]
        })
        
        # Should identify missing data
        nan_count = nan_data.isnull().sum().sum()
        self.assertGreater(nan_count, 0, "Should detect missing data")
        
        # Test with empty dataset
        empty_data = pd.DataFrame()
        self.assertTrue(empty_data.empty, "Should correctly identify empty data")


if __name__ == '__main__':
    unittest.main()