# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Log row counts without loading a pandas runtime."""

import logging
from pathlib import Path

import polars as pl

PREP_DIR = Path("data/prepared")
logger = logging.getLogger(__name__)


def get_row_counts() -> None:
    """Read only Parquet metadata/counts for the two reference tables."""
    for name in ("2._labor_prices.parquet", "3._estimates.parquet"):
        count = pl.scan_parquet(PREP_DIR / name).select(pl.len()).collect().item()
        logger.info("%s row count: %s", name, count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    get_row_counts()
