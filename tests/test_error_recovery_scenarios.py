# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test error recovery scenarios for genomics microcosting analysis.

This module tests various error recovery scenarios to ensure the system can
gracefully handle and recover from different types of errors.
"""

import logging
import shutil
import tempfile
import unittest
from contextlib import suppress
from pathlib import Path
from typing import TypedDict

import numpy as np
import polars as pl

from genomics_microcosting.error_handling import (
    ErrorContext,
    ErrorSeverity,
    setup_standard_error_handling,
)
from genomics_microcosting.input_validation import InputValidator
from tests.checks import require_equal, require_runtime_instance


class _AnalysisStep(TypedDict):
    step: str
    data: dict[str, object]


class TestErrorRecoveryScenarios(unittest.TestCase):
    """Test error recovery scenarios."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger("test_error_recovery")
        self.logger.setLevel(logging.DEBUG)

        # Create temporary directory for checkpoints
        self.temp_checkpoint_dir = tempfile.mkdtemp()

        # Create error handler with checkpoint directory
        self.error_handler = setup_standard_error_handling(
            logger=self.logger,
            checkpoint_dir=self.temp_checkpoint_dir,
        )

        # Create input validator
        self.validator = InputValidator(self.logger)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Remove temporary checkpoint directory
        with suppress(OSError):
            shutil.rmtree(self.temp_checkpoint_dir)

    def test_missing_data_source_recovery(self) -> None:
        """Test recovery from missing data source errors."""

        # Create a function that might fail due to missing data
        @self.error_handler.graceful_degradation(
            operation="load_analysis_data",
            default_value=pl.DataFrame(),
            data_source="missing_analysis_data.xlsx",
        )
        def load_analysis_data(file_path: str) -> pl.DataFrame:
            """Simulate loading analysis data that might fail."""
            if not Path(file_path).exists():
                message = f"Analysis data file not found: {file_path}"
                raise FileNotFoundError(message)
            # Simulate successful loading
            return pl.DataFrame({"test": [1, 2, 3]})

        # This will fail gracefully and return default value
        result = load_analysis_data("nonexistent_file.xlsx")

        # Verify default value is returned
        require_runtime_instance(result, pl.DataFrame)
        if result is None or not result.is_empty():
            raise AssertionError

        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        if not ((len(error_logs)) == (1)):
            raise AssertionError
        if not ((error_logs[0]["error_type"]) == ("FileNotFoundError")):
            raise AssertionError
        if not ((error_logs[0]["operation"]) == ("load_analysis_data")):
            raise AssertionError

    def test_invalid_input_recovery(self) -> None:
        """Test recovery from invalid input errors."""

        # Create a function that validates input and handles validation errors
        @self.error_handler.graceful_degradation(
            operation="process_cost_data",
            default_value=0.0,
            data_source="cost_calculation",
        )
        def process_cost_data(cost_value: float) -> float:
            """Process cost data with validation."""
            # Validate input
            self.validator.validate_numeric_value(cost_value, min_value=0)
            # Process the cost value
            return cost_value * 1.1  # Add 10% markup

        # Test with valid input
        result = process_cost_data(1000)
        require_equal(result, 1100.0)

        # Test with invalid input (negative value)
        result = process_cost_data(-500)
        # Should return default value due to validation error
        if not ((result) == (0.0)):
            raise AssertionError

        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        if not ((len(error_logs)) >= (1)):
            raise AssertionError
        # Find the validation error
        validation_errors = [
            e
            for e in error_logs
            if "ValidationError" in str(e.get("error_type", ""))
            or "less than minimum" in str(e.get("error_message", ""))
        ]
        if not ((len(validation_errors)) >= (1)):
            raise AssertionError

    def test_calculation_error_recovery(self) -> None:
        """Test recovery from calculation errors."""

        # Create a function that might have calculation errors
        @self.error_handler.graceful_degradation(
            operation="calculate_ratio",
            default_value=1.0,
            data_source="ratio_calculation",
        )
        def calculate_ratio(numerator: float, denominator: float) -> float:
            """Calculate ratio with potential division by zero."""
            if denominator == 0:
                message = "Cannot divide by zero"
                raise ZeroDivisionError(message)
            return numerator / denominator

        # Test normal calculation
        result = calculate_ratio(10, 2)
        require_equal(result, 5.0)

        # Test division by zero recovery
        result = calculate_ratio(10, 0)
        # Should return default value due to ZeroDivisionError
        if not ((result) == (1.0)):
            raise AssertionError

        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        zero_div_errors = [
            e for e in error_logs if e.get("error_type") == "ZeroDivisionError"
        ]
        if not ((len(zero_div_errors)) >= (1)):
            raise AssertionError

    def test_checkpoint_recovery_scenario(self) -> None:
        """Test recovery using checkpoints after an error."""
        # Simulate a multi-step analysis process
        analysis_steps: list[_AnalysisStep] = [
            {"step": "data_loading", "data": {"samples": 100}},
            {"step": "preprocessing", "data": {"samples": 100, "features": 50}},
            {"step": "analysis", "data": {"results": [1, 2, 3, 4, 5]}},
            {"step": "reporting", "data": {"summary": "Analysis complete"}},
        ]

        completed_steps: list[tuple[str, str]] = []

        def fail_at_analysis(step_name: str) -> None:
            if step_name == "analysis":
                message = "Analysis failed due to resource constraints"
                raise RuntimeError(message)

        # Process each step and create checkpoints
        for i, step in enumerate(analysis_steps):
            try:
                # Simulate step processing
                fail_at_analysis(step["step"])

                # Create checkpoint for successful step
                checkpoint_id = self.error_handler.create_checkpoint(
                    f"analysis_step_{i}",
                    step["data"],
                    {"step_name": step["step"], "status": "completed"},
                )
                completed_steps.append((step["step"], checkpoint_id))

            except RuntimeError as e:
                context = ErrorContext(
                    operation=f"analysis_step_{i}",
                    data_source=step["step"],
                    parameters={"step_data": step},
                )
                self.error_handler.handle_error(e, context, ErrorSeverity.HIGH)

                # Try to recover using last successful checkpoint
                if completed_steps:
                    last_step_name, last_checkpoint_id = completed_steps[-1]
                    recovered_data = self.error_handler.restore_checkpoint(
                        last_checkpoint_id,
                    )
                    if recovered_data is None:
                        raise AssertionError from e
                    # Log recovery information
                    self.logger.info(
                        "Recovered from checkpoint %s for step %s",
                        last_checkpoint_id,
                        last_step_name,
                    )
                break

        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        runtime_errors = [
            e for e in error_logs if e.get("error_type") == "RuntimeError"
        ]
        if not ((len(runtime_errors)) >= (1)):
            raise AssertionError

        # Verify checkpoints were created
        checkpoints = self.error_handler.list_checkpoints()
        minimum_successful_steps = 2
        if len(checkpoints) < minimum_successful_steps:
            raise AssertionError

    def test_data_quality_error_recovery(self) -> None:
        """Test recovery from data quality issues."""
        # Create test data with quality issues
        test_data = pl.DataFrame(
            {
                "Test": ["Panel", "WES (P)", "WES (T)", "WGS", None],  # Missing value
                "Cost": [50000, 75000, 40000, 60000, -1000],  # Negative value
                "Quantity": [100, 200, np.nan, 150, 80],  # NaN value
            },
            strict=False,
        )

        # Function to process data with quality checks
        @self.error_handler.graceful_degradation(
            operation="process_genomic_data",
            default_value=pl.DataFrame(),
            data_source="genomic_cost_data",
        )
        def process_genomic_data(df: pl.DataFrame) -> pl.DataFrame:
            """Process genomic data with quality validation."""
            # Validate data structure
            self.validator.validate_dataframe(df, min_rows=1)

            # Check for negative costs
            negative_costs = df.filter(pl.col("Cost") < 0)
            if not negative_costs.is_empty():
                message = f"Found {len(negative_costs)} negative cost values"
                raise ValueError(message)

            # Check for missing test names
            missing_tests = df.filter(pl.col("Test").is_null())
            if not missing_tests.is_empty():
                message = f"Found {len(missing_tests)} missing test names"
                raise ValueError(message)

            # Process valid data
            return df.with_columns(
                (pl.col("Cost") * pl.col("Quantity").fill_nan(None).fill_null(1)).alias(
                    "Total_Cost",
                ),
            )

        # Test with problematic data
        result = process_genomic_data(test_data)

        # Should return default value due to data quality issues
        require_runtime_instance(result, pl.DataFrame)
        if result is None or not result.is_empty():
            raise AssertionError

        # Verify errors were logged
        error_logs = self.error_handler.get_error_log()
        value_errors = [e for e in error_logs if e.get("error_type") == "ValueError"]
        if not ((len(value_errors)) >= (1)):
            raise AssertionError

    def test_nested_error_recovery(self) -> None:
        """Test recovery from nested error scenarios."""

        # Create nested functions that might fail
        @self.error_handler.graceful_degradation(
            operation="outer_calculation",
            default_value=0,
            data_source="nested_calculation",
        )
        def outer_calculation(x: int, y: int) -> int:
            """Outer calculation that calls inner calculation."""
            intermediate_result = inner_calculation(x)
            if intermediate_result is None:
                raise AssertionError
            return intermediate_result + y

        @self.error_handler.graceful_degradation(
            operation="inner_calculation",
            default_value=1,
            data_source="nested_calculation",
        )
        def inner_calculation(x: int) -> int:
            """Inner calculation that might fail."""
            if x < 0:
                message = "Input must be non-negative"
                raise ValueError(message)
            return x * 2

        # Test normal operation
        result = outer_calculation(5, 3)
        require_equal(result, 5 * 2 + 3)

        # Test error in inner calculation
        result = outer_calculation(-5, 3)
        # Should recover using default values: (1) + 3 = 4
        require_equal(result, 4)

        # Verify errors were logged
        error_logs = self.error_handler.get_error_log()
        value_errors = [e for e in error_logs if e.get("error_type") == "ValueError"]
        if not ((len(value_errors)) >= (1)):
            raise AssertionError

    def test_resource_exhaustion_recovery(self) -> None:
        """Test recovery from resource exhaustion errors."""
        simulated_limit = 1_000_000

        # Simulate memory-intensive operation
        @self.error_handler.graceful_degradation(
            operation="memory_intensive_operation",
            default_value=list[int](),
            data_source="large_dataset",
        )
        def memory_intensive_operation(size: int) -> list[int]:
            """Simulate memory-intensive operation."""
            if size > simulated_limit:
                # Simulate MemoryError
                message = "Not enough memory to process large dataset"
                raise MemoryError(message)

            # Simulate successful operation
            return list(range(min(size, 1000)))  # Limit to prevent actual memory issues

        # Test normal operation
        result = memory_intensive_operation(100)
        if result is None:
            raise AssertionError
        require_equal(len(result), 100)

        # Test memory exhaustion recovery
        result = memory_intensive_operation(2000000)
        # Should return default value due to MemoryError
        require_runtime_instance(result, list)
        if result is None or len(result) != 0:
            raise AssertionError

        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        memory_errors = [
            e for e in error_logs if "Memory" in str(e.get("error_type", ""))
        ]
        if not ((len(memory_errors)) >= (1)):
            raise AssertionError

    def test_persistent_recovery_scenario(self) -> None:
        """Test recovery using persistent checkpoints after application restart."""
        # Simulate long-running analysis with persistent checkpoints
        analysis_phases = [
            {"phase": "data_ingestion", "progress": 25},
            {"phase": "data_processing", "progress": 50},
            {"phase": "analysis_execution", "progress": 75},
            {"phase": "report_generation", "progress": 100},
        ]

        # Create checkpoints for each phase
        checkpoint_ids: list[str] = []
        for i, phase in enumerate(analysis_phases):
            checkpoint_id = self.error_handler.create_checkpoint(
                f"analysis_phase_{i}",
                phase,
                {"phase_name": phase["phase"], "progress": phase["progress"]},
            )
            checkpoint_ids.append(checkpoint_id)

        # Simulate application restart by creating new error handler
        new_error_handler = setup_standard_error_handling(
            logger=self.logger,
            checkpoint_dir=self.temp_checkpoint_dir,
        )

        # Verify checkpoints can be restored from disk
        restored_checkpoints: list[object] = []
        for checkpoint_id in checkpoint_ids:
            restored_data = new_error_handler.restore_checkpoint(
                checkpoint_id,
                from_disk=True,
            )
            if restored_data is None:
                raise AssertionError
            restored_checkpoints.append(restored_data)

        if not ((len(restored_checkpoints)) == (len(analysis_phases))):
            raise AssertionError

        # Verify checkpoint metadata
        listed_checkpoints = new_error_handler.list_checkpoints()
        if not ((len(listed_checkpoints)) == (len(analysis_phases))):
            raise AssertionError

        # Test continuing from last checkpoint
        last_checkpoint = restored_checkpoints[-1]
        require_equal(last_checkpoint, {"phase": "report_generation", "progress": 100})


if __name__ == "__main__":
    unittest.main()
