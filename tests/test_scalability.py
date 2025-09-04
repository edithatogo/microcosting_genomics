"""Scalability testing scenarios for genomics microcosting analysis.

This module provides comprehensive scalability testing scenarios to evaluate
how the genomics microcosting framework performs with increasing data sizes
and complexity.
"""

import unittest
import time
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, List, Callable, Tuple
import matplotlib.pyplot as plt
from unittest.mock import Mock, patch

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.performance import PerformanceProfiler, DataOptimizer
from unimelb_phd_phase_1.data_manager import DataManager
from unimelb_phd_phase_1.cost_driver_analysis import CostDriverAnalyzer


class ScalabilityTester:
    """Comprehensive scalability tester for genomics microcosting analysis."""
    
    def __init__(self):
        """Initialize the scalability tester."""
        self.profiler = PerformanceProfiler()
        self.results = []
    
    def generate_scalability_test_data(self, size: int, 
                                     complexity: str = "basic") -> Dict[str, pd.DataFrame]:
        """Generate test data of specified size and complexity.
        
        Args:
            size (int): Number of rows to generate
            complexity (str): Complexity level ("basic", "medium", "complex")
            
        Returns:
            Dict[str, pd.DataFrame]: Generated test data
        """
        np.random.seed(42 + size)  # Different seed for different sizes
        
        # Base data
        test_types = ['Panel', 'WES (P)', 'WES (T)', 'WGS']
        categories = ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage']
        
        if complexity == "basic":
            sub_categories = ['Sequencing', 'Library Prep', 'DNA Extraction']
            steps = ['Sample Prep']
        elif complexity == "medium":
            sub_categories = ['Sequencing', 'Library Prep', 'DNA Extraction', 'Processing', 'Analysis']
            steps = ['Sample Prep', 'QC', 'Processing']
        else:  # complex
            sub_categories = ['Sequencing', 'Library Prep', 'DNA Extraction', 'Processing', 'Analysis', 'Storage', 'Retrieval']
            steps = ['Sample Prep', 'QC', 'Processing', 'Analysis', 'Storage', 'Retrieval']
        
        # Generate main detailed table
        data = {
            'Test': np.random.choice(test_types, size),
            'Category': np.random.choice(categories, size),
            'Sub-Category': np.random.choice(sub_categories, size),
            'Step': np.random.choice(steps, size),
            'Quantity': np.random.uniform(0.5, 5.0, size),
            'Unit_Cost': np.random.uniform(50.0, 200.0, size),
        }
        
        # Calculate total cost
        data['Total_Cost'] = np.array(data['Quantity']) * np.array(data['Unit_Cost'])
        
        detailed_table = pd.DataFrame(data)
        
        # Generate additional sheets based on complexity
        additional_sheets = {}
        
        if complexity in ["medium", "complex"]:
            # DSA parameters
            dsa_params = {
                'Labour Prices': pd.DataFrame({
                    'Parameter': ['Hourly Rate', 'Overtime Rate'],
                    'Baseline': [50.0, 75.0],
                    'Low': [40.0, 60.0],
                    'High': [60.0, 90.0]
                }),
                'Equipment Throughput': pd.DataFrame({
                    'Parameter': ['Utilization Rate', 'Maintenance Factor'],
                    'Baseline': [0.8, 0.95],
                    'Low': [0.6, 0.9],
                    'High': [0.95, 0.99]
                })
            }
            additional_sheets.update(dsa_params)
        
        if complexity == "complex":
            # PSA parameters
            psa_params = {
                'PSA': pd.DataFrame({
                    'Parameter': ['Labour Cost', 'Equipment Cost', 'Consumable Cost', 'Compute Cost'],
                    'Distribution': ['normal', 'normal', 'normal', 'normal'],
                    'Mean': [50000, 40000, 30000, 20000],
                    'Std': [5000, 4000, 3000, 2000]
                })
            }
            additional_sheets.update(psa_params)
        
        return {
            'Detailed Table': detailed_table,
            **additional_sheets
        }
    
    def run_scalability_test(self, operation_name: str,
                           test_function: Callable,
                           sizes: List[int],
                           complexity: str = "basic",
                           iterations: int = 3) -> List[Dict[str, any]]:
        """Run scalability test across multiple data sizes.
        
        Args:
            operation_name (str): Name of the operation being tested
            test_function (Callable): Function to test
            sizes (List[int]): List of data sizes to test
            complexity (str): Complexity level
            iterations (int): Number of iterations per size
            
        Returns:
            List[Dict[str, any]]: Test results
        """
        results = []
        
        for size in sizes:
            print(f"Running scalability test for {operation_name} with {size} rows...")
            
            # Generate test data
            test_data = self.generate_scalability_test_data(size, complexity)
            
            # Run multiple iterations
            iteration_times = []
            iteration_memory = []
            
            for i in range(iterations):
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                try:
                    result = test_function(test_data)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                
                end_time = time.time()
                end_memory = self._get_memory_usage()
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                iteration_times.append(execution_time)
                iteration_memory.append(memory_used)
            
            # Calculate statistics
            if iteration_times:
                mean_time = sum(iteration_times) / len(iteration_times)
                min_time = min(iteration_times)
                max_time = max(iteration_times)
            else:
                mean_time = min_time = max_time = 0
            
            if iteration_memory:
                mean_memory = sum(iteration_memory) / len(iteration_memory)
            else:
                mean_memory = 0
            
            # Store results
            test_result = {
                'operation_name': operation_name,
                'data_size': size,
                'complexity': complexity,
                'iterations': iterations,
                'mean_execution_time': mean_time,
                'min_execution_time': min_time,
                'max_execution_time': max_time,
                'mean_memory_usage': mean_memory,
                'success_rate': sum(1 for t in iteration_times if t > 0) / iterations if iterations > 0 else 0,
                'timestamp': time.time()
            }
            
            results.append(test_result)
            self.results.append(test_result)
            
            print(f"  Mean time: {mean_time:.4f}s, Mean memory: {mean_memory:.2f}MB")
        
        return results
    
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
    
    def analyze_scaling_behavior(self, results: List[Dict[str, any]]) -> Dict[str, any]:
        """Analyze scaling behavior from test results.
        
        Args:
            results (List[Dict[str, any]]): Test results
            
        Returns:
            Dict[str, any]: Scaling analysis
        """
        if not results:
            return {'error': 'No results to analyze'}
        
        # Extract data points
        sizes = [r['data_size'] for r in results]
        times = [r['mean_execution_time'] for r in results]
        
        # Calculate scaling factors
        scaling_factors = []
        for i in range(1, len(sizes)):
            if sizes[i-1] > 0 and times[i-1] > 0:
                size_ratio = sizes[i] / sizes[i-1]
                time_ratio = times[i] / times[i-1]
                scaling_factor = time_ratio / size_ratio if size_ratio > 0 else 0
                scaling_factors.append(scaling_factor)
        
        avg_scaling_factor = sum(scaling_factors) / len(scaling_factors) if scaling_factors else 0
        
        # Classify scaling behavior
        if avg_scaling_factor < 0.5:
            scaling_behavior = "sub-linear (good)"
        elif avg_scaling_factor < 1.5:
            scaling_behavior = "linear (acceptable)"
        else:
            scaling_behavior = "super-linear (concerning)"
        
        return {
            'sizes': sizes,
            'times': times,
            'scaling_factors': scaling_factors,
            'average_scaling_factor': avg_scaling_factor,
            'scaling_behavior': scaling_behavior,
            'performance_regression': avg_scaling_factor > 2.0
        }
    
    def generate_scalability_report(self) -> pd.DataFrame:
        """Generate scalability report.
        
        Returns:
            pd.DataFrame: Scalability report
        """
        return pd.DataFrame(self.results)
    
    def plot_scalability_results(self, operation_name: str = None):
        """Plot scalability results.
        
        Args:
            operation_name (str): Specific operation to plot (None for all)
        """
        # Filter results
        if operation_name:
            results = [r for r in self.results if r['operation_name'] == operation_name]
        else:
            results = self.results
        
        if not results:
            print("No results to plot")
            return
        
        # Group by operation
        operations = {}
        for result in results:
            op_name = result['operation_name']
            if op_name not in operations:
                operations[op_name] = []
            operations[op_name].append(result)
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for op_name, op_results in operations.items():
            sizes = [r['data_size'] for r in op_results]
            times = [r['mean_execution_time'] for r in op_results]
            ax.plot(sizes, times, marker='o', label=op_name)
        
        ax.set_xlabel('Data Size (rows)')
        ax.set_ylabel('Execution Time (seconds)')
        ax.set_title('Scalability Analysis')
        ax.legend()
        ax.grid(True)
        
        plt.tight_layout()
        plt.show()


class GenomicsAnalysisScalability:
    """Scalability tests for genomics analysis operations."""
    
    def __init__(self):
        """Initialize the genomics analysis scalability tester."""
        self.tester = ScalabilityTester()
    
    def test_cost_driver_analysis_scalability(self, test_data: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """Test scalability of cost driver analysis.
        
        Args:
            test_data (Dict[str, pd.DataFrame]): Test data
            
        Returns:
            Dict[str, any]: Analysis results
        """
        # Mock data manager
        mock_data_manager = Mock(spec=DataManager)
        mock_data_manager.load_sheet.return_value = test_data.get('Detailed Table')
        
        # Initialize analyzer
        analyzer = CostDriverAnalyzer(mock_data_manager)
        
        # Run analysis
        detailed_table = test_data.get('Detailed Table', pd.DataFrame())
        cost_drivers = analyzer.calculate_absolute_cost_drivers(detailed_table)
        
        return {
            'cost_drivers_count': len(cost_drivers),
            'top_cost_driver': cost_drivers.iloc[0]['Category'] if len(cost_drivers) > 0 else None
        }
    
    def test_data_loading_scalability(self, test_data: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """Test scalability of data loading operations.
        
        Args:
            test_data (Dict[str, pd.DataFrame]): Test data
            
        Returns:
            Dict[str, any]: Loading results
        """
        # Simulate data loading
        total_rows = 0
        total_columns = 0
        
        for sheet_name, df in test_data.items():
            total_rows += len(df)
            total_columns += len(df.columns)
        
        return {
            'sheets_loaded': len(test_data),
            'total_rows': total_rows,
            'total_columns': total_columns
        }
    
    def test_data_optimization_scalability(self, test_data: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """Test scalability of data optimization operations.
        
        Args:
            test_data (Dict[str, pd.DataFrame]): Test data
            
        Returns:
            Dict[str, any]: Optimization results
        """
        optimizer = DataOptimizer()
        
        # Optimize each DataFrame
        optimized_sheets = {}
        for sheet_name, df in test_data.items():
            optimized_df = optimizer.optimize_dataframe(df)
            optimized_sheets[sheet_name] = optimized_df
        
        # Calculate memory savings
        original_memory = sum(df.memory_usage(deep=True).sum() for df in test_data.values())
        optimized_memory = sum(df.memory_usage(deep=True).sum() for df in optimized_sheets.values())
        
        memory_savings = original_memory - optimized_memory
        savings_percentage = (memory_savings / original_memory * 100) if original_memory > 0 else 0
        
        return {
            'sheets_optimized': len(optimized_sheets),
            'memory_savings_mb': memory_savings / 1024 / 1024,
            'savings_percentage': savings_percentage
        }


class TestScalability(unittest.TestCase):
    """Scalability testing scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scalability_tester = ScalabilityTester()
        self.genomics_scalability = GenomicsAnalysisScalability()
    
    def test_generate_scalability_test_data(self):
        """Test generation of scalability test data."""
        # Test basic complexity
        basic_data = self.scalability_tester.generate_scalability_test_data(1000, "basic")
        self.assertIsInstance(basic_data, dict)
        self.assertIn('Detailed Table', basic_data)
        self.assertEqual(len(basic_data['Detailed Table']), 1000)
        
        # Test medium complexity
        medium_data = self.scalability_tester.generate_scalability_test_data(1000, "medium")
        self.assertIn('Detailed Table', medium_data)
        self.assertIn('Labour Prices', medium_data)
        
        # Test complex complexity
        complex_data = self.scalability_tester.generate_scalability_test_data(1000, "complex")
        self.assertIn('Detailed Table', complex_data)
        self.assertIn('PSA', complex_data)
    
    def test_run_scalability_test(self):
        """Test running scalability tests."""
        def simple_operation(test_data):
            # Simple operation that works with any test data
            df = test_data.get('Detailed Table', pd.DataFrame())
            return len(df)
        
        sizes = [100, 500, 1000]
        results = self.scalability_tester.run_scalability_test(
            "simple_operation",
            simple_operation,
            sizes,
            "basic",
            iterations=2
        )
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), len(sizes))
        
        # Check results structure
        for result in results:
            self.assertIn('operation_name', result)
            self.assertIn('data_size', result)
            self.assertIn('mean_execution_time', result)
            self.assertIn('success_rate', result)
            self.assertEqual(result['operation_name'], 'simple_operation')
    
    def test_analyze_scaling_behavior(self):
        """Test scaling behavior analysis."""
        # Create mock results
        mock_results = [
            {'data_size': 100, 'mean_execution_time': 0.1},
            {'data_size': 500, 'mean_execution_time': 0.5},
            {'data_size': 1000, 'mean_execution_time': 1.0}
        ]
        
        analysis = self.scalability_tester.analyze_scaling_behavior(mock_results)
        
        self.assertIsInstance(analysis, dict)
        self.assertIn('scaling_behavior', analysis)
        self.assertIn('average_scaling_factor', analysis)
        
        # Should show linear or sub-linear scaling for this data
        self.assertIn(analysis['scaling_behavior'], 
                     ['sub-linear (good)', 'linear (acceptable)'])
    
    def test_cost_driver_analysis_scalability(self):
        """Test scalability of cost driver analysis."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(1000, "basic")
        
        # Test cost driver analysis
        result = self.genomics_scalability.test_cost_driver_analysis_scalability(test_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('cost_drivers_count', result)
        self.assertGreaterEqual(result['cost_drivers_count'], 0)
    
    def test_data_loading_scalability(self):
        """Test scalability of data loading operations."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(1000, "complex")
        
        # Test data loading
        result = self.genomics_scalability.test_data_loading_scalability(test_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheets_loaded', result)
        self.assertIn('total_rows', result)
        self.assertIn('total_columns', result)
        self.assertGreater(result['sheets_loaded'], 0)
        self.assertGreater(result['total_rows'], 0)
    
    def test_data_optimization_scalability(self):
        """Test scalability of data optimization operations."""
        # Generate test data
        test_data = self.scalability_tester.generate_scalability_test_data(10000, "basic")
        
        # Test data optimization
        result = self.genomics_scalability.test_data_optimization_scalability(test_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheets_optimized', result)
        self.assertIn('memory_savings_mb', result)
        self.assertIn('savings_percentage', result)
        self.assertGreaterEqual(result['sheets_optimized'], 0)


class PerformanceBaselineEstablisher:
    """Establish performance baselines for different operations."""
    
    def __init__(self):
        """Initialize the baseline establisher."""
        self.scalability_tester = ScalabilityTester()
        self.genomics_scalability = GenomicsAnalysisScalability()
    
    def establish_baselines(self) -> Dict[str, Dict[str, any]]:
        """Establish performance baselines.
        
        Returns:
            Dict[str, Dict[str, any]]: Performance baselines
        """
        baselines = {}
        
        # Define test scenarios
        scenarios = [
            {
                'name': 'cost_driver_analysis',
                'function': self.genomics_scalability.test_cost_driver_analysis_scalability,
                'sizes': [1000, 5000, 10000],
                'complexity': 'basic'
            },
            {
                'name': 'data_loading',
                'function': self.genomics_scalability.test_data_loading_scalability,
                'sizes': [1000, 5000, 10000],
                'complexity': 'complex'
            },
            {
                'name': 'data_optimization',
                'function': self.genomics_scalability.test_data_optimization_scalability,
                'sizes': [10000, 50000, 100000],
                'complexity': 'basic'
            }
        ]
        
        # Run baseline tests
        for scenario in scenarios:
            print(f"Establishing baseline for {scenario['name']}...")
            results = self.scalability_tester.run_scalability_test(
                scenario['name'],
                scenario['function'],
                scenario['sizes'],
                scenario['complexity'],
                iterations=3
            )
            
            analysis = self.scalability_tester.analyze_scaling_behavior(results)
            baselines[scenario['name']] = {
                'results': results,
                'analysis': analysis
            }
        
        return baselines
    
    def compare_against_baselines(self, current_results: List[Dict[str, any]], 
                                baselines: Dict[str, Dict[str, any]]) -> Dict[str, any]:
        """Compare current results against established baselines.
        
        Args:
            current_results (List[Dict[str, any]]): Current test results
            baselines (Dict[str, Dict[str, any]]): Established baselines
            
        Returns:
            Dict[str, any]: Comparison results
        """
        comparisons = {}
        
        for operation_name, baseline_data in baselines.items():
            baseline_results = baseline_data['results']
            if not baseline_results:
                continue
                
            # Find corresponding current results
            current_op_results = [r for r in current_results if r['operation_name'] == operation_name]
            if not current_op_results:
                continue
            
            # Compare at similar data sizes
            for current_result in current_op_results:
                current_size = current_result['data_size']
                
                # Find baseline result for similar size
                baseline_result = min(baseline_results, 
                                    key=lambda x: abs(x['data_size'] - current_size))
                
                if baseline_result:
                    time_regression = (
                        current_result['mean_execution_time'] > 
                        baseline_result['mean_execution_time'] * 1.1  # 10% threshold
                    )
                    
                    comparisons[operation_name] = {
                        'current_time': current_result['mean_execution_time'],
                        'baseline_time': baseline_result['mean_execution_time'],
                        'regression_detected': time_regression,
                        'time_difference': (
                            current_result['mean_execution_time'] - 
                            baseline_result['mean_execution_time']
                        )
                    }
        
        return comparisons


# Example usage:
if __name__ == "__main__":
    # Create scalability tester
    scalability_tester = ScalabilityTester()
    genomics_scalability = GenomicsAnalysisScalability()
    
    # Define test operations
    def cost_driver_test(test_data):
        return genomics_scalability.test_cost_driver_analysis_scalability(test_data)
    
    def data_loading_test(test_data):
        return genomics_scalability.test_data_loading_scalability(test_data)
    
    # Run scalability tests
    print("Running cost driver analysis scalability test...")
    cost_driver_results = scalability_tester.run_scalability_test(
        "cost_driver_analysis",
        cost_driver_test,
        sizes=[1000, 5000, 10000],
        complexity="basic",
        iterations=2
    )
    
    print("\nRunning data loading scalability test...")
    data_loading_results = scalability_tester.run_scalability_test(
        "data_loading",
        data_loading_test,
        sizes=[1000, 5000, 10000],
        complexity="complex",
        iterations=2
    )
    
    # Analyze scaling behavior
    print("\nAnalyzing cost driver analysis scaling behavior...")
    cost_driver_analysis = scalability_tester.analyze_scaling_behavior(cost_driver_results)
    print(f"Scaling behavior: {cost_driver_analysis['scaling_behavior']}")
    print(f"Average scaling factor: {cost_driver_analysis['average_scaling_factor']:.2f}")
    
    print("\nAnalyzing data loading scaling behavior...")
    data_loading_analysis = scalability_tester.analyze_scaling_behavior(data_loading_results)
    print(f"Scaling behavior: {data_loading_analysis['scaling_behavior']}")
    print(f"Average scaling factor: {data_loading_analysis['average_scaling_factor']:.2f}")
    
    # Generate report
    report = scalability_tester.generate_scalability_report()
    print(f"\nGenerated {len(report)} test results")
    
    # Show summary
    print("\nScalability Test Summary:")
    print("=" * 50)
    for _, row in report.iterrows():
        print(f"{row['operation_name']:<25} {row['data_size']:<10} "
              f"{row['mean_execution_time']:<10.4f}s {row['mean_memory_usage']:<10.2f}MB")