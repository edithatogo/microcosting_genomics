# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check conservation when an assay stage is split into two entries."""

import polars as pl
from hypothesis import given, settings
from hypothesis import strategies as st

from genomics_microcosting.polars_costing import assay_totals


# This checks values; pytest-timeout bounds hangs independently of instrumentation.
@settings(deadline=None)
@given(st.integers(0, 100000), st.integers(0, 100000))
def test_stage_split_conserves_assay_cost(left: int, right: int) -> None:
    """A source subtotal must never add another copy of the assay cost."""
    values = [left, right, left + right]
    rows = pl.DataFrame(
        {
            "Test": ["Panel"] * 3,
            "Category": ["Labour"] * 3,
            "Stage": ["Preparation", "Sequencing", "Total"],
            **dict.fromkeys(("LL", "MP", "UL"), values),
        },
    )
    if not (assay_totals(rows).item(0, "MP") == left + right):
        raise AssertionError
