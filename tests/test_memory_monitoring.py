"""Memory usage monitoring tools for genomics microcosting analysis.

This module provides tools to monitor and analyze memory usage during
pandas DataFrame operations in the genomics microcosting framework.
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import time
from typing import Dict, List, Tuple
import tracemalloc

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.performance import DataOptimizer  # noqa: E402


class MemoryMonitor:
    """Memory monitoring tool for pandas DataFrame operations."""
    
    def __init__(self):
        """Initialize the memory monitor."""
        self.snapshots = []
        self.monitoring_enabled = False
    
    def start_monitoring(self):
        """Start memory monitoring."""
        tracemalloc.start()
        self.monitoring_enabled = True
        self.take_snapshot("start")
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.take_snapshot("end")
        tracemalloc.stop()
        self.monitoring_enabled = False
    
    def take_snapshot(self, label: str = ""):
        """Take a memory snapshot.
        
        Args:
            label (str): Label for the snapshot
        """
        if not self.monitoring_enabled:
            return
            
        snapshot = tracemalloc.take_snapshot()
        timestamp = time.time()
        self.snapshots.append({
            'label': label,
            'snapshot': snapshot,
            'timestamp': timestamp
        })
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB.
        
        Returns:
            float: Current memory usage in MB
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def analyze_dataframe_memory(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze memory usage of a DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze
            
        Returns:
            Dict[str, float]: Memory usage analysis
        """
        # Get memory usage for entire DataFrame
        total_memory = df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        
        # Get memory usage by column
        column_memory = {}
        for col in df.columns:
            column_memory[col] = df[col].memory_usage(deep=True) / 1024 / 1024  # MB
        
        # Get data types
        dtypes = {}
        for col in df.columns:
            dtypes[col] = str(df[col].dtype)
        
        return {
            'total_memory_mb': total_memory,
            'column_memory_mb': column_memory,
            'data_types': dtypes,
            'shape': df.shape
        }
    
    def compare_memory_usage(self, before_df: pd.DataFrame, 
                           after_df: pd.DataFrame) -> Dict[str, float]:
        """Compare memory usage between two DataFrames.
        
        Args:
            before_df (pd.DataFrame): DataFrame before operation
            after_df (pd.DataFrame): DataFrame after operation
            
        Returns:
            Dict[str, float]: Memory usage comparison
        """
        before_usage = self.analyze_dataframe_memory(before_df)
        after_usage = self.analyze_dataframe_memory(after_df)
        
        return {
            'before_total_mb': before_usage['total_memory_mb'],
            'after_total_mb': after_usage['total_memory_mb'],
            'memory_savings_mb': before_usage['total_memory_mb'] - after_usage['total_memory_mb'],
            'memory_savings_percentage': (
                (before_usage['total_memory_mb'] - after_usage['total_memory_mb']) / 
                before_usage['total_memory_mb'] * 100
            ) if before_usage['total_memory_mb'] > 0 else 0
        }
    
    def get_top_memory_consumers(self, df: pd.DataFrame, 
                               top_n: int = 10) -> List[Tuple[str, float]]:
        """Get top memory consuming columns.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze
            top_n (int): Number of top consumers to return
            
        Returns:
            List[Tuple[str, float]]: List of (column, memory_mb) tuples
        """
        column_memory = self.analyze_dataframe_memory(df)['column_memory_mb']
        sorted_columns = sorted(column_memory.items(), key=lambda x: x[1], reverse=True)
        return sorted_columns[:top_n]
    
    def generate_memory_report(self, df: pd.DataFrame) -> str:
        """Generate a formatted memory usage report.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze
            
        Returns:
            str: Formatted memory report
        """
        analysis = self.analyze_dataframe_memory(df)
        top_consumers = self.get_top_memory_consumers(df, 5)
        
        report = []
        report.append("Memory Usage Report")
        report.append("=" * 50)
        report.append(f"DataFrame Shape: {analysis['shape'][0]} rows × {analysis['shape'][1]} columns")
        report.append(f"Total Memory Usage: {analysis['total_memory_mb']:.2f} MB")
        report.append("")
        report.append("Top Memory Consumers:")
        for col, memory_mb in top_consumers:
            dtype = analysis['data_types'].get(col, 'unknown')
            report.append(f"  {col} ({dtype}): {memory_mb:.2f} MB")
        
        return "\n".join(report)


class DataFrameMemoryTester:
    """Test memory usage of various DataFrame operations."""
    
    def __init__(self):
        """Initialize the tester."""
        self.monitor = MemoryMonitor()
        self.optimizer = DataOptimizer()
    
    def test_merge_operations(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                            merge_key: str) -> Dict[str, any]:
        """Test memory usage of DataFrame merge operations.
        
        Args:
            df1 (pd.DataFrame): First DataFrame
            df2 (pd.DataFrame): Second DataFrame
            merge_key (str): Key column for merging
            
        Returns:
            Dict[str, any]: Test results
        """
        self.monitor.start_monitoring()
        
        # Measure memory before merge
        memory_before = self.monitor.get_memory_usage()
        
        # Perform merge
        start_time = time.time()
        merged_df = pd.merge(df1, df2, on=merge_key, how='inner')
        merge_time = time.time() - start_time
        
        # Measure memory after merge
        memory_after = self.monitor.get_memory_usage()
        
        self.monitor.stop_monitoring()
        
        return {
            'merged_dataframe': merged_df,
            'merge_time': merge_time,
            'memory_before_mb': memory_before,
            'memory_after_mb': memory_after,
            'memory_increase_mb': memory_after - memory_before,
            'result_shape': merged_df.shape
        }
    
    def test_groupby_operations(self, df: pd.DataFrame, 
                              group_column: str) -> Dict[str, any]:
        """Test memory usage of DataFrame groupby operations.
        
        Args:
            df (pd.DataFrame): DataFrame to group
            group_column (str): Column to group by
            
        Returns:
            Dict[str, any]: Test results
        """
        self.monitor.start_monitoring()
        
        # Measure memory before groupby
        memory_before = self.monitor.get_memory_usage()
        
        # Perform groupby
        start_time = time.time()
        grouped = df.groupby(group_column)
        aggregated = grouped.agg({
            'Total_Cost': ['sum', 'mean', 'count'],
            'Quantity': ['sum', 'mean']
        })
        groupby_time = time.time() - start_time
        
        # Measure memory after groupby
        memory_after = self.monitor.get_memory_usage()
        
        self.monitor.stop_monitoring()
        
        return {
            'aggregated_dataframe': aggregated,
            'groupby_time': groupby_time,
            'memory_before_mb': memory_before,
            'memory_after_mb': memory_after,
            'memory_increase_mb': memory_after - memory_before,
            'result_shape': aggregated.shape
        }
    
    def test_pivot_operations(self, df: pd.DataFrame, index: str, 
                            columns: str, values: str) -> Dict[str, any]:
        """Test memory usage of DataFrame pivot operations.
        
        Args:
            df (pd.DataFrame): DataFrame to pivot
            index (str): Index column
            columns (str): Columns column
            values (str): Values column
            
        Returns:
            Dict[str, any]: Test results
        """
        self.monitor.start_monitoring()
        
        # Measure memory before pivot
        memory_before = self.monitor.get_memory_usage()
        
        # Perform pivot
        start_time = time.time()
        pivoted_df = df.pivot_table(index=index, columns=columns, values=values, aggfunc='sum')
        pivot_time = time.time() - start_time
        
        # Measure memory after pivot
        memory_after = self.monitor.get_memory_usage()
        
        self.monitor.stop_monitoring()
        
        return {
            'pivoted_dataframe': pivoted_df,
            'pivot_time': pivot_time,
            'memory_before_mb': memory_before,
            'memory_after_mb': memory_after,
            'memory_increase_mb': memory_after - memory_before,
            'result_shape': pivoted_df.shape
        }


class TestMemoryMonitoring(unittest.TestCase):
    """Memory monitoring tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = MemoryMonitor()
        self.tester = DataFrameMemoryTester()
    
    def generate_test_data(self, size: int) -> pd.DataFrame:
        """Generate test data for memory testing.
        
        Args:
            size (int): Number of rows to generate
            
        Returns:
            pd.DataFrame: Generated test data
        """
        np.random.seed(42)
        
        test_types = ['Panel', 'WES (P)', 'WES (T)', 'WGS']
        categories = ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage']
        
        data = {
            'Test': np.random.choice(test_types, size),
            'Category': np.random.choice(categories, size),
            'Quantity': np.random.uniform(0.5, 5.0, size),
            'Unit_Cost': np.random.uniform(50.0, 200.0, size),
            'Year': np.random.choice([2023, 2024, 2025], size)
        }
        
        # Calculate total cost
        data['Total_Cost'] = np.array(data['Quantity']) * np.array(data['Unit_Cost'])
        
        return pd.DataFrame(data)
    
    def test_memory_monitoring_basic(self):
        """Test basic memory monitoring functionality."""
        # Test memory usage measurement
        memory_usage = self.monitor.get_memory_usage()
        self.assertIsInstance(memory_usage, float)
        self.assertGreaterEqual(memory_usage, 0)
        
        # Test monitoring start/stop
        self.assertFalse(self.monitor.monitoring_enabled)
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring_enabled)
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring_enabled)
    
    def test_dataframe_memory_analysis(self):
        """Test DataFrame memory analysis."""
        # Create test DataFrame
        df = self.generate_test_data(1000)
        
        # Analyze memory usage
        analysis = self.monitor.analyze_dataframe_memory(df)
        
        # Check analysis results
        self.assertIn('total_memory_mb', analysis)
        self.assertIn('column_memory_mb', analysis)
        self.assertIn('data_types', analysis)
        self.assertIn('shape', analysis)
        
        self.assertIsInstance(analysis['total_memory_mb'], float)
        self.assertGreater(analysis['total_memory_mb'], 0)
        self.assertEqual(analysis['shape'], (1000, 6))
        
        # Check column memory analysis
        column_memory = analysis['column_memory_mb']
        self.assertIsInstance(column_memory, dict)
        self.assertIn('Test', column_memory)
        self.assertIn('Category', column_memory)
        self.assertIn('Total_Cost', column_memory)
    
    def test_memory_comparison(self):
        """Test memory usage comparison."""
        # Create test DataFrames
        df1 = self.generate_test_data(1000)
        df2 = self.generate_test_data(500)  # Smaller DataFrame
        
        # Compare memory usage
        comparison = self.monitor.compare_memory_usage(df1, df2)
        
        self.assertIn('before_total_mb', comparison)
        self.assertIn('after_total_mb', comparison)
        self.assertIn('memory_savings_mb', comparison)
        self.assertIn('memory_savings_percentage', comparison)
        
        # df1 should be larger than df2
        self.assertGreater(comparison['before_total_mb'], comparison['after_total_mb'])
    
    def test_top_memory_consumers(self):
        """Test identification of top memory consumers."""
        # Create test DataFrame
        df = self.generate_test_data(10000)
        
        # Get top consumers
        top_consumers = self.monitor.get_top_memory_consumers(df, 3)
        
        self.assertIsInstance(top_consumers, list)
        self.assertLessEqual(len(top_consumers), 3)
        
        # Each item should be a tuple of (column, memory_mb)
        for item in top_consumers:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], str)  # column name
            self.assertIsInstance(item[1], float)  # memory in MB
    
    def test_merge_operation_memory(self):
        """Test memory usage of merge operations."""
        # Create test DataFrames
        df1 = self.generate_test_data(1000)
        df2 = self.generate_test_data(500)
        
        # Add a common key column for merging
        df1['Merge_Key'] = np.random.randint(1, 100, len(df1))
        df2['Merge_Key'] = np.random.randint(1, 100, len(df2))
        
        # Test merge operation
        result = self.tester.test_merge_operations(df1, df2, 'Merge_Key')
        
        self.assertIn('merged_dataframe', result)
        self.assertIn('merge_time', result)
        self.assertIn('memory_increase_mb', result)
        self.assertIn('result_shape', result)
        
        self.assertIsInstance(result['merged_dataframe'], pd.DataFrame)
        self.assertGreaterEqual(result['merge_time'], 0)
        self.assertIsInstance(result['result_shape'], tuple)
    
    def test_groupby_operation_memory(self):
        """Test memory usage of groupby operations."""
        # Create test DataFrame
        df = self.generate_test_data(5000)
        
        # Test groupby operation
        result = self.tester.test_groupby_operations(df, 'Category')
        
        self.assertIn('aggregated_dataframe', result)
        self.assertIn('groupby_time', result)
        self.assertIn('result_shape', result)
        
        self.assertIsInstance(result['aggregated_dataframe'], pd.DataFrame)
        self.assertGreaterEqual(result['groupby_time'], 0)
        self.assertIsInstance(result['result_shape'], tuple)
    
    def test_memory_report_generation(self):
        """Test memory report generation."""
        # Create test DataFrame
        df = self.generate_test_data(1000)
        
        # Generate report
        report = self.monitor.generate_memory_report(df)
        
        self.assertIsInstance(report, str)
        self.assertIn('Memory Usage Report', report)
        self.assertIn('Total Memory Usage', report)
        self.assertIn('Top Memory Consumers', report)


class MemoryOptimizationBenchmark:
    """Benchmark memory optimization techniques."""
    
    def __init__(self):
        """Initialize the benchmark."""
        self.monitor = MemoryMonitor()
        self.optimizer = DataOptimizer()
    
    def benchmark_optimization_techniques(self, df: pd.DataFrame) -> Dict[str, any]:
        """Benchmark different memory optimization techniques.
        
        Args:
            df (pd.DataFrame): DataFrame to optimize
            
        Returns:
            Dict[str, any]: Benchmark results
        """
        results = {}
        
        # Baseline memory usage
        baseline_analysis = self.monitor.analyze_dataframe_memory(df)
        results['baseline'] = baseline_analysis
        
        # Test DataFrame optimization
        start_time = time.time()
        optimized_df = self.optimizer.optimize_dataframe(df.copy())
        optimization_time = time.time() - start_time
        
        optimized_analysis = self.monitor.analyze_dataframe_memory(optimized_df)
        
        results['optimized'] = {
            'analysis': optimized_analysis,
            'optimization_time': optimization_time,
            'memory_savings_mb': baseline_analysis['total_memory_mb'] - optimized_analysis['total_memory_mb'],
            'memory_savings_percentage': (
                (baseline_analysis['total_memory_mb'] - optimized_analysis['total_memory_mb']) / 
                baseline_analysis['total_memory_mb'] * 100
            ) if baseline_analysis['total_memory_mb'] > 0 else 0
        }
        
        # Test chunked processing
        start_time = time.time()
        chunked_df = self.optimizer.chunked_processing(df.copy(), chunk_size=1000)
        chunking_time = time.time() - start_time
        
        chunked_analysis = self.monitor.analyze_dataframe_memory(chunked_df)
        
        results['chunked'] = {
            'analysis': chunked_analysis,
            'chunking_time': chunking_time
        }
        
        return results


# Example usage:
if __name__ == "__main__":
    # Create memory monitor
    monitor = MemoryMonitor()
    
    # Generate test data
    np.random.seed(42)
    test_data = pd.DataFrame({
        'Category': np.random.choice(['Labour', 'Equipment', 'Consumables'], 10000),
        'Sub_Category': np.random.choice(['Sequencing', 'Library Prep', 'DNA Extraction'], 10000),
        'Quantity': np.random.uniform(0.5, 5.0, 10000),
        'Unit_Cost': np.random.uniform(50.0, 200.0, 10000),
        'Description': ['Test description ' + str(i) for i in range(10000)]
    })
    
    # Calculate total cost
    test_data['Total_Cost'] = test_data['Quantity'] * test_data['Unit_Cost']
    
    # Analyze memory usage
    print("Analyzing DataFrame memory usage...")
    analysis = monitor.analyze_dataframe_memory(test_data)
    print(f"Total memory usage: {analysis['total_memory_mb']:.2f} MB")
    print(f"DataFrame shape: {analysis['shape']}")
    
    # Show top memory consumers
    print("\nTop memory consumers:")
    top_consumers = monitor.get_top_memory_consumers(test_data, 5)
    for col, memory_mb in top_consumers:
        dtype = analysis['data_types'].get(col, 'unknown')
        print(f"  {col} ({dtype}): {memory_mb:.2f} MB")
    
    # Generate full report
    print("\n" + monitor.generate_memory_report(test_data))