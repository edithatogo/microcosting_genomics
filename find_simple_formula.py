# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Locate the first uncomplicated multiplication formula in prepared values."""

import logging

import polars as pl

logger = logging.getLogger(__name__)


def find_formula() -> None:
    """Find a formula containing '*' without a structured '[' reference."""
    df = pl.read_parquet("data/prepared/detailed_table_formulas.parquet")
    for col_name in df.columns:
        for i, cell_value in enumerate(df[col_name]):
            if (
                isinstance(cell_value, str)
                and "*" in cell_value
                and "[" not in cell_value
            ):
                logger.info(
                    "Found simple formula at row %s, column %r: %s",
                    i,
                    col_name,
                    cell_value,
                )
                return


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    find_formula()
