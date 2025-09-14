"""Test cases for the Monte Carlo Optimization module."""

import unittest
import numpy as np
from unittest.mock import Mock

from src.unimelb_phd_phase_1.monte_carlo_optimizer import MonteCarloOptimizer
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestMonteCarloOptimizer(unittest.TestCase):
    """Test cases for the MonteCarloOptimizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.optimizer = MonteCarloOptimizer(self.mock_data_manager)

    def test_init(self):
        """Test MonteCarloOptimizer initialization."""
        self.assertIsInstance(self.optimizer, MonteCarloOptimizer)
        self.assertEqual(self.optimizer.data_manager, self.mock_data_manager)

    def test_vectorized_sampling_normal(self):
        """Test vectorized sampling from normal distribution."""
        parameters = {'mean': 100, 'std': 15}
        size = 1000
        
        result = self.optimizer.vectorized_sampling('normal', parameters, size)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), size)
        # Check that the mean and std are approximately correct
        self.assertAlmostEqual(np.mean(result), 100, delta=5)  # Allow some variance
        self.assertAlmostEqual(np.std(result), 15, delta=3)   # Allow some variance

    def test_vectorized_sampling_uniform(self):
        """Test vectorized sampling from uniform distribution."""
        parameters = {'low': 10, 'high': 50}
        size = 1000
        
        result = self.optimizer.vectorized_sampling('uniform', parameters, size)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), size)
        # Check that values are within expected range
        self.assertTrue(np.all(result >= 10))
        self.assertTrue(np.all(result <= 50))
        # Check that the mean is approximately correct
        self.assertAlmostEqual(np.mean(result), 30, delta=5)  # (10+50)/2 = 30

    def test_vectorized_sampling_triangular(self):
        """Test vectorized sampling from triangular distribution."""
        parameters = {'left': 0, 'mode': 50, 'right': 100}
        size = 1000
        
        result = self.optimizer.vectorized_sampling('triangular', parameters, size)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), size)
        # Check that values are within expected range
        self.assertTrue(np.all(result >= 0))
        self.assertTrue(np.all(result <= 100))
        # Check that the mean is approximately correct (should be ~50 for symmetric triangle)
        self.assertAlmostEqual(np.mean(result), 50, delta=10)

    def test_single_process_sampling(self):
        """Test single-process sampling."""
        parameters = {
            'param1': {
                'distribution': 'normal',
                'parameters': {'mean': 100, 'std': 15}
            },
            'param2': {
                'distribution': 'uniform',
                'parameters': {'low': 10, 'high': 50}
            }
        }
        iterations = 100
        
        result = self.optimizer._single_process_sampling(parameters, iterations)
        
        self.assertIsInstance(result, dict)
        self.assertIn('param1', result)
        self.assertIn('param2', result)
        self.assertIsInstance(result['param1'], np.ndarray)
        self.assertIsInstance(result['param2'], np.ndarray)
        self.assertEqual(len(result['param1']), iterations)
        self.assertEqual(len(result['param2']), iterations)

    def test_create_chunks(self):
        """Test chunk creation for parallel processing."""
        total_iterations = 100000
        chunk_size = 10000
        n_processes = 4
        
        chunks = self.optimizer._create_chunks(total_iterations, chunk_size, n_processes)
        
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(sum(chunks), total_iterations)

    def test_optimized_cost_calculation(self):
        """Test optimized cost calculation."""
        # Create test simulation results
        simulation_results = {
            'param1': np.array([1, 2, 3, 4, 5]),
            'param2': np.array([10, 20, 30, 40, 50])
        }
        
        # Define a simple cost function
        def cost_function(params):
            return params['param1'] + params['param2']
        
        result = self.optimizer.optimized_cost_calculation(simulation_results, cost_function)
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), 5)
        # Check that the cost calculation is correct
        expected = np.array([11, 22, 33, 44, 55])
        np.testing.assert_array_equal(result, expected)

    def test_benchmark_sampling_methods(self):
        """Test benchmarking of sampling methods."""
        parameters = {
            'test_param': {
                'distribution': 'normal',
                'parameters': {'mean': 0, 'std': 1}
            }
        }
        iterations = 10000
        
        result = self.optimizer.benchmark_sampling_methods(parameters, iterations)
        
        self.assertIsInstance(result, dict)
        self.assertIn('single_process_vectorized', result)
        self.assertGreater(result['single_process_vectorized'], 0)
        # Parallel sampling might not be benchmarked for small iterations
        # but should not raise an exception

    def test_sample_chunk(self):
        """Test sampling a chunk of data."""
        parameters = {
            'param1': {
                'distribution': 'normal',
                'parameters': {'mean': 100, 'std': 15}
            }
        }
        chunk_size = 100
        
        result = self.optimizer._sample_chunk(parameters, chunk_size)
        
        self.assertIsInstance(result, dict)
        self.assertIn('param1', result)
        self.assertIsInstance(result['param1'], list)
        self.assertEqual(len(result['param1']), chunk_size)

    def test_generate_optimization_report(self):
        """Test optimization report generation."""
        # Generate report
        report = self.optimizer.generate_optimization_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Monte Carlo Simulation Optimization", report)
        self.assertIn("Benchmark Results", report)


if __name__ == '__main__':
    unittest.main()