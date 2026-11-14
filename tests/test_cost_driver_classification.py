# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Distinguish priced components from ambiguous unpriced worksheet rows."""

import polars as pl

from genomics_microcosting.cost_driver_tables import (
    qualify_cost_rows,
    summarise_cost_drivers,
)
from tests.checks import require_equal


def test_unpriced_steps_are_not_asserted_to_be_cost_components() -> None:
    """Preserve unknown rows without classifying them as priced components."""
    frame = pl.DataFrame(
        {
            "Test": ["test", None, None, None],
            "Category": ["Equipment", None, None, None],
            "Sub-Category": ["Sequencing", None, None, None],
            "Step": ["stage heading", "instrument", "-", "Total"],
            "cost": [None, 12.0, None, 12.0],
        },
    )
    result = qualify_cost_rows(frame, cost_column="cost")
    require_equal(
        result["Row_Role"].to_list(),
        ["unpriced_or_heading", "component", "unpriced_or_heading", "subtotal"],
    )
    require_equal(result["cost"].to_list(), [None, 12.0, None, 12.0])
    selected = result.filter(
        pl.col("Row_Role").is_in(["component", "unpriced_or_heading"]),
    )
    summary = summarise_cost_drivers(selected, cost_column="cost")
    require_equal(summary["Absolute_Value"].to_list(), [12.0])
    require_equal(summary["Unpriced_Rows"].to_list(), [2])
