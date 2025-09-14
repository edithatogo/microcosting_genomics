"""Script to compare current performance against established baselines.

This script runs performance tests and compares results against previously
established baselines to detect performance regressions.
"""

import sys
import argparse
from pathlib import Path
import json
from datetime import datetime

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from scripts.establish_performance_baselines import (  # noqa: E402
    establish_performance_baselines, 
    load_baselines, 
    compare_baselines,
    print_baseline_summary
)


def run_performance_comparison(baseline_file: str = None):
    """Run performance comparison against baselines.
    
    Args:
        baseline_file (str): Path to baseline file (if None, establish new baselines)
        
    Returns:
        dict: Comparison results
    """
    print("Running performance comparison...")
    print("=" * 50)
    
    # Establish current performance
    print("\nEstablishing current performance metrics...")
    current_baselines = establish_performance_baselines()
    
    if baseline_file:
        # Load reference baselines
        print(f"\nLoading reference baselines from {baseline_file}...")
        try:
            reference_baselines = load_baselines(baseline_file)
        except Exception as e:
            print(f"Error loading reference baselines: {e}")
            return None
    else:
        # Use current baselines as reference (first run)
        print("\nNo reference baselines provided. Using current run as baseline.")
        reference_baselines = current_baselines
        # Save as reference for future comparisons
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        baseline_file = f"performance_baselines_{timestamp}.json"
        with open(baseline_file, 'w') as f:
            json.dump(current_baselines, f, indent=2)
        print(f"Baseline saved as reference: {baseline_file}")
    
    # Compare performance
    print("\nComparing performance...")
    comparison = compare_baselines(current_baselines, reference_baselines)
    
    return {
        'current_baselines': current_baselines,
        'reference_baselines': reference_baselines,
        'comparison': comparison
    }


def print_comparison_results(results: dict):
    """Print formatted comparison results.
    
    Args:
        results (dict): Comparison results
    """
    if not results:
        print("No comparison results to display.")
        return
    
    comparison = results.get('comparison', {})
    if not comparison:
        print("No performance metrics to compare.")
        return
    
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON RESULTS")
    print("=" * 60)
    
    regressions_found = False
    
    # Processing Time Comparison
    time_comparison = comparison.get('processing_time', {})
    if time_comparison:
        print("\nProcessing Time:")
        print(f"  Current:  {time_comparison['current']:.4f}s")
        print(f"  Reference: {time_comparison['reference']:.4f}s")
        print(f"  Change:   {time_comparison['change_percentage']:+.2f}%")
        
        if time_comparison.get('performance_regression', False):
            print("  ⚠️  PERFORMANCE REGRESSION DETECTED")
            regressions_found = True
        else:
            print("  ✅ Performance within acceptable range")
    
    # Memory Usage Comparison
    memory_comparison = comparison.get('memory_usage', {})
    if memory_comparison:
        print("\nMemory Usage:")
        print(f"  Current:  {memory_comparison['current']:.2f} MB")
        print(f"  Reference: {memory_comparison['reference']:.2f} MB")
        print(f"  Change:   {memory_comparison['change_percentage']:+.2f}%")
        
        if memory_comparison.get('memory_regression', False):
            print("  ⚠️  MEMORY REGRESSION DETECTED")
            regressions_found = True
        else:
            print("  ✅ Memory usage within acceptable range")
    
    # Scalability Comparison
    scaling_comparison = comparison.get('scalability', {})
    if scaling_comparison:
        print("\nScalability:")
        print(f"  Current Scaling Factor:  {scaling_comparison['current']:.2f}")
        print(f"  Reference Scaling Factor: {scaling_comparison['reference']:.2f}")
        print(f"  Change:                  {scaling_comparison['change_percentage']:+.2f}%")
        
        if scaling_comparison.get('scaling_regression', False):
            print("  ⚠️  SCALABILITY REGRESSION DETECTED")
            regressions_found = True
        else:
            print("  ✅ Scaling behavior within acceptable range")
    
    if regressions_found:
        print("\n🚨 PERFORMANCE REGRESSIONS DETECTED!")
        print("Please investigate the performance issues before proceeding.")
    else:
        print("\n✅ All performance metrics within acceptable ranges.")


def generate_performance_report(results: dict, output_file: str = None):
    """Generate detailed performance report.
    
    Args:
        results (dict): Comparison results
        output_file (str): Output file path (default: auto-generated)
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"performance_comparison_report_{timestamp}.json"
    
    # Add timestamp to results
    results['timestamp'] = datetime.now().isoformat()
    
    # Convert to JSON-serializable format
    def convert_for_json(obj):
        if isinstance(obj, dict):
            return {key: convert_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return obj
    
    results_converted = convert_for_json(results)
    
    with open(output_file, 'w') as f:
        json.dump(results_converted, f, indent=2)
    
    print(f"\nDetailed performance report saved to: {output_file}")
    return output_file


def main():
    """Main function to run performance comparison."""
    parser = argparse.ArgumentParser(description='Compare performance against baselines')
    parser.add_argument('baseline_file', nargs='?', 
                       help='Path to baseline JSON file (optional)')
    parser.add_argument('--output', '-o', 
                       help='Output file for detailed report')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode - only output comparison results')
    
    args = parser.parse_args()
    
    try:
        # Run performance comparison
        results = run_performance_comparison(args.baseline_file)
        
        if not args.quiet:
            # Print current performance summary
            if results and 'current_baselines' in results:
                print("\nCurrent Performance Summary:")
                print("-" * 30)
                print_baseline_summary(results['current_baselines'])
        
        # Print comparison results
        print_comparison_results(results)
        
        # Generate detailed report if requested
        if args.output:
            generate_performance_report(results, args.output)
        
        # Exit with error code if regressions found
        if results and results.get('comparison'):
            regressions = [k for k, v in results['comparison'].items() 
                          if v.get('performance_regression') or 
                             v.get('memory_regression') or 
                             v.get('scaling_regression')]
            if regressions:
                print(f"\nExiting with error due to regressions in: {', '.join(regressions)}")
                sys.exit(1)
        
        print("\nPerformance comparison completed successfully.")
        
    except Exception as e:
        print(f"Error during performance comparison: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()