"""Load testing framework for genomics microcosting analysis.

This module provides load testing capabilities with variable data sizes
to benchmark performance of the genomics microcosting framework.
"""

import unittest
import time
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.performance import PerformanceProfiler, DataOptimizer  # noqa: E402
from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer  # noqa: E402


class LoadTestingFramework:
    """Load testing framework with variable data sizes."""
    
    def __init__(self):
        """Initialize the load testing framework."""
        self.profiler = PerformanceProfiler()
        self.results = []
    
    def generate_test_data(self, size: int) -> pd.DataFrame:
        """Generate test data of specified size.
        
        Args:
            size (int): Number of rows to generate
            
        Returns:
            pd.DataFrame: Generated test data
        """
        np.random.seed(42)  # For reproducible results
        
        # Generate realistic test data for genomics microcosting
        test_types = ['Panel', 'WES (P)', 'WES (T)', 'WGS']
        categories = ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage']
        sub_categories = ['Sequencing', 'Library Prep', 'DNA Extraction', 'Processing', 'Archival']
        
        data = {
            'Test': np.random.choice(test_types, size),
            'Category': np.random.choice(categories, size),
            'Sub-Category': np.random.choice(sub_categories, size),
            'Step': ['Sample Prep'] * size,
            'Quantity': np.random.uniform(0.5, 5.0, size),
            'Unit_Cost': np.random.uniform(50.0, 200.0, size),
        }
        
        # Calculate total cost
        data['Total_Cost'] = np.array(data['Quantity']) * np.array(data['Unit_Cost'])
        
        return pd.DataFrame(data)
    
    def run_load_test(self, data_size: int, operation_name: str, 
                     test_function: callable, *args, **kwargs) -> dict:
        """Run a load test with specified data size.
        
        Args:
            data_size (int): Size of test data
            operation_name (str): Name of the operation being tested
            test_function (callable): Function to test
            *args: Arguments to pass to test function
            **kwargs: Keyword arguments to pass to test function
            
        Returns:
            dict: Test results including timing and memory usage
        """
        # Generate test data
        test_data = self.generate_test_data(data_size)
        
        # Profile the operation
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        # Run the test function
        success = False
        error = None
        try:
            test_function(test_data, *args, **kwargs)
            success = True
        except Exception:
            error = "Exception occurred during test execution"
        
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        # Calculate metrics
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Store results
        test_result = {
            'data_size': data_size,
            'operation_name': operation_name,
            'execution_time': execution_time,
            'memory_used': memory_used,
            'success': success,
            'error': error,
            'timestamp': pd.Timestamp.now()
        }
        
        self.results.append(test_result)
        return test_result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB.
        
        Returns:
            float: Memory usage in MB
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def run_scalability_test(self, sizes: list, operation_name: str,
                           test_function: callable, *args, **kwargs) -> list:
        """Run scalability test across multiple data sizes.
        
        Args:
            sizes (list): List of data sizes to test
            operation_name (str): Name of the operation being tested
            test_function (callable): Function to test
            *args: Arguments to pass to test function
            **kwargs: Keyword arguments to pass to test function
            
        Returns:
            list: List of test results
        """
        results = []
        
        for size in sizes:
            print(f"Running load test with {size} rows...")
            result = self.run_load_test(size, operation_name, test_function, *args, **kwargs)
            results.append(result)
            print(f"  Time: {result['execution_time']:.4f}s, Memory: {result['memory_used']:.2f}MB")
        
        return results
    
    def get_performance_report(self) -> pd.DataFrame:
        """Get performance report as DataFrame.
        
        Returns:
            pd.DataFrame: Performance report
        """
        return pd.DataFrame(self.results)
    
    def print_performance_summary(self):
        """Print formatted performance summary."""
        if not self.results:
            print("No performance data collected.")
            return
        
        df = pd.DataFrame(self.results)
        
        print("\nLoad Testing Performance Summary")
        print("=" * 80)
        print(f"{'Data Size':<12} {'Operation':<25} {'Time (s)':<12} {'Memory (MB)':<12} {'Success':<8}")
        print("-" * 80)
        
        for _, row in df.iterrows():
            print(f"{row['data_size']:<12} {row['operation_name']:<25} {row['execution_time']:<12.4f} "
                  f"{row['memory_used']:<12.2f} {row['success']:<8}")


class TestDataFrameOptimization:
    """Test DataFrame optimization performance."""
    
    def __init__(self):
        self.optimizer = DataOptimizer()
    
    def test_optimization_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Test DataFrame optimization performance.
        
        Args:
            df (pd.DataFrame): DataFrame to optimize
            
        Returns:
            pd.DataFrame: Optimized DataFrame
        """
        return self.optimizer.optimize_dataframe(df)
    
    def test_chunked_processing_performance(self, df: pd.DataFrame, 
                                          chunk_size: int = 1000) -> pd.DataFrame:
        """Test chunked processing performance.
        
        Args:
            df (pd.DataFrame): DataFrame to process
            chunk_size (int): Chunk size for processing
            
        Returns:
            pd.DataFrame: Processed DataFrame
        """
        return self.optimizer.chunked_processing(df, chunk_size)


class TestLoadTestingFramework(unittest.TestCase):
    """Load testing framework tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.load_tester = LoadTestingFramework()
        self.optimizer_tester = TestDataFrameOptimization()
    
    def test_generate_test_data(self):
        """Test generation of test data."""
        # Test small dataset
        small_data = self.load_tester.generate_test_data(100)
        self.assertIsInstance(small_data, pd.DataFrame)
        self.assertEqual(len(small_data), 100)
        self.assertIn('Test', small_data.columns)
        self.assertIn('Category', small_data.columns)
        self.assertIn('Total_Cost', small_data.columns)
        
        # Test larger dataset
        large_data = self.load_tester.generate_test_data(1000)
        self.assertEqual(len(large_data), 1000)
        
        # Verify data types
        self.assertTrue(pd.api.types.is_numeric_dtype(large_data['Quantity']))
        self.assertTrue(pd.api.types.is_numeric_dtype(large_data['Unit_Cost']))
        self.assertTrue(pd.api.types.is_numeric_dtype(large_data['Total_Cost']))
    
    def test_run_load_test(self):
        """Test running a single load test."""
        def simple_operation(df):
            return df['Total_Cost'].sum()
        
        result = self.load_tester.run_load_test(
            data_size=1000,
            operation_name="sum_total_cost",
            test_function=simple_operation
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('data_size', result)
        self.assertIn('execution_time', result)
        self.assertIn('memory_used', result)
        self.assertIn('success', result)
        self.assertEqual(result['data_size'], 1000)
        self.assertTrue(result['success'])
    
    def test_scalability_test(self):
        """Test scalability testing across multiple data sizes."""
        def count_rows(df):
            return len(df)
        
        sizes = [100, 500, 1000]
        results = self.load_tester.run_scalability_test(
            sizes=sizes,
            operation_name="count_rows",
            test_function=count_rows
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), len(sizes))
        
        # Verify results
        for i, result in enumerate(results):
            self.assertEqual(result['data_size'], sizes[i])
            self.assertTrue(result['success'])
    
    def test_dataframe_optimization_performance(self):
        """Test DataFrame optimization performance."""
        # Create test DataFrame
        df = self.load_tester.generate_test_data(10000)
        
        # Test optimization
        result = self.load_tester.run_load_test(
            data_size=len(df),
            operation_name="dataframe_optimization",
            test_function=self.optimizer_tester.test_optimization_performance
        )
        
        self.assertTrue(result['success'])
        self.assertGreater(result['execution_time'], 0)
    
    def test_performance_report(self):
        """Test performance report generation."""
        # Run a few tests to generate data
        def dummy_operation(df):
            return df.head(10)
        
        self.load_tester.run_load_test(100, "dummy1", dummy_operation)
        self.load_tester.run_load_test(200, "dummy2", dummy_operation)
        
        # Get report
        report = self.load_tester.get_performance_report()
        self.assertIsInstance(report, pd.DataFrame)
        self.assertGreater(len(report), 0)
        
        # Check required columns
        required_columns = ['data_size', 'operation_name', 'execution_time', 'memory_used', 'success']
        for col in required_columns:
            self.assertIn(col, report.columns)


class BenchmarkingScenarios:
    """Benchmarking scenarios for different operations."""
    
    @staticmethod
    def cost_driver_analysis_benchmark(data_manager_mock, data_size: int):
        """Benchmark cost driver analysis with specified data size.
        
        Args:
            data_manager_mock: Mock data manager
            data_size (int): Size of test data
            
        Returns:
            dict: Benchmark results
        """
        # Generate test data
        load_tester = LoadTestingFramework()
        test_data = load_tester.generate_test_data(data_size)
        
        # Mock data manager to return test data
        data_manager_mock.load_sheet.return_value = test_data
        
        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager_mock)
        
        # Run analysis
        start_time = time.time()
        cost_drivers = analyzer.calculate_absolute_cost_drivers(test_data)
        execution_time = time.time() - start_time
        
        return {
            'cost_drivers': cost_drivers,
            'execution_time': execution_time,
            'data_size': data_size
        }
    
    @staticmethod
    def data_loading_benchmark(file_path: str, data_size: int):
        """Benchmark data loading performance.
        
        Args:
            file_path (str): Path to test file
            data_size (int): Size of test data
            
        Returns:
            dict: Benchmark results
        """
        # This would test actual file loading performance
        # For now, we'll simulate it
        load_tester = LoadTestingFramework()
        test_data = load_tester.generate_test_data(data_size)
        
        start_time = time.time()
        # Simulate data loading
        result = test_data.copy()
        execution_time = time.time() - start_time
        
        return {
            'data': result,
            'execution_time': execution_time,
            'data_size': data_size
        }


# Example usage:
if __name__ == "__main__":
    # Create load testing framework
    load_tester = LoadTestingFramework()
    
    # Define test function
    def sample_analysis(df):
        """Sample analysis function."""
        # Simulate some analysis work
        summary = {
            'total_rows': len(df),
            'avg_cost': df['Total_Cost'].mean(),
            'max_cost': df['Total_Cost'].max(),
            'min_cost': df['Total_Cost'].min()
        }
        return summary
    
    # Run scalability test
    sizes = [1000, 5000, 10000, 50000]
    print("Running scalability test...")
    results = load_tester.run_scalability_test(
        sizes=sizes,
        operation_name="sample_analysis",
        test_function=sample_analysis
    )
    
    # Print performance summary
    load_tester.print_performance_summary()
    
    # Get detailed report
    report = load_tester.get_performance_report()
    print(f"\nDetailed report shape: {report.shape}")