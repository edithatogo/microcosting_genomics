#!/usr/bin/env python3
"""
Script to profile and optimize the performance of microcosting analysis.
"""

import sys
from pathlib import Path
import pandas as pd
import time
import argparse
import json
from typing import Dict, Any

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.performance import PerformanceProfiler, DataOptimizer, CachingOptimizer, ParallelProcessor
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager
from unimelb_phd_phase_1.visualization import load_prepared_data


def profile_data_loading(profiler: PerformanceProfiler, data_dir: Path) -> Dict[str, Any]:
    """Profile data loading performance.
    
    Args:
        profiler: PerformanceProfiler instance
        data_dir: Directory containing prepared data
        
    Returns:
        Dictionary with profiling results
    """
    print("Profiling data loading performance...")
    
    @profiler.profile("load_prepared_data")
    def load_data():
        return load_prepared_data(data_dir)
    
    try:
        data_dict = load_data()
        print(f"Loaded {len(data_dict)} data tables")
        return {"status": "success", "table_count": len(data_dict), "data": data_dict}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"status": "error", "error": str(e)}


def profile_calculation_engine(profiler: PerformanceProfiler, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Profile calculation engine performance.
    
    Args:
        profiler: PerformanceProfiler instance
        data_dict: Dictionary of loaded data tables
        
    Returns:
        Dictionary with profiling results
    """
    print("Profiling calculation engine performance...")
    
    @profiler.profile("initialize_engine")
    def init_engine():
        sheet_manager = SheetManager()
        engine = CalculationEngine(sheet_manager)
        return engine
    
    @profiler.profile("run_engine")
    def run_engine(engine):
        return engine.run_engine()
    
    try:
        engine = init_engine()
        results_df, errors = run_engine(engine)
        
        print(f"Calculation engine completed with {len(errors) if errors else 0} errors")
        return {
            "status": "success", 
            "result_shape": results_df.shape if results_df is not None else None,
            "error_count": len(errors) if errors else 0
        }
    except Exception as e:
        print(f"Error running calculation engine: {e}")
        return {"status": "error", "error": str(e)}


def optimize_dataframes(data_dict: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, pd.DataFrame]:
    """Optimize DataFrames for better memory usage.
    
    Args:
        data_dict: Dictionary of DataFrames to optimize
        output_dir: Directory to save optimized data
        
    Returns:
        Dictionary of optimized DataFrames
    """
    print("Optimizing DataFrames...")
    optimizer = DataOptimizer()
    
    optimized_data = {}
    optimization_stats = []
    
    for table_name, df in data_dict.items():
        print(f"  Optimizing {table_name} ({df.shape})...")
        start_time = time.time()
        
        original_memory = df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        optimized_df = optimizer.optimize_dataframe(df)
        optimized_memory = optimized_df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        
        end_time = time.time()
        
        savings = original_memory - optimized_memory
        savings_percent = (savings / original_memory) * 100 if original_memory > 0 else 0
        
        optimization_stats.append({
            "table": table_name,
            "original_memory_mb": original_memory,
            "optimized_memory_mb": optimized_memory,
            "savings_mb": savings,
            "savings_percent": savings_percent,
            "processing_time_seconds": end_time - start_time
        })
        
        optimized_data[table_name] = optimized_df
        
        # Save optimized DataFrame
        optimized_file = output_dir / f"optimized_{table_name}.parquet"
        optimized_df.to_parquet(optimized_file)
        print(f"    Saved optimized data to {optimized_file}")
    
    # Save optimization statistics
    stats_file = output_dir / "optimization_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(optimization_stats, f, indent=2)
    print(f"  Saved optimization statistics to {stats_file}")
    
    return optimized_data


def benchmark_parallel_processing(data_dict: Dict[str, pd.DataFrame], profiler: PerformanceProfiler) -> Dict[str, Any]:
    """Benchmark parallel processing capabilities.
    
    Args:
        data_dict: Dictionary of DataFrames
        profiler: PerformanceProfiler instance
        
    Returns:
        Dictionary with benchmark results
    """
    print("Benchmarking parallel processing...")
    
    # Find the largest table for benchmarking
    largest_table = max(data_dict.items(), key=lambda x: len(x[1]))[0] if data_dict else None
    
    if not largest_table:
        return {"status": "skipped", "reason": "No data available"}
    
    df = data_dict[largest_table]
    print(f"  Using {largest_table} with {len(df)} rows for benchmarking")
    
    # Create a test function to apply
    def test_function(series_chunk):
        # Simulate some computation
        return series_chunk.apply(lambda x: x * 1.1 if isinstance(x, (int, float)) else x)
    
    # Profile sequential processing
    @profiler.profile(f"sequential_processing_{largest_table}")
    def sequential_processing():
        if len(df.columns) > 0:
            # Process the first numeric column
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    return df[col].apply(test_function)
        return None
    
    # Profile parallel processing
    @profiler.profile(f"parallel_processing_{largest_table}")
    def parallel_processing():
        if len(df.columns) > 0:
            # Process the first numeric column
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        return ParallelProcessor().parallel_apply(df, test_function, col, n_cores=4)
                    except Exception as e:
                        print(f"    Parallel processing failed: {e}")
                        # Fall back to sequential
                        return df[col].apply(test_function)
        return None
    
    try:
        print("    Running sequential processing...")
        sequential_result = sequential_processing()
        
        print("    Running parallel processing...")
        parallel_result = parallel_processing()
        
        return {
            "status": "success",
            "table": largest_table,
            "rows_processed": len(df),
            "sequential_result_shape": sequential_result.shape if sequential_result is not None else None,
            "parallel_result_shape": parallel_result.shape if parallel_result is not None else None
        }
    except Exception as e:
        print(f"  Error in parallel processing benchmark: {e}")
        return {"status": "error", "error": str(e)}


def test_caching_performance(data_dict: Dict[str, pd.DataFrame], profiler: PerformanceProfiler) -> Dict[str, Any]:
    """Test caching performance improvements.
    
    Args:
        data_dict: Dictionary of DataFrames
        profiler: PerformanceProfiler instance
        
    Returns:
        Dictionary with caching test results
    """
    print("Testing caching performance...")
    cache = CachingOptimizer()
    
    # Test caching with a sample operation
    @profiler.profile("cache_test_operation")
    def expensive_operation(data):
        # Simulate an expensive operation
        time.sleep(0.01)  # 10ms delay
        return data.sum().sum() if isinstance(data, pd.DataFrame) else 0
    
    # Find a reasonably sized table
    test_table = None
    for name, df in data_dict.items():
        if len(df) > 100:  # At least 100 rows
            test_table = name
            break
    
    if not test_table:
        return {"status": "skipped", "reason": "No suitable table found for caching test"}
    
    df = data_dict[test_table]
    print(f"  Testing caching with {test_table}")
    
    # Run operation without caching first
    print("    Running operation without caching...")
    result1 = expensive_operation(df)
    
    # Cache the result
    cache.set(f"expensive_op_{test_table}", result1)
    
    # Run operation with caching
    @profiler.profile("cached_operation")
    def cached_operation():
        cached_result = cache.get(f"expensive_op_{test_table}")
        if cached_result is not None:
            return cached_result
        else:
            result = expensive_operation(df)
            cache.set(f"expensive_op_{test_table}", result)
            return result
    
    print("    Running operation with caching...")
    result2 = cached_operation()
    
    # Get cache statistics
    cache_stats = cache.get_stats()
    
    return {
        "status": "success",
        "table": test_table,
        "original_result": result1,
        "cached_result": result2,
        "cache_stats": cache_stats
    }


def generate_performance_report(profiler: PerformanceProfiler, optimization_stats: Dict[str, Any], 
                              output_dir: Path) -> None:
    """Generate a comprehensive performance report.
    
    Args:
        profiler: PerformanceProfiler instance
        optimization_stats: Data optimization statistics
        output_dir: Directory to save report
    """
    print("Generating performance report...")
    
    report = []
    report.append("# Performance Analysis Report")
    report.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Add profiling results
    report.append("## Performance Profiling Results")
    report.append("")
    
    metrics = profiler.get_report()
    if metrics:
        report.append("| Operation | Calls | Avg Time (s) | Max Time (s) | Memory (MB) | Errors |")
        report.append("|-----------|-------|--------------|--------------|-------------|--------|")
        
        for operation, data in metrics.items():
            report.append(f"| {operation} | {data['call_count']} | {data['avg_time']:.4f} | "
                         f"{data['max_time']:.4f} | {data['avg_memory']:.2f} | {data['errors']} |")
    else:
        report.append("No profiling data available.")
    
    report.append("")
    
    # Add optimization statistics
    report.append("## Data Optimization Results")
    report.append("")
    
    if "optimization_stats.json" in [f.name for f in output_dir.iterdir() if f.is_file()]:
        try:
            with open(output_dir / "optimization_stats.json", 'r') as f:
                opt_stats = json.load(f)
            
            report.append("| Table | Original (MB) | Optimized (MB) | Savings (MB) | Savings (%) | Time (s) |")
            report.append("|-------|---------------|----------------|--------------|-------------|----------|")
            
            total_original = 0
            total_optimized = 0
            total_time = 0
            
            for stat in opt_stats:
                report.append(f"| {stat['table']} | {stat['original_memory_mb']:.2f} | "
                             f"{stat['optimized_memory_mb']:.2f} | {stat['savings_mb']:.2f} | "
                             f"{stat['savings_percent']:.1f} | {stat['processing_time_seconds']:.3f} |")
                total_original += stat['original_memory_mb']
                total_optimized += stat['optimized_memory_mb']
                total_time += stat['processing_time_seconds']
            
            total_savings = total_original - total_optimized
            total_savings_percent = (total_savings / total_original) * 100 if total_original > 0 else 0
            
            report.append("| **TOTAL** | **{:.2f}** | **{:.2f}** | **{:.2f}** | **{:.1f}** | **{:.3f}** |".format(
                total_original, total_optimized, total_savings, total_savings_percent, total_time))
        except Exception as e:
            report.append(f"Error loading optimization statistics: {e}")
    else:
        report.append("No optimization statistics available.")
    
    report.append("")
    
    # Save report
    report_file = output_dir / "performance_report.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report))
    
    print(f"Performance report saved to {report_file}")


def main():
    """Main function to profile and optimize performance."""
    parser = argparse.ArgumentParser(description="Profile and optimize microcosting analysis performance")
    parser.add_argument("--data-dir", help="Path to prepared data directory")
    parser.add_argument("--output-dir", help="Path to output directory for results")
    parser.add_argument("--optimize-data", action="store_true", help="Optimize DataFrames for memory usage")
    parser.add_argument("--benchmark-parallel", action="store_true", help="Benchmark parallel processing")
    parser.add_argument("--test-cache", action="store_true", help="Test caching performance")
    
    args = parser.parse_args()
    
    print("Performance Profiling and Optimization")
    print("=" * 50)
    
    try:
        # Set up directories
        if args.data_dir:
            data_dir = Path(args.data_dir)
        else:
            data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path(__file__).resolve().parents[1] / "reports" / "performance"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create performance profiler
        profiler = PerformanceProfiler()
        
        # Profile data loading
        data_results = profile_data_loading(profiler, data_dir)
        if data_results["status"] != "success":
            print("Failed to load data, cannot continue with performance analysis")
            return 1
        
        data_dict = data_results["data"]
        
        # Profile calculation engine
        engine_results = profile_calculation_engine(profiler, data_dict)
        
        # Optimize DataFrames if requested
        if args.optimize_data:
            optimized_data = optimize_dataframes(data_dict, output_dir)
        else:
            optimized_data = None
        
        # Benchmark parallel processing if requested
        parallel_results = None
        if args.benchmark_parallel:
            parallel_results = benchmark_parallel_processing(data_dict, profiler)
            print(f"Parallel processing results: {parallel_results}")
        
        # Test caching performance if requested
        cache_results = None
        if args.test_cache:
            cache_results = test_caching_performance(data_dict, profiler)
            print(f"Caching test results: {cache_results}")
        
        # Generate performance report
        generate_performance_report(profiler, {"optimization_stats": []}, output_dir)
        
        # Print performance summary
        print("\nPerformance Profiling Summary:")
        print("-" * 30)
        profiler.print_report()
        
        print("\nPerformance analysis complete!")
        print(f"Results saved to {output_dir}")
        
        # List generated files
        print("\nGenerated files:")
        for item in output_dir.iterdir():
            if item.is_file():
                print(f"  {item.name}")
        
    except Exception as e:
        print(f"Error during performance profiling: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())