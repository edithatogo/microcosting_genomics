# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test for 3. Estimates table transfer and validation."""

import logging
from pathlib import Path

import polars as pl
import pytest

from tests.checks import require, require_runtime_instance

logger = logging.getLogger(__name__)


def test_3__estimates_loading() -> None:
    """Test that the 3. Estimates table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
    if prepared_path.exists():
        df = pl.read_parquet(prepared_path)
        require_runtime_instance(df, pl.DataFrame)
        require(condition=len(df) > 0)
        require(condition=len(df.columns) > 0)
        logger.info(
            "%s",
            f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}",
        )
    else:
        # Try alternative names
        alternatives = [
            "3._estimates",
            "3._Estimates",
        ]
        found = False
        for alt in alternatives:
            # Try different extensions
            for ext in [".parquet"]:
                prepared_path = Path("data/prepared") / f"{alt}{ext}"
                if prepared_path.exists():
                    df = pl.read_parquet(prepared_path)
                    require_runtime_instance(df, pl.DataFrame)
                    require(condition=len(df) > 0)
                    require(condition=len(df.columns) > 0)
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
            if found:
                break
        if not found:
            # List available files for debugging
            logger.info("%s", "Available prepared files:")
            for f in Path("data/prepared").glob("*.parquet"):
                logger.info("%s", f"  - {f.name}")
            pytest.skip("Prepared data for 3. Estimates not found")


def test_3__estimates_data_integrity() -> None:
    """Test data integrity for 3. Estimates table."""
    maximum_null_fraction = 0.5
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

        # Allow up to 50% null values (this might need adjustment based on the table)
        if not (null_percentage < maximum_null_fraction):
            message = f"Too many null values: {null_percentage:.2%}"
            raise AssertionError(message)

        logger.info("%s", "Data integrity check passed for 3. Estimates")
        logger.info("%s", f"  - Null value percentage: {null_percentage:.2%}")
    else:
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "3._estimates" in f.name:
                df = pl.read_parquet(f)
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

                # Allow up to 50% null values (this might need adjustment based on the
                # table)
                if not (null_percentage < maximum_null_fraction):
                    message = f"Too many null values: {null_percentage:.2%}"
                    raise AssertionError(message)

                logger.info("%s", "Data integrity check passed for 3. Estimates")
                logger.info("%s", f"  - Null value percentage: {null_percentage:.2%}")
                found = True
                break
        if not found:
            pytest.skip("Prepared data for 3. Estimates not found")


def test_3__estimates_schema_consistency() -> None:
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
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "3._estimates" in f.name:
                df = pl.read_parquet(f)
                # Check that we have columns
                if not (len(df.columns) > 0):
                    raise AssertionError

                # Check for duplicate column names
                columns_list = list(df.columns)
                if len(columns_list) != len(set(columns_list)):
                    message = "Duplicate column names found"
                    raise AssertionError(message)

                logger.info("%s", "Schema consistency check passed for 3. Estimates")
                found = True
                break
        if not found:
            pytest.skip("Prepared data for 3. Estimates not found")


if __name__ == "__main__":
    try:
        test_3__estimates_loading()
        test_3__estimates_data_integrity()
        test_3__estimates_schema_consistency()
        logger.info("%s", "All tests passed!")
    except Exception:
        logger.exception("Prepared-table check failed")
