# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to compare current performance against established baselines.

This script runs performance tests and compares results against previously
established baselines to detect performance regressions.
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.establish_performance_baselines import (
    compare_baselines,
    establish_performance_baselines,
    load_baselines,
    print_baseline_summary,
)

logger = logging.getLogger(__name__)


def run_performance_comparison(
    baseline_file: str | None = None,
) -> dict[str, object] | None:
    """Run performance comparison against baselines.

    Args:
        baseline_file (str): Path to baseline file (if None, establish new baselines)

    Returns:
        dict: Comparison results

    """
    sys.stdout.write("Running performance comparison..." + "\n")
    sys.stdout.write(str("=" * 50) + "\n")

    # Establish current performance
    sys.stdout.write("\nEstablishing current performance metrics..." + "\n")
    current_baselines = establish_performance_baselines()

    if baseline_file:
        # Load reference baselines
        sys.stdout.write(
            f"\nLoading reference baselines from {baseline_file}..." + "\n",
        )
        try:
            reference_baselines = load_baselines(baseline_file)
        except Exception as e:
            logger.exception("Could not complete run performance comparison")
            sys.stdout.write(f"Error loading reference baselines: {e}" + "\n")
            return None
    else:
        # Use current baselines as reference (first run)
        sys.stdout.write(
            "\nNo reference baselines provided. Using current run as baseline." + "\n",
        )
        reference_baselines = current_baselines
        # Save as reference for future comparisons
        timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")

        baseline_file = f"performance_baselines_{timestamp}.json"
        with Path(baseline_file).open("w") as f:
            json.dump(current_baselines, f, indent=2)
        sys.stdout.write(f"Baseline saved as reference: {baseline_file}" + "\n")

    # Compare performance
    sys.stdout.write("\nComparing performance..." + "\n")
    comparison = compare_baselines(current_baselines, reference_baselines)

    return {
        "current_baselines": current_baselines,
        "reference_baselines": reference_baselines,
        "comparison": comparison,
    }


def _print_scalability_comparison(comparison: dict) -> bool:
    regressions_found = False
    # Scalability Comparison
    scaling_comparison = comparison.get("scalability", {})
    if scaling_comparison:
        sys.stdout.write("\nScalability:" + "\n")
        sys.stdout.write(
            f"  Current Scaling Factor:  {scaling_comparison['current']:.2f}" + "\n",
        )
        sys.stdout.write(
            f"  Reference Scaling Factor: {scaling_comparison['reference']:.2f}" + "\n",
        )
        sys.stdout.write(
            "  Change:                  "
            f"{scaling_comparison['change_percentage']:+.2f}%"
            "\n",
        )

        if scaling_comparison.get("scaling_regression", False):
            sys.stdout.write("  ⚠️  SCALABILITY REGRESSION DETECTED" + "\n")
            regressions_found = True
        else:
            sys.stdout.write("  ✅ Scaling behavior within acceptable range" + "\n")

    return regressions_found


def print_comparison_results(results: dict) -> None:
    """Print formatted comparison results.

    Args:
        results (dict): Comparison results

    """
    if not results:
        sys.stdout.write("No comparison results to display." + "\n")
        return

    comparison = results.get("comparison", {})
    if not comparison:
        sys.stdout.write("No performance metrics to compare." + "\n")
        return

    sys.stdout.write(str("\n" + "=" * 60) + "\n")
    sys.stdout.write("PERFORMANCE COMPARISON RESULTS" + "\n")
    sys.stdout.write(str("=" * 60) + "\n")

    regressions_found = False

    # Processing Time Comparison
    time_comparison = comparison.get("processing_time", {})
    if time_comparison:
        sys.stdout.write("\nProcessing Time:" + "\n")
        sys.stdout.write(f"  Current:  {time_comparison['current']:.4f}s" + "\n")
        sys.stdout.write(f"  Reference: {time_comparison['reference']:.4f}s" + "\n")
        sys.stdout.write(
            f"  Change:   {time_comparison['change_percentage']:+.2f}%" + "\n",
        )

        if time_comparison.get("performance_regression", False):
            sys.stdout.write("  ⚠️  PERFORMANCE REGRESSION DETECTED" + "\n")
            regressions_found = True
        else:
            sys.stdout.write("  ✅ Performance within acceptable range" + "\n")

    # Memory Usage Comparison
    memory_comparison = comparison.get("memory_usage", {})
    if memory_comparison:
        sys.stdout.write("\nMemory Usage:" + "\n")
        sys.stdout.write(f"  Current:  {memory_comparison['current']:.2f} MB" + "\n")
        sys.stdout.write(f"  Reference: {memory_comparison['reference']:.2f} MB" + "\n")
        sys.stdout.write(
            f"  Change:   {memory_comparison['change_percentage']:+.2f}%" + "\n",
        )

        if memory_comparison.get("memory_regression", False):
            sys.stdout.write("  ⚠️  MEMORY REGRESSION DETECTED" + "\n")
            regressions_found = True
        else:
            sys.stdout.write("  ✅ Memory usage within acceptable range" + "\n")

    regressions_found = _print_scalability_comparison(comparison) or regressions_found

    if regressions_found:
        sys.stdout.write("\n🚨 PERFORMANCE REGRESSIONS DETECTED!" + "\n")
        sys.stdout.write(
            "Please investigate the performance issues before proceeding." + "\n",
        )
    else:
        sys.stdout.write(
            "\n✅ All performance metrics within acceptable ranges." + "\n",
        )


def generate_performance_report(results: dict, output_file: str | None = None) -> str:
    """Generate detailed performance report.

    Args:
        results (dict): Comparison results
        output_file (str): Output file path (default: auto-generated)

    """
    if output_file is None:
        timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")

        output_file = f"performance_comparison_report_{timestamp}.json"

    # Add timestamp to results
    results["timestamp"] = datetime.now(UTC).astimezone().isoformat()

    # Convert to JSON-serializable format
    def convert_for_json(obj: object) -> object:
        if isinstance(obj, dict):
            return {key: convert_for_json(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        if hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return obj

    results_converted = convert_for_json(results)

    with Path(output_file).open("w") as f:
        json.dump(results_converted, f, indent=2)

    sys.stdout.write(f"\nDetailed performance report saved to: {output_file}" + "\n")
    return output_file


def main() -> None:
    """Run performance comparison."""
    parser = argparse.ArgumentParser(
        description="Compare performance against baselines",
    )
    parser.add_argument(
        "baseline_file",
        nargs="?",
        help="Path to baseline JSON file (optional)",
    )
    parser.add_argument("--output", "-o", help="Output file for detailed report")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode - only output comparison results",
    )

    args = parser.parse_args()

    try:
        # Run performance comparison
        results = run_performance_comparison(args.baseline_file)

        if not args.quiet and results and "current_baselines" in results:
            sys.stdout.write("\nCurrent Performance Summary:\n")
            sys.stdout.write("-" * 30 + "\n")
            print_baseline_summary(results["current_baselines"])

        # Print comparison results
        print_comparison_results(results)

        # Generate detailed report if requested
        if args.output:
            generate_performance_report(results, args.output)

        # Exit with error code if regressions found
        if results and results.get("comparison"):
            regressions = [
                k
                for k, v in results["comparison"].items()
                if v.get("performance_regression")
                or v.get("memory_regression")
                or v.get("scaling_regression")
            ]
            if regressions:
                sys.stdout.write(
                    "\nExiting with error due to regressions in: "
                    f"{', '.join(regressions)}"
                    "\n",
                )
                sys.exit(1)

        sys.stdout.write("\nPerformance comparison completed successfully." + "\n")

    except Exception as e:
        logger.exception("Could not complete compare performance")
        sys.stdout.write(f"Error during performance comparison: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
