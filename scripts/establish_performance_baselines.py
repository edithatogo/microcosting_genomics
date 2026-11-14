# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to establish performance baseline metrics for genomics microcosting analysis.

This script runs comprehensive performance tests to establish baseline metrics
for various operations in the genomics microcosting framework.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from tests.test_load_testing import LoadTestingFramework
from tests.test_memory_monitoring import MemoryMonitor
from tests.test_processing_time import ProcessingTimeMeasurer
from tests.test_scalability import ScalabilityTester

logger = logging.getLogger(__name__)

REGRESSION_PERCENT = 5
SCALING_REGRESSION_PERCENT = 10


def establish_performance_baselines() -> dict[str, object]:
    """Establish performance baselines for all major operations."""
    sys.stdout.write("Establishing performance baselines..." + "\n")
    sys.stdout.write(str("=" * 50) + "\n")

    # Initialize testing frameworks
    load_tester = LoadTestingFramework()
    memory_monitor = MemoryMonitor()
    time_measurer = ProcessingTimeMeasurer()
    scalability_tester = ScalabilityTester()

    baselines = {
        "timestamp": datetime.now(UTC).astimezone().isoformat(),
        "load_testing": {},
        "memory_usage": {},
        "processing_time": {},
        "scalability": {},
    }

    # 1. Load Testing Baselines
    sys.stdout.write("\n1. Running load testing baselines..." + "\n")

    def sample_operation(df: pd.DataFrame) -> float | int:
        return df["Total_Cost"].sum() if "Total_Cost" in df.columns else len(df)

    load_sizes = [1000, 5000, 10000]
    load_results = load_tester.run_scalability_test(
        sizes=load_sizes,
        operation_name="baseline_load_test",
        test_function=sample_operation,
    )

    baselines["load_testing"] = {
        "test_sizes": load_sizes,
        "results": load_results,
    }

    # 2. Memory Usage Baselines
    sys.stdout.write("\n2. Running memory usage baselines..." + "\n")
    test_data = load_tester.generate_test_data(10000)
    memory_analysis = memory_monitor.analyze_dataframe_memory(test_data)

    baselines["memory_usage"] = {
        "test_data_size": len(test_data),
        "total_memory_mb": memory_analysis["total_memory_mb"],
        "column_memory_mb": memory_analysis["column_memory_mb"],
    }

    # 3. Processing Time Baselines
    sys.stdout.write("\n3. Running processing time baselines..." + "\n")

    def processing_test() -> float:
        # Simulate some processing work
        data = list(range(10000))
        return sum(x * 1.5 for x in data)

    time_stats = time_measurer.measure_multiple_executions(
        "baseline_processing",
        processing_test,
        iterations=5,
    )

    baselines["processing_time"] = {
        "iterations": time_stats["iterations"],
        "successful_executions": time_stats["successful_executions"],
        "wall_time_mean": time_stats["wall_time_stats"]["mean"],
        "wall_time_stdev": time_stats["wall_time_stats"]["stdev"],
        "cpu_time_mean": time_stats["cpu_time_stats"]["mean"],
    }

    # 4. Scalability Baselines
    sys.stdout.write("\n4. Running scalability baselines..." + "\n")

    def simple_scalability_test(test_data: dict[str, pd.DataFrame]) -> int:
        # Simple operation for scalability testing
        df = test_data.get("Detailed Table", pd.DataFrame())
        return len(df)

    scalability_sizes = [1000, 5000, 10000]
    scalability_results = scalability_tester.run_scalability_test(
        operation_name="baseline_scalability",
        test_function=simple_scalability_test,
        sizes=scalability_sizes,
        complexity="basic",
        iterations=3,
    )

    scalability_analysis = scalability_tester.analyze_scaling_behavior(
        scalability_results,
    )

    baselines["scalability"] = {
        "test_sizes": scalability_sizes,
        "results": scalability_results,
        "analysis": scalability_analysis,
    }

    return baselines


def save_baselines(baselines: dict, output_file: str | None = None) -> str:
    """Save baselines to a JSON file.

    Args:
        baselines (dict): Baselines data to save
        output_file (str): Output file path (default: auto-generated)

    """
    if output_file is None:
        timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")

        output_file = f"performance_baselines_{timestamp}.json"

    # Convert numpy types to native Python types for JSON serialization
    def convert_numpy_types(obj: object) -> object:
        if isinstance(obj, np.integer | np.floating):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        return obj

    baselines_converted = convert_numpy_types(baselines)

    with Path(output_file).open("w") as f:
        json.dump(baselines_converted, f, indent=2)

    sys.stdout.write(f"\nBaselines saved to: {output_file}" + "\n")
    return output_file


def print_baseline_summary(baselines: dict) -> None:
    """Print a summary of the established baselines.

    Args:
        baselines (dict): Baselines data to summarize

    """
    sys.stdout.write(str("\n" + "=" * 60) + "\n")
    sys.stdout.write("PERFORMANCE BASELINES SUMMARY" + "\n")
    sys.stdout.write(str("=" * 60) + "\n")

    # Load Testing Summary
    load_results = baselines.get("load_testing", {}).get("results", [])
    if load_results:
        sys.stdout.write("\nLoad Testing:" + "\n")
        sys.stdout.write(
            " ".join(
                ("  Data Sizes Tested:", str(baselines["load_testing"]["test_sizes"])),
            )
            + "\n",
        )
        for result in load_results:
            sys.stdout.write(
                f"    {result['data_size']} rows: {result['execution_time']:.4f}s, "
                f"{result['memory_used']:.2f}MB" + "\n",
            )

    # Memory Usage Summary
    memory_data = baselines.get("memory_usage", {})
    if memory_data:
        sys.stdout.write("\nMemory Usage:" + "\n")
        sys.stdout.write(
            f"  Test Data Size: {memory_data.get('test_data_size', 0)} rows" + "\n",
        )
        sys.stdout.write(
            f"  Total Memory: {memory_data.get('total_memory_mb', 0):.2f} MB" + "\n",
        )
        sys.stdout.write("  Top Memory Consumers:" + "\n")
        column_memory = memory_data.get("column_memory_mb", {})
        top_consumers = sorted(column_memory.items(), key=lambda x: x[1], reverse=True)[
            :3
        ]
        for col, mem in top_consumers:
            sys.stdout.write(f"    {col}: {mem:.2f} MB" + "\n")

    # Processing Time Summary
    time_data = baselines.get("processing_time", {})
    if time_data:
        sys.stdout.write("\nProcessing Time:" + "\n")
        sys.stdout.write(f"  Iterations: {time_data.get('iterations', 0)}" + "\n")
        sys.stdout.write(
            "  Success Rate: "
            f"{time_data.get('successful_executions', 0)}"
            "/"
            f"{time_data.get('iterations', 0)}"
            "\n",
        )
        sys.stdout.write(
            f"  Mean Wall Time: {time_data.get('wall_time_mean', 0):.4f}s "
            f"(±{time_data.get('wall_time_stdev', 0):.4f})" + "\n",
        )
        sys.stdout.write(
            f"  Mean CPU Time: {time_data.get('cpu_time_mean', 0):.4f}s" + "\n",
        )

    # Scalability Summary
    scalability_data = baselines.get("scalability", {})
    if scalability_data:
        analysis = scalability_data.get("analysis", {})
        sys.stdout.write("\nScalability:" + "\n")
        sys.stdout.write(
            f"  Test Sizes: {scalability_data.get('test_sizes', [])}" + "\n",
        )
        sys.stdout.write(
            f"  Scaling Behavior: {analysis.get('scaling_behavior', 'unknown')}" + "\n",
        )
        sys.stdout.write(
            f"  Average Scaling Factor: {analysis.get('average_scaling_factor', 0):.2f}"
            "\n",
        )


def load_baselines(input_file: str) -> dict:
    """Load baselines from a JSON file.

    Args:
        input_file (str): Input file path

    Returns:
        dict: Loaded baselines data

    """
    with Path(input_file).open() as f:
        baselines = json.load(f)

    sys.stdout.write(f"Baselines loaded from: {input_file}" + "\n")
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
    current_time = current_baselines.get("processing_time", {}).get("wall_time_mean", 0)
    reference_time = reference_baselines.get("processing_time", {}).get(
        "wall_time_mean",
        0,
    )

    if current_time > 0 and reference_time > 0:
        time_change = ((current_time - reference_time) / reference_time) * 100
        comparison["processing_time"] = {
            "current": current_time,
            "reference": reference_time,
            "change_percentage": time_change,
            "performance_regression": time_change > REGRESSION_PERCENT,  # 5% threshold
        }

    # Compare memory usage
    current_memory = current_baselines.get("memory_usage", {}).get("total_memory_mb", 0)
    reference_memory = reference_baselines.get("memory_usage", {}).get(
        "total_memory_mb",
        0,
    )

    if current_memory > 0 and reference_memory > 0:
        memory_change = ((current_memory - reference_memory) / reference_memory) * 100
        comparison["memory_usage"] = {
            "current": current_memory,
            "reference": reference_memory,
            "change_percentage": memory_change,
            "memory_regression": memory_change > REGRESSION_PERCENT,  # 5% threshold
        }

    # Compare scalability
    current_scaling = (
        current_baselines.get("scalability", {})
        .get("analysis", {})
        .get("average_scaling_factor", 0)
    )
    reference_scaling = (
        reference_baselines.get("scalability", {})
        .get("analysis", {})
        .get("average_scaling_factor", 0)
    )

    if current_scaling > 0 and reference_scaling > 0:
        scaling_change = (
            (current_scaling - reference_scaling) / reference_scaling
        ) * 100
        comparison["scalability"] = {
            "current": current_scaling,
            "reference": reference_scaling,
            "change_percentage": scaling_change,
            "scaling_regression": scaling_change
            > SCALING_REGRESSION_PERCENT,  # 10% threshold
        }

    return comparison


def main() -> None:
    """Establish and save performance baselines."""
    try:
        # Establish baselines
        baselines = establish_performance_baselines()

        # Print summary
        print_baseline_summary(baselines)

        # Save baselines
        output_file = save_baselines(baselines)

        sys.stdout.write(
            "\nPerformance baselines successfully established and saved to "
            f"{output_file}"
            "\n",
        )

        # Example of how to use baselines for comparison
        sys.stdout.write(
            "\nTo compare future performance against these baselines, use:" + "\n",
        )
        sys.stdout.write(f"  python compare_performance.py {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete establish performance baselines")
        sys.stdout.write(f"Error establishing performance baselines: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
