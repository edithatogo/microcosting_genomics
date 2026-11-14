# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test for Detailed Table validation."""

import logging
from pathlib import Path

import polars as pl
import pytest

from tests.checks import require_runtime_instance

logger = logging.getLogger(__name__)


def test_detailed_table_loading() -> None:
    """Test that the Detailed Table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pl.read_parquet(prepared_path)
        require_runtime_instance(df, pl.DataFrame)
        if not (len(df) > 0):
            raise AssertionError
        if not (len(df.columns) > 0):
            raise AssertionError
        logger.info(
            "%s",
            f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}",
        )
    else:
        pytest.skip("Prepared data for Detailed Table not found")


def test_detailed_table_data_integrity() -> None:
    """Test data integrity for Detailed Table."""
    maximum_null_fraction = 0.7
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pl.read_parquet(prepared_path)

        # Check for reasonable data types
        if not (len(df.columns) > 0):
            raise AssertionError

        # Check for null values (should be reasonable amount)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = (
            df.with_columns(pl.selectors.float().fill_nan(None))
            .null_count()
            .sum_horizontal()
            .item()
        )
        null_percentage = null_cells / total_cells if total_cells > 0 else 0

        # For Detailed Table, allow up to 70% null values as it's expected to have
        # sparse data
        if not (null_percentage < maximum_null_fraction):
            message = f"Too many null values: {null_percentage:.2%}"
            raise AssertionError(message)

        logger.info("%s", "Data integrity check passed for Detailed Table")
        logger.info("%s", f"  - Null value percentage: {null_percentage:.2%}")

        # Check that we have the expected columns
        expected_columns = ["Test", "Category", "Sub-Category", "Step"]
        for col in expected_columns:
            if col not in df.columns:
                raise AssertionError(col)

    else:
        pytest.skip("Prepared data for Detailed Table not found")


def test_detailed_table_schema_consistency() -> None:
    """Test schema consistency for Detailed Table."""
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pl.read_parquet(prepared_path)

        # Check that we have columns
        if not (len(df.columns) > 0):
            raise AssertionError

        # Check for duplicate column names
        columns_list = list(df.columns)
        if len(columns_list) != len(set(columns_list)):
            message = "Duplicate column names found"
            raise AssertionError(message)

        logger.info("%s", "Schema consistency check passed for Detailed Table")
    else:
        pytest.skip("Prepared data for Detailed Table not found")


if __name__ == "__main__":
    try:
        test_detailed_table_loading()
        test_detailed_table_data_integrity()
        test_detailed_table_schema_consistency()
        logger.info("%s", "All tests passed!")
    except Exception as e:
        logger.info("%s", f"Test error: {e}", exc_info=True)
        import traceback

        traceback.print_exc()
