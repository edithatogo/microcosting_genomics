# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect one prepared source cell using the native Polars table."""

import logging

import polars as pl

logger = logging.getLogger(__name__)


def inspect_data() -> None:
    """Log the value and Python type of row 428 in the Test column."""
    df = pl.read_parquet("data/prepared/detailed_table_formulas.parquet")
    value: object = df.item(428, "Test")
    logger.info("Value at row 428, column 'Test': %r", value)
    logger.info("Value type: %s", type(value))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    inspect_data()
