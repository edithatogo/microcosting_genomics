# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Memory usage monitoring tools for genomics microcosting analysis.

This module provides tools to monitor and analyze memory usage during
native Polars DataFrame operations in the genomics microcosting framework.
"""

import logging
import time
import tracemalloc
import unittest
from typing import TypedDict

import numpy as np
import polars as pl
import psutil

from genomics_microcosting.performance import DataOptimizer
from tests.checks import require_equal, require_runtime_instance

logger = logging.getLogger(__name__)


class MemorySnapshot(TypedDict):
    """One Python-allocation observation, not a native RSS peak."""

    label: str
    snapshot: tracemalloc.Snapshot
    timestamp: float


class MemoryAnalysis(TypedDict):
    """Estimated Polars buffers in MiB, separate from process resident memory."""

    total_memory_mb: float
    column_memory_mb: dict[str, float]
    data_types: dict[str, str]
    shape: tuple[int, int]


class ResourceDelta(TypedDict):
    """Two resident-memory snapshots and resulting native table dimensions."""

    memory_before_mb: float
    memory_after_mb: float
    memory_increase_mb: float
    result_shape: tuple[int, int]


class MergeResult(ResourceDelta):
    """Native joined rows and observed callback time."""

    merged_dataframe: pl.DataFrame
    merge_time: float


class GroupResult(ResourceDelta):
    """Flat named aggregates with the group key retained as a column."""

    aggregated_dataframe: pl.DataFrame
    groupby_time: float


class PivotResult(ResourceDelta):
    """Native pivot values and observed callback time."""

    pivoted_dataframe: pl.DataFrame
    pivot_time: float


class OptimizedMemory(TypedDict):
    """Measured optimization and estimated buffer changes."""

    analysis: MemoryAnalysis
    optimization_time: float
    memory_savings_mb: float
    memory_savings_percentage: float


class ChunkedMemory(TypedDict):
    """Estimated native buffers after chunk processing."""

    analysis: MemoryAnalysis
    chunking_time: float


class MemoryBenchmark(TypedDict):
    """Separate baseline, optimization and chunking observations."""

    baseline: MemoryAnalysis
    optimized: OptimizedMemory
    chunked: ChunkedMemory


class MemoryMonitor:
    """Memory monitoring tool for native Polars DataFrame operations."""

    def __init__(self) -> None:
        """Initialize the memory monitor."""
        self.snapshots: list[MemorySnapshot] = []
        self.monitoring_enabled = False

    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        tracemalloc.start()
        self.monitoring_enabled = True
        self.take_snapshot("start")

    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.take_snapshot("end")
        tracemalloc.stop()
        self.monitoring_enabled = False

    def take_snapshot(self, label: str = "") -> None:
        """Take a memory snapshot.

        Args:
            label (str): Label for the snapshot

        """
        if not self.monitoring_enabled:
            return

        snapshot = tracemalloc.take_snapshot()
        timestamp = time.time()
        self.snapshots.append(
            {
                "label": label,
                "snapshot": snapshot,
                "timestamp": timestamp,
            },
        )

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB.

        Returns:
            float: Current memory usage in MB

        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def analyze_dataframe_memory(self, df: pl.DataFrame) -> MemoryAnalysis:
        """Analyze memory usage of a DataFrame.

        Args:
            df (pl.DataFrame): DataFrame to analyze

        Returns:
            Dict[str, float]: Memory usage analysis

        """
        # Get memory usage for entire DataFrame
        total_memory = df.estimated_size("b") / 1024 / 1024  # MB

        # Get memory usage by column
        column_memory: dict[str, float] = {}
        for col in df.columns:
            column_memory[col] = df[col].estimated_size("b") / 1024 / 1024  # MB

        # Get data types
        dtypes: dict[str, str] = {}
        for col in df.columns:
            dtypes[col] = str(df[col].dtype)

        return {
            "total_memory_mb": total_memory,
            "column_memory_mb": column_memory,
            "data_types": dtypes,
            "shape": df.shape,
        }

    def compare_memory_usage(
        self,
        before_df: pl.DataFrame,
        after_df: pl.DataFrame,
    ) -> dict[str, float]:
        """Compare memory usage between two DataFrames.

        Args:
            before_df (pl.DataFrame): DataFrame before operation
            after_df (pl.DataFrame): DataFrame after operation

        Returns:
            Dict[str, float]: Memory usage comparison

        """
        before_usage = self.analyze_dataframe_memory(before_df)
        after_usage = self.analyze_dataframe_memory(after_df)

        return {
            "before_total_mb": before_usage["total_memory_mb"],
            "after_total_mb": after_usage["total_memory_mb"],
            "memory_savings_mb": before_usage["total_memory_mb"]
            - after_usage["total_memory_mb"],
            "memory_savings_percentage": (
                (before_usage["total_memory_mb"] - after_usage["total_memory_mb"])
                / before_usage["total_memory_mb"]
                * 100
            )
            if before_usage["total_memory_mb"] > 0
            else 0,
        }

    def get_top_memory_consumers(
        self,
        df: pl.DataFrame,
        top_n: int = 10,
    ) -> list[tuple[str, float]]:
        """Get top memory consuming columns.

        Args:
            df (pl.DataFrame): DataFrame to analyze
            top_n (int): Number of top consumers to return

        Returns:
            List[Tuple[str, float]]: List of (column, memory_mb) tuples

        """
        column_memory = self.analyze_dataframe_memory(df)["column_memory_mb"]
        sorted_columns = sorted(column_memory.items(), key=lambda x: x[1], reverse=True)
        return sorted_columns[:top_n]

    def generate_memory_report(self, df: pl.DataFrame) -> str:
        """Generate a formatted memory usage report.

        Args:
            df (pl.DataFrame): DataFrame to analyze

        Returns:
            str: Formatted memory report

        """
        analysis = self.analyze_dataframe_memory(df)
        top_consumers = self.get_top_memory_consumers(df, 5)

        report: list[str] = []
        report.append("Memory Usage Report")
        report.append("=" * 50)
        report.append(
            "DataFrame Shape: "
            f"{analysis['shape'][0]}"
            " rows x "
            f"{analysis['shape'][1]}"
            " columns",
        )
        report.append(f"Total Memory Usage: {analysis['total_memory_mb']:.2f} MB")
        report.append("")
        report.append("Top Memory Consumers:")
        for col, memory_mb in top_consumers:
            dtype = analysis["data_types"].get(col, "unknown")
            report.append(f"  {col} ({dtype}): {memory_mb:.2f} MB")

        return "\n".join(report)


class DataFrameMemoryTester:
    """Test memory usage of various DataFrame operations."""

    def __init__(self) -> None:
        """Initialize the tester."""
        self.monitor = MemoryMonitor()
        self.optimizer = DataOptimizer()

    def test_merge_operations(
        self,
        df1: pl.DataFrame,
        df2: pl.DataFrame,
        merge_key: str,
    ) -> MergeResult:
        """Test memory usage of DataFrame merge operations.

        Args:
            df1 (pl.DataFrame): First DataFrame
            df2 (pl.DataFrame): Second DataFrame
            merge_key (str): Key column for merging

        Returns:
            Dict[str, any]: Test results

        """
        self.monitor.start_monitoring()

        # Measure memory before merge
        memory_before = self.monitor.get_memory_usage()

        # Perform merge
        start_time = time.time()
        overlap = (set(df1.columns) & set(df2.columns)) - {merge_key}
        left = df1.rename({column: f"{column}_x" for column in overlap})
        right = df2.rename({column: f"{column}_y" for column in overlap})
        merged_df = left.join(
            right,
            on=merge_key,
            how="inner",
            maintain_order="left",
            nulls_equal=True,
        )
        merge_time = time.time() - start_time

        # Measure memory after merge
        memory_after = self.monitor.get_memory_usage()

        self.monitor.stop_monitoring()

        return {
            "merged_dataframe": merged_df,
            "merge_time": merge_time,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_increase_mb": memory_after - memory_before,
            "result_shape": merged_df.shape,
        }

    def test_groupby_operations(
        self,
        df: pl.DataFrame,
        group_column: str,
    ) -> GroupResult:
        """Test memory usage of DataFrame groupby operations.

        Args:
            df (pl.DataFrame): DataFrame to group
            group_column (str): Column to group by

        Returns:
            Dict[str, any]: Test results

        """
        self.monitor.start_monitoring()

        # Measure memory before groupby
        memory_before = self.monitor.get_memory_usage()

        # Perform groupby
        start_time = time.time()
        groups = df.filter(pl.col(group_column).is_not_null())
        if df.schema[group_column].is_float():
            groups = groups.filter(pl.col(group_column).is_not_nan())
        groups = groups.with_columns(pl.selectors.float().fill_nan(None))
        aggregated = (
            groups.group_by(group_column)
            .agg(
                pl.col("Total_Cost").sum().alias("Total_Cost_sum"),
                pl.col("Total_Cost").mean().alias("Total_Cost_mean"),
                pl.col("Total_Cost").count().alias("Total_Cost_count"),
                pl.col("Quantity").sum().alias("Quantity_sum"),
                pl.col("Quantity").mean().alias("Quantity_mean"),
            )
            .sort(group_column)
        )
        groupby_time = time.time() - start_time

        # Measure memory after groupby
        memory_after = self.monitor.get_memory_usage()

        self.monitor.stop_monitoring()

        return {
            "aggregated_dataframe": aggregated,
            "groupby_time": groupby_time,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_increase_mb": memory_after - memory_before,
            "result_shape": aggregated.shape,
        }

    def test_pivot_operations(
        self,
        df: pl.DataFrame,
        index: str,
        columns: str,
        values: str,
    ) -> PivotResult:
        """Test memory usage of DataFrame pivot operations.

        Args:
            df (pl.DataFrame): DataFrame to pivot
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
        pivoted_df = df.pivot(
            on=columns,
            index=index,
            values=values,
            aggregate_function="sum",
            sort_columns=True,
            maintain_order=True,
        ).sort(index)
        pivot_time = time.time() - start_time

        # Measure memory after pivot
        memory_after = self.monitor.get_memory_usage()

        self.monitor.stop_monitoring()

        return {
            "pivoted_dataframe": pivoted_df,
            "pivot_time": pivot_time,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after,
            "memory_increase_mb": memory_after - memory_before,
            "result_shape": pivoted_df.shape,
        }


class TestMemoryMonitoring(unittest.TestCase):
    """Memory monitoring tests."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.monitor = MemoryMonitor()
        self.tester = DataFrameMemoryTester()

    def generate_test_data(self, size: int) -> pl.DataFrame:
        """Generate test data for memory testing.

        Args:
            size (int): Number of rows to generate

        Returns:
            pl.DataFrame: Generated test data

        """
        rng = np.random.default_rng(42)

        test_types = ["Panel", "WES (P)", "WES (T)", "WGS"]
        categories = ["Labour", "Equipment", "Consumables", "Compute", "Storage"]

        data = {
            "Test": rng.choice(test_types, size),
            "Category": rng.choice(categories, size),
            "Quantity": rng.uniform(0.5, 5.0, size),
            "Unit_Cost": rng.uniform(50.0, 200.0, size),
            "Year": rng.choice([2023, 2024, 2025], size),
        }

        # Calculate total cost
        data["Total_Cost"] = np.array(data["Quantity"]) * np.array(data["Unit_Cost"])

        return pl.DataFrame(data)

    def test_memory_monitoring_basic(self) -> None:
        """Test basic memory monitoring functionality."""
        # Test memory usage measurement
        memory_usage = self.monitor.get_memory_usage()
        require_runtime_instance(memory_usage, float)
        if not ((memory_usage) >= (0)):
            raise AssertionError

        # Test monitoring start/stop
        if self.monitor.monitoring_enabled:
            raise AssertionError
        self.monitor.start_monitoring()
        if not (self.monitor.monitoring_enabled):
            raise AssertionError
        self.monitor.stop_monitoring()
        if self.monitor.monitoring_enabled:
            raise AssertionError

    def test_dataframe_memory_analysis(self) -> None:
        """Test DataFrame memory analysis."""
        # Create test DataFrame
        df = self.generate_test_data(1000)

        # Analyze memory usage
        analysis = self.monitor.analyze_dataframe_memory(df)

        # Check analysis results
        if ("total_memory_mb") not in (analysis):
            raise AssertionError
        if ("column_memory_mb") not in (analysis):
            raise AssertionError
        if ("data_types") not in (analysis):
            raise AssertionError
        if ("shape") not in (analysis):
            raise AssertionError

        require_runtime_instance(analysis["total_memory_mb"], float)
        if not ((analysis["total_memory_mb"]) > (0)):
            raise AssertionError
        if not ((analysis["shape"]) == ((1000, 6))):
            raise AssertionError

        # Check column memory analysis
        column_memory = analysis["column_memory_mb"]
        require_runtime_instance(column_memory, dict)
        if ("Test") not in (column_memory):
            raise AssertionError
        if ("Category") not in (column_memory):
            raise AssertionError
        if ("Total_Cost") not in (column_memory):
            raise AssertionError

    def test_memory_comparison(self) -> None:
        """Test memory usage comparison."""
        # Create test DataFrames
        df1 = self.generate_test_data(1000)
        df2 = self.generate_test_data(500)  # Smaller DataFrame

        # Compare memory usage
        comparison = self.monitor.compare_memory_usage(df1, df2)

        if ("before_total_mb") not in (comparison):
            raise AssertionError
        if ("after_total_mb") not in (comparison):
            raise AssertionError
        if ("memory_savings_mb") not in (comparison):
            raise AssertionError
        if ("memory_savings_percentage") not in (comparison):
            raise AssertionError

        # df1 should be larger than df2
        if not ((comparison["before_total_mb"]) > (comparison["after_total_mb"])):
            raise AssertionError

    def test_top_memory_consumers(self) -> None:
        """Test identification of top memory consumers."""
        maximum_consumers = 3
        # Create test DataFrame
        df = self.generate_test_data(10000)

        # Get top consumers
        top_consumers = self.monitor.get_top_memory_consumers(df, 3)

        require_runtime_instance(top_consumers, list)
        if not ((len(top_consumers)) <= (maximum_consumers)):
            raise AssertionError

        # Each item should be a tuple of (column, memory_mb)
        for item in top_consumers:
            require_runtime_instance(item, tuple)
            require_equal(len(item), 2)
            require_runtime_instance(item[0], str)  # column name
            require_runtime_instance(item[1], float)  # memory in MB

    def test_merge_operation_memory(self) -> None:
        """Test memory usage of merge operations."""
        # Create test DataFrames
        rng = np.random.default_rng(42)
        df1 = self.generate_test_data(1000)
        df2 = self.generate_test_data(500)

        # Add a common key column for merging
        df1 = df1.with_columns(
            pl.Series("Merge_Key", rng.integers(1, 100, len(df1))),
        )
        df2 = df2.with_columns(
            pl.Series("Merge_Key", rng.integers(1, 100, len(df2))),
        )

        # Test merge operation
        result = self.tester.test_merge_operations(df1, df2, "Merge_Key")

        if ("merged_dataframe") not in (result):
            raise AssertionError
        if ("merge_time") not in (result):
            raise AssertionError
        if ("memory_increase_mb") not in (result):
            raise AssertionError
        if ("result_shape") not in (result):
            raise AssertionError

        require_runtime_instance(result["merged_dataframe"], pl.DataFrame)
        if not ((result["merge_time"]) >= (0)):
            raise AssertionError
        require_runtime_instance(result["result_shape"], tuple)

    def test_groupby_operation_memory(self) -> None:
        """Test memory usage of groupby operations."""
        # Create test DataFrame
        df = self.generate_test_data(5000)

        # Test groupby operation
        result = self.tester.test_groupby_operations(df, "Category")

        if ("aggregated_dataframe") not in (result):
            raise AssertionError
        if ("groupby_time") not in (result):
            raise AssertionError
        if ("result_shape") not in (result):
            raise AssertionError

        require_runtime_instance(result["aggregated_dataframe"], pl.DataFrame)
        if not ((result["groupby_time"]) >= (0)):
            raise AssertionError
        require_runtime_instance(result["result_shape"], tuple)

    def test_memory_report_generation(self) -> None:
        """Test memory report generation."""
        # Create test DataFrame
        df = self.generate_test_data(1000)

        # Generate report
        report = self.monitor.generate_memory_report(df)

        require_runtime_instance(report, str)
        if ("Memory Usage Report") not in (report):
            raise AssertionError
        if ("Total Memory Usage") not in (report):
            raise AssertionError
        if ("Top Memory Consumers") not in (report):
            raise AssertionError


class MemoryOptimizationBenchmark:
    """Benchmark memory optimization techniques."""

    def __init__(self) -> None:
        """Initialize the benchmark."""
        self.monitor = MemoryMonitor()
        self.optimizer = DataOptimizer()

    def benchmark_optimization_techniques(self, df: pl.DataFrame) -> MemoryBenchmark:
        """Benchmark different memory optimization techniques.

        Args:
            df (pl.DataFrame): DataFrame to optimize

        Returns:
            Dict[str, any]: Benchmark results

        """
        # Baseline memory usage
        baseline_analysis = self.monitor.analyze_dataframe_memory(df)

        # Test DataFrame optimization
        start_time = time.time()
        optimized_df = self.optimizer.optimize_dataframe(df.clone())
        optimization_time = time.time() - start_time

        optimized_analysis = self.monitor.analyze_dataframe_memory(optimized_df)

        optimized: OptimizedMemory = {
            "analysis": optimized_analysis,
            "optimization_time": optimization_time,
            "memory_savings_mb": baseline_analysis["total_memory_mb"]
            - optimized_analysis["total_memory_mb"],
            "memory_savings_percentage": (
                (
                    baseline_analysis["total_memory_mb"]
                    - optimized_analysis["total_memory_mb"]
                )
                / baseline_analysis["total_memory_mb"]
                * 100
            )
            if baseline_analysis["total_memory_mb"] > 0
            else 0,
        }

        # Test chunked processing
        start_time = time.time()
        chunked_df = self.optimizer.chunked_processing(df.clone(), chunk_size=1000)
        chunking_time = time.time() - start_time

        chunked_analysis = self.monitor.analyze_dataframe_memory(chunked_df)

        chunked: ChunkedMemory = {
            "analysis": chunked_analysis,
            "chunking_time": chunking_time,
        }

        return {
            "baseline": baseline_analysis,
            "optimized": optimized,
            "chunked": chunked,
        }


# Example usage:
if __name__ == "__main__":
    # Create memory monitor
    monitor = MemoryMonitor()

    # Generate test data
    rng = np.random.default_rng(42)
    test_data = pl.DataFrame(
        {
            "Category": rng.choice(["Labour", "Equipment", "Consumables"], 10000),
            "Sub_Category": rng.choice(
                ["Sequencing", "Library Prep", "DNA Extraction"],
                10000,
            ),
            "Quantity": rng.uniform(0.5, 5.0, 10000),
            "Unit_Cost": rng.uniform(50.0, 200.0, 10000),
            "Description": ["Test description " + str(i) for i in range(10000)],
        },
    )

    # Calculate total cost
    test_data["Total_Cost"] = test_data["Quantity"] * test_data["Unit_Cost"]

    # Analyze memory usage
    logger.info("%s", "Analyzing DataFrame memory usage...")
    analysis = monitor.analyze_dataframe_memory(test_data)
    logger.info("%s", f"Total memory usage: {analysis['total_memory_mb']:.2f} MB")
    logger.info("%s", f"DataFrame shape: {analysis['shape']}")

    # Show top memory consumers
    logger.info("%s", "\nTop memory consumers:")
    top_consumers = monitor.get_top_memory_consumers(test_data, 5)
    for col, memory_mb in top_consumers:
        dtype = analysis["data_types"].get(col, "unknown")
        logger.info("%s", f"  {col} ({dtype}): {memory_mb:.2f} MB")

    # Generate full report
    logger.info("%s", "\n" + monitor.generate_memory_report(test_data))
