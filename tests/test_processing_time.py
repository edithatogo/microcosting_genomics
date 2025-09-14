"""Processing time measurement utilities for genomics microcosting analysis.

This module provides utilities to measure and analyze processing time for
various operations in the genomics microcosting framework.
"""

import unittest
import time
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, List, Callable, Any
import statistics

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.performance import PerformanceProfiler  # noqa: E402


class ProcessingTimeMeasurer:
    """Measures and analyzes processing time for various operations."""
    
    def __init__(self):
        """Initialize the processing time measurer."""
        self.measurements = {}
        self.profiler = PerformanceProfiler()
    
    def measure_execution_time(self, operation_name: str, 
                             operation_func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Measure execution time for a single operation.
        
        Args:
            operation_name (str): Name of the operation
            operation_func (Callable): Function to measure
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dict[str, Any]: Measurement results
        """
        start_time = time.perf_counter()
        start_cpu = time.process_time()
        
        try:
            result = operation_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.perf_counter()
        end_cpu = time.process_time()
        
        wall_time = end_time - start_time
        cpu_time = end_cpu - start_cpu
        
        measurement = {
            'operation_name': operation_name,
            'wall_time': wall_time,
            'cpu_time': cpu_time,
            'success': success,
            'error': error,
            'result': result,
            'timestamp': time.time()
        }
        
        if operation_name not in self.measurements:
            self.measurements[operation_name] = []
        self.measurements[operation_name].append(measurement)
        
        return measurement
    
    def measure_multiple_executions(self, operation_name: str, 
                                  operation_func: Callable, 
                                  iterations: int = 10, 
                                  *args, **kwargs) -> Dict[str, Any]:
        """Measure execution time for multiple executions of an operation.
        
        Args:
            operation_name (str): Name of the operation
            operation_func (Callable): Function to measure
            iterations (int): Number of times to execute the function
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dict[str, Any]: Aggregated measurement results
        """
        measurements = []
        
        for i in range(iterations):
            measurement = self.measure_execution_time(
                f"{operation_name}_run_{i+1}", 
                operation_func, 
                *args, 
                **kwargs
            )
            measurements.append(measurement)
        
        # Calculate statistics
        successful_measurements = [m for m in measurements if m['success']]
        
        if successful_measurements:
            wall_times = [m['wall_time'] for m in successful_measurements]
            cpu_times = [m['cpu_time'] for m in successful_measurements]
            
            stats = {
                'operation_name': operation_name,
                'iterations': iterations,
                'successful_executions': len(successful_measurements),
                'wall_time_stats': {
                    'mean': statistics.mean(wall_times),
                    'median': statistics.median(wall_times),
                    'stdev': statistics.stdev(wall_times) if len(wall_times) > 1 else 0,
                    'min': min(wall_times),
                    'max': max(wall_times)
                },
                'cpu_time_stats': {
                    'mean': statistics.mean(cpu_times),
                    'median': statistics.median(cpu_times),
                    'stdev': statistics.stdev(cpu_times) if len(cpu_times) > 1 else 0,
                    'min': min(cpu_times),
                    'max': max(cpu_times)
                },
                'all_measurements': measurements
            }
        else:
            stats = {
                'operation_name': operation_name,
                'iterations': iterations,
                'successful_executions': 0,
                'error': 'All executions failed',
                'all_measurements': measurements
            }
        
        return stats
    
    def compare_processing_times(self, baseline_stats: Dict[str, Any], 
                               test_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Compare processing times between baseline and test operations.
        
        Args:
            baseline_stats (Dict[str, Any]): Baseline measurement statistics
            test_stats (Dict[str, Any]): Test measurement statistics
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        if (baseline_stats['successful_executions'] == 0 or 
            test_stats['successful_executions'] == 0):
            return {
                'comparison_possible': False,
                'error': 'Insufficient successful executions for comparison'
            }
        
        baseline_wall_mean = baseline_stats['wall_time_stats']['mean']
        test_wall_mean = test_stats['wall_time_stats']['mean']
        
        baseline_cpu_mean = baseline_stats['cpu_time_stats']['mean']
        test_cpu_mean = test_stats['cpu_time_stats']['mean']
        
        # Calculate improvements (negative means test is slower)
        wall_time_improvement = baseline_wall_mean - test_wall_mean
        wall_time_improvement_pct = (wall_time_improvement / baseline_wall_mean * 100) if baseline_wall_mean > 0 else 0
        
        cpu_time_improvement = baseline_cpu_mean - test_cpu_mean
        cpu_time_improvement_pct = (cpu_time_improvement / baseline_cpu_mean * 100) if baseline_cpu_mean > 0 else 0
        
        return {
            'comparison_possible': True,
            'baseline_operation': baseline_stats['operation_name'],
            'test_operation': test_stats['operation_name'],
            'wall_time_comparison': {
                'baseline_mean': baseline_wall_mean,
                'test_mean': test_wall_mean,
                'improvement': wall_time_improvement,
                'improvement_percentage': wall_time_improvement_pct
            },
            'cpu_time_comparison': {
                'baseline_mean': baseline_cpu_mean,
                'test_mean': test_cpu_mean,
                'improvement': cpu_time_improvement,
                'improvement_percentage': cpu_time_improvement_pct
            }
        }
    
    def get_processing_time_report(self) -> pd.DataFrame:
        """Get processing time report as DataFrame.
        
        Returns:
            pd.DataFrame: Processing time report
        """
        report_data = []
        
        for operation_name, measurements in self.measurements.items():
            for measurement in measurements:
                report_data.append({
                    'operation_name': operation_name,
                    'wall_time': measurement['wall_time'],
                    'cpu_time': measurement['cpu_time'],
                    'success': measurement['success'],
                    'timestamp': measurement['timestamp']
                })
        
        return pd.DataFrame(report_data)
    
    def print_processing_time_summary(self):
        """Print formatted processing time summary."""
        if not self.measurements:
            print("No processing time data collected.")
            return
        
        print("\nProcessing Time Summary")
        print("=" * 80)
        print(f"{'Operation':<30} {'Count':<8} {'Mean Wall Time':<15} {'Mean CPU Time':<15} {'Success Rate':<12}")
        print("-" * 80)
        
        for operation_name, measurements in self.measurements.items():
            successful_count = sum(1 for m in measurements if m['success'])
            total_count = len(measurements)
            success_rate = (successful_count / total_count) * 100 if total_count > 0 else 0
            
            if successful_count > 0:
                wall_times = [m['wall_time'] for m in measurements if m['success']]
                cpu_times = [m['cpu_time'] for m in measurements if m['success']]
                mean_wall_time = statistics.mean(wall_times)
                mean_cpu_time = statistics.mean(cpu_times)
            else:
                mean_wall_time = 0
                mean_cpu_time = 0
            
            print(f"{operation_name:<30} {total_count:<8} {mean_wall_time:<15.4f} "
                  f"{mean_cpu_time:<15.4f} {success_rate:<11.1f}%")


class CalculationEngineBenchmark:
    """Benchmark the calculation engine performance."""
    
    def __init__(self):
        """Initialize the benchmark."""
        self.time_measurer = ProcessingTimeMeasurer()
    
    def benchmark_formula_parsing(self, formulas: List[str]) -> Dict[str, Any]:
        """Benchmark formula parsing performance.
        
        Args:
            formulas (List[str]): List of formulas to parse
            
        Returns:
            Dict[str, Any]: Benchmark results
        """
        # This would test the actual formula parsing performance
        # For now, we'll simulate it
        def parse_formulas(formula_list):
            # Simulate parsing work
            parsed_count = 0
            for formula in formula_list:
                # Simulate some parsing work
                if formula.startswith('='):
                    parsed_count += 1
                time.sleep(0.001)  # Simulate processing time
            return parsed_count
        
        stats = self.time_measurer.measure_multiple_executions(
            "formula_parsing",
            parse_formulas,
            iterations=5,
            formula_list=formulas
        )
        
        return stats
    
    def benchmark_cell_calculations(self, cell_count: int) -> Dict[str, Any]:
        """Benchmark cell calculation performance.
        
        Args:
            cell_count (int): Number of cells to calculate
            
        Returns:
            Dict[str, Any]: Benchmark results
        """
        # This would test actual cell calculation performance
        # For now, we'll simulate it
        def calculate_cells(count):
            # Simulate calculation work
            results = []
            for i in range(count):
                # Simulate some calculation
                result = (i * 1.5) + (i * 0.7)
                results.append(result)
                if i % 100 == 0:
                    time.sleep(0.001)  # Simulate processing time
            return results
        
        stats = self.time_measurer.measure_multiple_executions(
            "cell_calculations",
            calculate_cells,
            iterations=3,
            count=cell_count
        )
        
        return stats


class TestProcessingTimeMeasurer(unittest.TestCase):
    """Processing time measurement tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.time_measurer = ProcessingTimeMeasurer()
        self.benchmark = CalculationEngineBenchmark()
    
    def test_single_execution_measurement(self):
        """Test measurement of single execution time."""
        def sample_operation():
            # Simulate some work
            time.sleep(0.01)
            return "result"
        
        measurement = self.time_measurer.measure_execution_time(
            "sample_operation",
            sample_operation
        )
        
        self.assertIsInstance(measurement, dict)
        self.assertIn('operation_name', measurement)
        self.assertIn('wall_time', measurement)
        self.assertIn('cpu_time', measurement)
        self.assertIn('success', measurement)
        self.assertIn('result', measurement)
        
        self.assertEqual(measurement['operation_name'], 'sample_operation')
        self.assertTrue(measurement['success'])
        self.assertEqual(measurement['result'], 'result')
        self.assertGreater(measurement['wall_time'], 0)
        self.assertGreater(measurement['cpu_time'], 0)
    
    def test_multiple_execution_measurement(self):
        """Test measurement of multiple executions."""
        def sample_operation(x, y):
            # Simulate some work
            time.sleep(0.005)
            return x + y
        
        stats = self.time_measurer.measure_multiple_executions(
            "addition_operation",
            sample_operation,
            iterations=5,
            x=10,
            y=20
        )
        
        self.assertIsInstance(stats, dict)
        self.assertIn('operation_name', stats)
        self.assertIn('iterations', stats)
        self.assertIn('successful_executions', stats)
        self.assertIn('wall_time_stats', stats)
        self.assertIn('cpu_time_stats', stats)
        
        self.assertEqual(stats['operation_name'], 'addition_operation')
        self.assertEqual(stats['iterations'], 5)
        self.assertEqual(stats['successful_executions'], 5)
        
        # Check statistics
        wall_stats = stats['wall_time_stats']
        self.assertIn('mean', wall_stats)
        self.assertIn('median', wall_stats)
        self.assertIn('min', wall_stats)
        self.assertIn('max', wall_stats)
        self.assertGreater(wall_stats['mean'], 0)
    
    def test_error_handling_in_measurement(self):
        """Test error handling during measurement."""
        def failing_operation():
            raise ValueError("Test error")
        
        measurement = self.time_measurer.measure_execution_time(
            "failing_operation",
            failing_operation
        )
        
        self.assertFalse(measurement['success'])
        self.assertIn('error', measurement)
        self.assertIsNotNone(measurement['error'])
        self.assertEqual(measurement['result'], None)
    
    def test_comparison_of_processing_times(self):
        """Test comparison of processing times."""
        # Create baseline measurements
        def fast_operation():
            time.sleep(0.01)
            return "fast"
        
        def slow_operation():
            time.sleep(0.02)
            return "slow"
        
        baseline_stats = self.time_measurer.measure_multiple_executions(
            "fast_operation",
            fast_operation,
            iterations=3
        )
        
        test_stats = self.time_measurer.measure_multiple_executions(
            "slow_operation",
            slow_operation,
            iterations=3
        )
        
        # Compare processing times
        comparison = self.time_measurer.compare_processing_times(baseline_stats, test_stats)
        
        self.assertIsInstance(comparison, dict)
        self.assertIn('comparison_possible', comparison)
        self.assertTrue(comparison['comparison_possible'])
        
        # Check comparison results
        wall_comparison = comparison['wall_time_comparison']
        self.assertIn('baseline_mean', wall_comparison)
        self.assertIn('test_mean', wall_comparison)
        self.assertIn('improvement', wall_comparison)
        self.assertIn('improvement_percentage', wall_comparison)
        
        # Slow operation should have negative improvement (it's slower)
        self.assertLess(wall_comparison['improvement'], 0)
    
    def test_processing_time_report(self):
        """Test processing time report generation."""
        # Run some measurements to generate data
        def dummy_operation():
            return "dummy"
        
        self.time_measurer.measure_execution_time("test1", dummy_operation)
        self.time_measurer.measure_execution_time("test2", dummy_operation)
        
        # Get report
        report = self.time_measurer.get_processing_time_report()
        self.assertIsInstance(report, pd.DataFrame)
        self.assertGreater(len(report), 0)
        
        # Check required columns
        required_columns = ['operation_name', 'wall_time', 'cpu_time', 'success', 'timestamp']
        for col in required_columns:
            self.assertIn(col, report.columns)
    
    def test_benchmark_formula_parsing(self):
        """Test formula parsing benchmark."""
        formulas = [
            "=A1+B1",
            "=SUM(A1:A10)",
            "=VLOOKUP(A1, B:C, 2, FALSE)",
            "=IF(A1>0, A1*B1, 0)"
        ]
        
        stats = self.benchmark.benchmark_formula_parsing(formulas)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('operation_name', stats)
        self.assertIn('iterations', stats)
        self.assertIn('successful_executions', stats)
        self.assertEqual(stats['operation_name'], 'formula_parsing')
    
    def test_benchmark_cell_calculations(self):
        """Test cell calculation benchmark."""
        stats = self.benchmark.benchmark_cell_calculations(1000)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('operation_name', stats)
        self.assertIn('iterations', stats)
        self.assertIn('successful_executions', stats)
        self.assertEqual(stats['operation_name'], 'cell_calculations')


class ScalabilityTester:
    """Test scalability of operations with increasing data sizes."""
    
    def __init__(self):
        """Initialize the scalability tester."""
        self.time_measurer = ProcessingTimeMeasurer()
    
    def test_scalability(self, operation_func: Callable, 
                        data_sizes: List[int]) -> Dict[str, Any]:
        """Test scalability of an operation with different data sizes.
        
        Args:
            operation_func (Callable): Function to test
            data_sizes (List[int]): List of data sizes to test
            
        Returns:
            Dict[str, Any]: Scalability test results
        """
        results = {}
        
        for size in data_sizes:
            def test_operation():
                # Generate test data of specified size
                test_data = list(range(size))
                return operation_func(test_data)
            
            stats = self.time_measurer.measure_multiple_executions(
                f"scalability_test_{size}",
                test_operation,
                iterations=3
            )
            
            results[size] = stats
        
        return results
    
    def analyze_scalability(self, scalability_results: Dict[int, Dict]) -> Dict[str, Any]:
        """Analyze scalability results.
        
        Args:
            scalability_results (Dict[int, Dict]): Results from scalability test
            
        Returns:
            Dict[str, Any]: Scalability analysis
        """
        sizes = list(scalability_results.keys())
        wall_times = []
        
        for size in sizes:
            stats = scalability_results[size]
            if stats['successful_executions'] > 0:
                wall_times.append(stats['wall_time_stats']['mean'])
            else:
                wall_times.append(0)
        
        # Simple linear regression to determine scaling behavior
        if len(sizes) > 1 and all(t > 0 for t in wall_times):
            # Calculate approximate scaling factor
            scaling_factors = []
            for i in range(1, len(sizes)):
                if sizes[i-1] > 0 and wall_times[i-1] > 0:
                    size_ratio = sizes[i] / sizes[i-1]
                    time_ratio = wall_times[i] / wall_times[i-1]
                    scaling_factor = time_ratio / size_ratio if size_ratio > 0 else 0
                    scaling_factors.append(scaling_factor)
            
            avg_scaling_factor = statistics.mean(scaling_factors) if scaling_factors else 0
            
            # Classify scaling behavior
            if avg_scaling_factor < 0.5:
                scaling_behavior = "sub-linear"
            elif avg_scaling_factor < 1.5:
                scaling_behavior = "linear"
            else:
                scaling_behavior = "super-linear"
        else:
            avg_scaling_factor = 0
            scaling_behavior = "unknown"
        
        return {
            'sizes': sizes,
            'wall_times': wall_times,
            'average_scaling_factor': avg_scaling_factor,
            'scaling_behavior': scaling_behavior,
            'scalability_results': scalability_results
        }


# Example usage:
if __name__ == "__main__":
    # Create processing time measurer
    time_measurer = ProcessingTimeMeasurer()
    
    # Define test operations
    def matrix_multiplication(size):
        """Simulate matrix multiplication."""
        # Create random matrices
        a = np.random.rand(size, size)
        b = np.random.rand(size, size)
        # Perform multiplication
        result = np.dot(a, b)
        return result.shape
    
    def data_processing(data_size):
        """Simulate data processing."""
        # Create test data
        data = pd.DataFrame({
            'A': np.random.rand(data_size),
            'B': np.random.rand(data_size),
            'C': np.random.rand(data_size)
        })
        # Perform some operations
        data['D'] = data['A'] * data['B']
        data['E'] = data['C'] + data['D']
        result = data['E'].sum()
        return result
    
    # Measure multiple executions
    print("Measuring matrix multiplication performance...")
    matrix_stats = time_measurer.measure_multiple_executions(
        "matrix_multiplication_50x50",
        matrix_multiplication,
        iterations=3,
        size=50
    )
    
    print("Measuring data processing performance...")
    data_stats = time_measurer.measure_multiple_executions(
        "data_processing_1000_rows",
        data_processing,
        iterations=3,
        data_size=1000
    )
    
    # Print results
    print("\nMatrix multiplication stats:")
    print(f"  Mean wall time: {matrix_stats['wall_time_stats']['mean']:.4f}s")
    print(f"  Success rate: {matrix_stats['successful_executions']}/{matrix_stats['iterations']}")
    
    print("\nData processing stats:")
    print(f"  Mean wall time: {data_stats['wall_time_stats']['mean']:.4f}s")
    print(f"  Success rate: {data_stats['successful_executions']}/{data_stats['iterations']}")
    
    # Compare operations
    comparison = time_measurer.compare_processing_times(matrix_stats, data_stats)
    if comparison['comparison_possible']:
        wall_comp = comparison['wall_time_comparison']
        print("\nComparison:")
        print(f"  Matrix operation is {abs(wall_comp['improvement']):.4f}s "
              f"({'faster' if wall_comp['improvement'] > 0 else 'slower'}) "
              f"than data processing "
              f"({wall_comp['improvement_percentage']:.1f}%)")
    
    # Print summary
    time_measurer.print_processing_time_summary()