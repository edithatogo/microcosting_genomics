"""Test cases for the VOI analysis module."""

import unittest
import numpy as np
from unittest.mock import Mock, patch

from src.unimelb_phd_phase_1.voi_analysis import VOIAnalyzer
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestVOIAnalyzer(unittest.TestCase):
    """Test cases for the VOIAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = VOIAnalyzer(self.mock_data_manager)

    def test_init(self):
        """Test VOIAnalyzer initialization."""
        self.assertIsInstance(self.analyzer, VOIAnalyzer)
        self.assertEqual(self.analyzer.data_manager, self.mock_data_manager)

    def test_load_voi_parameters(self):
        """Test loading VOI parameters."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None
        
        result = self.analyzer.load_voi_parameters()
        self.assertIsInstance(result, dict)
        # Should return an empty dict since all loads return None
        self.assertEqual(len(result), 0)

    def test_calculate_evpi_cost_only(self):
        """Test EVPI calculation for cost-only analysis."""
        # Create sample cost outcomes
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        
        result = self.analyzer.calculate_evpi(cost_outcomes)
        
        self.assertIn("evpi", result)
        self.assertIn("evpi_as_percentage_of_mean", result)
        self.assertIn("mean_cost", result)
        self.assertIn("std_cost", result)
        
        # Check that values are reasonable
        self.assertGreaterEqual(result["evpi"], 0)
        self.assertGreaterEqual(result["evpi_as_percentage_of_mean"], 0)
        self.assertEqual(result["mean_cost"], 1000)  # Mean of [900, 950, 1000, 1050, 1100]
        self.assertAlmostEqual(result["std_cost"], 70.71067811865476, places=10)  # Std dev

    def test_calculate_evpi_cost_effectiveness(self):
        """Test EVPI calculation for cost-effectiveness analysis."""
        # Create sample cost and effectiveness outcomes
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])
        willingness_to_pay = 50000
        
        result = self.analyzer.calculate_evpi(
            cost_outcomes, effectiveness_outcomes, willingness_to_pay)
        
        self.assertIn("evpi", result)
        self.assertIn("evpi_as_percentage_of_mean_cost", result)
        self.assertIn("mean_cost", result)
        self.assertIn("mean_effectiveness", result)
        self.assertIn("willingness_to_pay", result)

    def test_calculate_evppi(self):
        """Test EVPPI calculation."""
        # Create sample data
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        parameter_groups = {
            'group1': ['param1', 'param2'],
            'group2': ['param3']
        }
        parameter_values = {
            'param1': np.array([1, 2, 3, 4, 5]),
            'param2': np.array([2, 3, 4, 5, 6]),
            'param3': np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        }
        
        result = self.analyzer.calculate_evppi(cost_outcomes, parameter_groups, parameter_values)
        
        self.assertIsInstance(result, dict)
        self.assertIn('group1', result)
        self.assertIn('group2', result)
        
        # Check structure of results
        for group_name, group_results in result.items():
            self.assertIn('evppi', group_results)
            self.assertIn('evppi_as_percentage_of_total_variance', group_results)
            self.assertIn('parameters', group_results)
            self.assertGreaterEqual(group_results['evppi'], 0)

    def test_generate_net_benefit_curve_cost_only(self):
        """Test net benefit curve generation for cost-only analysis."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        
        result = self.analyzer.generate_net_benefit_curve(cost_outcomes)
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result["cost_only"])
        self.assertEqual(len(result["wtp_values"]), 0)
        self.assertEqual(len(result["net_benefits"]), 0)

    def test_generate_net_benefit_curve_cost_effectiveness(self):
        """Test net benefit curve generation for cost-effectiveness analysis."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])
        
        result = self.analyzer.generate_net_benefit_curve(cost_outcomes, effectiveness_outcomes)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result["cost_only"])
        self.assertIn("wtp_values", result)
        self.assertIn("net_benefits", result)
        self.assertGreater(len(result["wtp_values"]), 0)
        self.assertGreater(len(result["net_benefits"]), 0)
        self.assertEqual(len(result["wtp_values"]), len(result["net_benefits"]))

    def test_generate_ceac(self):
        """Test CEAC generation."""
        cost_outcomes = np.array([900, 950, 1000, 1050, 1100])
        effectiveness_outcomes = np.array([0.7, 0.75, 0.8, 0.85, 0.9])
        
        result = self.analyzer.generate_ceac(cost_outcomes, effectiveness_outcomes)
        
        self.assertIsInstance(result, dict)
        self.assertIn("wtp_values", result)
        self.assertIn("ceac_probabilities", result)
        self.assertGreater(len(result["wtp_values"]), 0)
        self.assertGreater(len(result["ceac_probabilities"]), 0)
        self.assertEqual(len(result["wtp_values"]), len(result["ceac_probabilities"]))

    @patch('src.unimelb_phd_phase_1.voi_analysis.PSAAnalyzer')
    def test_generate_voi_report(self, mock_psa_analyzer):
        """Test VOI report generation."""
        # Mock the PSA analyzer
        mock_psa_instance = Mock()
        mock_psa_analyzer.return_value = mock_psa_instance
        
        # Mock the Monte Carlo simulation results
        mock_simulation_results = {
            'labour_cost': np.array([750, 800, 850]),
            'equipment_cost': np.array([500, 600, 700]),
            'consumable_cost': np.array([250, 300, 350])
        }
        mock_psa_instance.perform_monte_carlo_simulation.return_value = mock_simulation_results
        
        # Mock the cost outcomes calculation
        mock_psa_instance.calculate_cost_outcomes.return_value = np.array([1500, 1700, 1900])
        
        # Mock loading VOI parameters
        self.mock_data_manager.load_sheet.return_value = None
        
        # Generate report
        report = self.analyzer.generate_voi_report(iterations=3)
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Value of Information", report)
        self.assertIn("EVPI", report)
        self.assertIn("EVPPI", report)


if __name__ == '__main__':
    unittest.main()