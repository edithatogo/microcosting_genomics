# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test for 3. Estimates table."""

import logging
from pathlib import Path

import polars as pl
import pytest

from tests.checks import require_runtime_instance

logger = logging.getLogger(__name__)


def test_estimates_loading() -> None:
    """Test that the 3. Estimates table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
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
        return
    pytest.skip("Prepared data for 3. Estimates not found")


def test_estimates_data_integrity() -> None:
    """Test data integrity for 3. Estimates table."""
    maximum_null_fraction = 0.45
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
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

        # For Estimates, allow up to 45% null values (it has 42.17%)
        if not (null_percentage < maximum_null_fraction):
            message = f"Too many null values: {null_percentage:.2%}"
            raise AssertionError(message)

        logger.info("%s", "Data integrity check passed for 3. Estimates")
        logger.info("%s", f"  - Null value percentage: {null_percentage:.2%}")

        # Check that we have some numeric columns (expected for quantities and prices)
        numeric_columns = df.select(pl.selectors.numeric()).columns
        if not (len(numeric_columns) > 0):
            message = "No numeric columns found"
            raise AssertionError(message)
        logger.info("%s", f"  - Numeric columns: {len(numeric_columns)}")
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


def test_estimates_schema_consistency() -> None:
    """Test schema consistency for 3. Estimates table."""
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
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

        logger.info("%s", "Schema consistency check passed for 3. Estimates")
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


if __name__ == "__main__":
    try:
        test_estimates_loading()
        test_estimates_data_integrity()
        test_estimates_schema_consistency()
        logger.info("%s", "All tests passed!")
    except Exception:
        logger.exception("Prepared-table check failed")
