# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test for DSA - Labour Prices table transfer and validation."""

import logging
from pathlib import Path

import polars as pl
import pytest

from tests.checks import require_runtime_instance

logger = logging.getLogger(__name__)


def test_dsa___labour_prices_loading() -> None:
    """Test that the DSA - Labour Prices table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "dsa___labour_prices.parquet"
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
        # Try alternative names
        alternatives = [
            "dsa---labour-prices",
            "dsa   labour prices",
            "DSA - Labour Prices",
        ]
        found = False
        for alt in alternatives:
            prepared_path = Path("data/prepared") / f"{alt}.parquet"
            if prepared_path.exists():
                df = pl.read_parquet(prepared_path)
                require_runtime_instance(df, pl.DataFrame)
                if not (len(df) > 0):
                    raise AssertionError
                if not (len(df.columns) > 0):
                    raise AssertionError
                logger.info(
                    "%s",
                    "Loaded "
                    f"{len(df)}"
                    " rows and "
                    f"{len(df.columns)}"
                    " columns from "
                    f"{prepared_path}",
                )
                found = True
                break
        if not found:
            pytest.skip("Prepared data for DSA - Labour Prices not found")


def test_dsa___labour_prices_data_integrity() -> None:
    """Test data integrity for DSA - Labour Prices table."""
    maximum_null_fraction = 0.5
    prepared_path = Path("data/prepared") / "dsa___labour_prices.parquet"
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

        # Allow up to 50% null values (this might need adjustment based on the table)
        if not (null_percentage < maximum_null_fraction):
            message = f"Too many null values: {null_percentage:.2%}"
            raise AssertionError(message)

        logger.info("%s", "Data integrity check passed for DSA - Labour Prices")
        logger.info("%s", f"  - Null value percentage: {null_percentage:.2%}")
    else:
        pytest.skip("Prepared data for DSA - Labour Prices not found")


def test_dsa___labour_prices_schema_consistency() -> None:
    """Test schema consistency for DSA - Labour Prices table."""
    prepared_path = Path("data/prepared") / "dsa___labour_prices.parquet"
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

        logger.info("%s", "Schema consistency check passed for DSA - Labour Prices")
    else:
        pytest.skip("Prepared data for DSA - Labour Prices not found")


if __name__ == "__main__":
    try:
        test_dsa___labour_prices_loading()
        test_dsa___labour_prices_data_integrity()
        test_dsa___labour_prices_schema_consistency()
        logger.info("%s", "All tests passed!")
    except Exception:
        logger.exception("Prepared-table check failed")
