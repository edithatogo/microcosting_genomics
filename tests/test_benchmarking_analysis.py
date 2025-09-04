"""Test cases for the Benchmarking Analysis module."""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.unimelb_phd_phase_1.benchmarking_analysis import BenchmarkingAnalyzer
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestBenchmarkingAnalyzer(unittest.TestCase):
    """Test cases for the BenchmarkingAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.analyzer = BenchmarkingAnalyzer(self.mock_data_manager)

    def test_init(self):
        """Test BenchmarkingAnalyzer initialization."""
        self.assertIsInstance(self.analyzer, BenchmarkingAnalyzer)
        self.assertEqual(self.analyzer.data_manager, self.mock_data_manager)

    def test_load_benchmark_data(self):
        """Test loading benchmark data."""
        # Mock the data manager to return None for all sheets
        self.mock_data_manager.load_sheet.return_value = None
        
        result = self.analyzer.load_benchmark_data()
        self.assertIsInstance(result, dict)
        # Should return an empty dict since all loads return None
        self.assertEqual(len(result), 0)

    def test_load_published_benchmarks(self):
        """Test loading published benchmark data."""
        result = self.analyzer.load_published_benchmarks()
        
        self.assertIsInstance(result, dict)
        self.assertIn("Panel Testing", result)
        self.assertIn("WES Testing", result)
        self.assertIn("WGS Testing", result)
        
        # Check that each benchmark has the expected keys
        for model_name, benchmark_data in result.items():
            self.assertIn("cost_per_test", benchmark_data)
            self.assertIn("turnaround_time", benchmark_data)
            self.assertIn("throughput_per_day", benchmark_data)
            self.assertIn("accuracy", benchmark_data)
            self.assertIn("source", benchmark_data)

    def test_compare_against_benchmarks(self):
        """Test comparison against benchmarks."""
        current_performance = {
            "Panel Testing": {
                "cost_per_test": 1800.0,
                "turnaround_time": 7,
                "throughput_per_day": 25,
                "accuracy": 0.94
            }
        }
        
        benchmarks = {
            "Panel Testing": {
                "cost_per_test": 1500.0,
                "turnaround_time": 5,
                "throughput_per_day": 20,
                "accuracy": 0.95,
                "source": "Smith et al., 2020"
            }
        }
        
        result = self.analyzer.compare_against_benchmarks(current_performance, benchmarks)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('Model', result.columns)
        self.assertIn('Metric', result.columns)
        self.assertIn('Current', result.columns)
        self.assertIn('Benchmark', result.columns)
        self.assertIn('Ratio', result.columns)
        self.assertIn('Performance', result.columns)
        self.assertIn('Source', result.columns)
        
        # Check that we have 4 rows for the 4 metrics
        panel_rows = result[result['Model'] == 'Panel Testing']
        self.assertEqual(len(panel_rows), 4)
        
        # Check specific calculations
        cost_row = panel_rows[panel_rows['Metric'] == 'Cost per Test'].iloc[0]
        self.assertEqual(cost_row['Current'], 1800.0)
        self.assertEqual(cost_row['Benchmark'], 1500.0)
        self.assertEqual(cost_row['Ratio'], 1.2)  # 1800/1500
        self.assertEqual(cost_row['Performance'], -1)  # Worse performance (higher cost)
        
        turnaround_row = panel_rows[panel_rows['Metric'] == 'Turnaround Time'].iloc[0]
        self.assertEqual(turnaround_row['Current'], 7)
        self.assertEqual(turnaround_row['Benchmark'], 5)
        self.assertEqual(turnaround_row['Ratio'], 1.4)  # 7/5
        self.assertEqual(turnaround_row['Performance'], -1)  # Worse performance (longer time)
        
        throughput_row = panel_rows[panel_rows['Metric'] == 'Throughput per Day'].iloc[0]
        self.assertEqual(throughput_row['Current'], 25)
        self.assertEqual(throughput_row['Benchmark'], 20)
        self.assertEqual(throughput_row['Ratio'], 1.25)  # 25/20
        self.assertEqual(throughput_row['Performance'], 1)  # Better performance (higher throughput)
        
        accuracy_row = panel_rows[panel_rows['Metric'] == 'Accuracy'].iloc[0]
        self.assertEqual(accuracy_row['Current'], 0.94)
        self.assertEqual(accuracy_row['Benchmark'], 0.95)
        self.assertAlmostEqual(accuracy_row['Ratio'], 0.989, places=3)  # 0.94/0.95
        self.assertEqual(accuracy_row['Performance'], -1)  # Worse performance (lower accuracy)

    def test_calculate_efficiency_metrics(self):
        """Test efficiency metrics calculation."""
        result = self.analyzer.calculate_efficiency_metrics(
            observed_output=1000,
            observed_input=2000000,
            best_practice_output=1200,
            best_practice_input=1800000
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('technical_efficiency', result)
        self.assertIn('cost_efficiency', result)
        self.assertIn('observed_productivity', result)
        self.assertIn('best_practice_productivity', result)
        self.assertIn('productivity_ratio', result)
        self.assertIn('observed_output', result)
        self.assertIn('observed_input', result)
        self.assertIn('best_practice_output', result)
        self.assertIn('best_practice_input', result)
        
        # Check calculations
        # Technical efficiency = (Observed output / Best practice output) / 
        #                        (Observed input / Best practice input)
        # = (1000 / 1200) / (2000000 / 1800000) = (0.8333) / (1.1111) = 0.75
        self.assertAlmostEqual(result['technical_efficiency'], 0.75, places=4)
        
        # Cost efficiency = Observed cost / Best practice cost
        # = 2000000 / 1800000 = 1.1111
        self.assertAlmostEqual(result['cost_efficiency'], 1.1111, places=4)
        
        # Productivity = Output / Input
        # Observed productivity = 1000 / 2000000 = 0.0005
        self.assertAlmostEqual(result['observed_productivity'], 0.0005, places=8)
        
        # Best practice productivity = 1200 / 1800000 = 0.0006667
        self.assertAlmostEqual(result['best_practice_productivity'], 0.0006666666666666666, places=10)
        
        # Productivity ratio = 0.0005 / (1200/1800000) = 0.75
        self.assertAlmostEqual(result['productivity_ratio'], 0.75, places=4)

    def test_benchmark_performance_over_time(self):
        """Test benchmarking performance over time."""
        historical_data = [
            {"date": "2023-01-01", "tests_completed": 800, "total_cost": 1600000},
            {"date": "2023-02-01", "tests_completed": 900, "total_cost": 1700000},
            {"date": "2023-03-01", "tests_completed": 1000, "total_cost": 1800000}
        ]
        
        result = self.analyzer.benchmark_performance_over_time(historical_data)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn('date', result.columns)
        self.assertIn('tests_completed', result.columns)
        self.assertIn('total_cost', result.columns)

    def test_generate_benchmarking_report(self):
        """Test benchmarking report generation."""
        # Mock the data manager
        self.mock_data_manager.load_sheet.return_value = None
        
        # Generate report
        report = self.analyzer.generate_benchmarking_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Benchmarking Analysis", report)
        self.assertIn("Benchmark Comparison", report)


if __name__ == '__main__':
    unittest.main()