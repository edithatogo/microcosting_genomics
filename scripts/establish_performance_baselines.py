"""Script to establish performance baseline metrics for genomics microcosting analysis.

This script runs comprehensive performance tests to establish baseline metrics
for various operations in the genomics microcosting framework.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys
from datetime import datetime

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from tests.test_load_testing import LoadTestingFramework  # noqa: E402
from tests.test_memory_monitoring import MemoryMonitor  # noqa: E402
from tests.test_processing_time import ProcessingTimeMeasurer  # noqa: E402
from tests.test_scalability import ScalabilityTester  # noqa: E402


def establish_performance_baselines():
    """Establish performance baselines for all major operations."""
    
    print("Establishing performance baselines...")
    print("=" * 50)
    
    # Initialize testing frameworks
    load_tester = LoadTestingFramework()
    memory_monitor = MemoryMonitor()
    time_measurer = ProcessingTimeMeasurer()
    scalability_tester = ScalabilityTester()
    
    baselines = {
        'timestamp': datetime.now().isoformat(),
        'load_testing': {},
        'memory_usage': {},
        'processing_time': {},
        'scalability': {}
    }
    
    # 1. Load Testing Baselines
    print("\n1. Running load testing baselines...")
    def sample_operation(df):
        return df['Total_Cost'].sum() if 'Total_Cost' in df.columns else len(df)
    
    load_sizes = [1000, 5000, 10000]
    load_results = load_tester.run_scalability_test(
        sizes=load_sizes,
        operation_name="baseline_load_test",
        test_function=sample_operation
    )
    
    baselines['load_testing'] = {
        'test_sizes': load_sizes,
        'results': load_results
    }
    
    # 2. Memory Usage Baselines
    print("\n2. Running memory usage baselines...")
    test_data = load_tester.generate_test_data(10000)
    memory_analysis = memory_monitor.analyze_dataframe_memory(test_data)
    
    baselines['memory_usage'] = {
        'test_data_size': len(test_data),
        'total_memory_mb': memory_analysis['total_memory_mb'],
        'column_memory_mb': memory_analysis['column_memory_mb']
    }
    
    # 3. Processing Time Baselines
    print("\n3. Running processing time baselines...")
    def processing_test():
        # Simulate some processing work
        data = list(range(10000))
        result = sum(x * 1.5 for x in data)
        return result
    
    time_stats = time_measurer.measure_multiple_executions(
        "baseline_processing",
        processing_test,
        iterations=5
    )
    
    baselines['processing_time'] = {
        'iterations': time_stats['iterations'],
        'successful_executions': time_stats['successful_executions'],
        'wall_time_mean': time_stats['wall_time_stats']['mean'],
        'wall_time_stdev': time_stats['wall_time_stats']['stdev'],
        'cpu_time_mean': time_stats['cpu_time_stats']['mean']
    }
    
    # 4. Scalability Baselines
    print("\n4. Running scalability baselines...")
    def simple_scalability_test(test_data):
        # Simple operation for scalability testing
        df = test_data.get('Detailed Table', pd.DataFrame())
        return len(df)
    
    scalability_sizes = [1000, 5000, 10000]
    scalability_results = scalability_tester.run_scalability_test(
        operation_name="baseline_scalability",
        test_function=simple_scalability_test,
        sizes=scalability_sizes,
        complexity="basic",
        iterations=3
    )
    
    scalability_analysis = scalability_tester.analyze_scaling_behavior(scalability_results)
    
    baselines['scalability'] = {
        'test_sizes': scalability_sizes,
        'results': scalability_results,
        'analysis': scalability_analysis
    }
    
    return baselines


def save_baselines(baselines: dict, output_file: str = None):
    """Save baselines to a JSON file.
    
    Args:
        baselines (dict): Baselines data to save
        output_file (str): Output file path (default: auto-generated)
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"performance_baselines_{timestamp}.json"
    
    # Convert numpy types to native Python types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        return obj
    
    baselines_converted = convert_numpy_types(baselines)
    
    with open(output_file, 'w') as f:
        json.dump(baselines_converted, f, indent=2)
    
    print(f"\nBaselines saved to: {output_file}")
    return output_file


def print_baseline_summary(baselines: dict):
    """Print a summary of the established baselines.
    
    Args:
        baselines (dict): Baselines data to summarize
    """
    print("\n" + "=" * 60)
    print("PERFORMANCE BASELINES SUMMARY")
    print("=" * 60)
    
    # Load Testing Summary
    load_results = baselines.get('load_testing', {}).get('results', [])
    if load_results:
        print("\nLoad Testing:")
        print("  Data Sizes Tested:", baselines['load_testing']['test_sizes'])
        for result in load_results:
            print(f"    {result['data_size']} rows: {result['execution_time']:.4f}s, "
                  f"{result['memory_used']:.2f}MB")
    
    # Memory Usage Summary
    memory_data = baselines.get('memory_usage', {})
    if memory_data:
        print("\nMemory Usage:")
        print(f"  Test Data Size: {memory_data.get('test_data_size', 0)} rows")
        print(f"  Total Memory: {memory_data.get('total_memory_mb', 0):.2f} MB")
        print("  Top Memory Consumers:")
        column_memory = memory_data.get('column_memory_mb', {})
        top_consumers = sorted(column_memory.items(), key=lambda x: x[1], reverse=True)[:3]
        for col, mem in top_consumers:
            print(f"    {col}: {mem:.2f} MB")
    
    # Processing Time Summary
    time_data = baselines.get('processing_time', {})
    if time_data:
        print("\nProcessing Time:")
        print(f"  Iterations: {time_data.get('iterations', 0)}")
        print(f"  Success Rate: {time_data.get('successful_executions', 0)}/{time_data.get('iterations', 0)}")
        print(f"  Mean Wall Time: {time_data.get('wall_time_mean', 0):.4f}s "
              f"(±{time_data.get('wall_time_stdev', 0):.4f})")
        print(f"  Mean CPU Time: {time_data.get('cpu_time_mean', 0):.4f}s")
    
    # Scalability Summary
    scalability_data = baselines.get('scalability', {})
    if scalability_data:
        analysis = scalability_data.get('analysis', {})
        print("\nScalability:")
        print(f"  Test Sizes: {scalability_data.get('test_sizes', [])}")
        print(f"  Scaling Behavior: {analysis.get('scaling_behavior', 'unknown')}")
        print(f"  Average Scaling Factor: {analysis.get('average_scaling_factor', 0):.2f}")


def load_baselines(input_file: str) -> dict:
    """Load baselines from a JSON file.
    
    Args:
        input_file (str): Input file path
        
    Returns:
        dict: Loaded baselines data
    """
    with open(input_file, 'r') as f:
        baselines = json.load(f)
    
    print(f"Baselines loaded from: {input_file}")
    return baselines


def compare_baselines(current_baselines: dict, reference_baselines: dict) -> dict:
    """Compare current baselines with reference baselines.
    
    Args:
        current_baselines (dict): Current baselines
        reference_baselines (dict): Reference baselines
        
    Returns:
        dict: Comparison results
    """
    comparison = {}
    
    # Compare processing times
    current_time = current_baselines.get('processing_time', {}).get('wall_time_mean', 0)
    reference_time = reference_baselines.get('processing_time', {}).get('wall_time_mean', 0)
    
    if current_time > 0 and reference_time > 0:
        time_change = ((current_time - reference_time) / reference_time) * 100
        comparison['processing_time'] = {
            'current': current_time,
            'reference': reference_time,
            'change_percentage': time_change,
            'performance_regression': time_change > 5  # 5% threshold
        }
    
    # Compare memory usage
    current_memory = current_baselines.get('memory_usage', {}).get('total_memory_mb', 0)
    reference_memory = reference_baselines.get('memory_usage', {}).get('total_memory_mb', 0)
    
    if current_memory > 0 and reference_memory > 0:
        memory_change = ((current_memory - reference_memory) / reference_memory) * 100
        comparison['memory_usage'] = {
            'current': current_memory,
            'reference': reference_memory,
            'change_percentage': memory_change,
            'memory_regression': memory_change > 5  # 5% threshold
        }
    
    # Compare scalability
    current_scaling = current_baselines.get('scalability', {}).get('analysis', {}).get('average_scaling_factor', 0)
    reference_scaling = reference_baselines.get('scalability', {}).get('analysis', {}).get('average_scaling_factor', 0)
    
    if current_scaling > 0 and reference_scaling > 0:
        scaling_change = ((current_scaling - reference_scaling) / reference_scaling) * 100
        comparison['scalability'] = {
            'current': current_scaling,
            'reference': reference_scaling,
            'change_percentage': scaling_change,
            'scaling_regression': scaling_change > 10  # 10% threshold
        }
    
    return comparison


def main():
    """Main function to establish and save performance baselines."""
    try:
        # Establish baselines
        baselines = establish_performance_baselines()
        
        # Print summary
        print_baseline_summary(baselines)
        
        # Save baselines
        output_file = save_baselines(baselines)
        
        print(f"\nPerformance baselines successfully established and saved to {output_file}")
        
        # Example of how to use baselines for comparison
        print("\nTo compare future performance against these baselines, use:")
        print(f"  python compare_performance.py {output_file}")
        
    except Exception as e:
        print(f"Error establishing performance baselines: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()