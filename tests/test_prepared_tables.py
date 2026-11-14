# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0

"""Check prepared labour prices and estimate tables."""

import logging
from pathlib import Path

import polars as pl

from tests.checks import require_equal

PREP_DIR = Path("data/prepared")


logger = logging.getLogger(__name__)


def test_labor_prices_table() -> None:
    """Check labor prices table."""
    df = pl.read_parquet(PREP_DIR / "2._labor_prices.parquet")
    require_equal(df.shape[0], 79)
    require_equal(df.shape[1], 52)


def test_estimates_table() -> None:
    """Check estimates table."""
    df = pl.read_parquet(PREP_DIR / "3._estimates.parquet")
    require_equal(df.shape[0], 77)
    require_equal(df.shape[1], 34)
