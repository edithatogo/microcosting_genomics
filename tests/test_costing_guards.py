# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reject missing stage identities and keep the explicit one-cent boundary."""

import polars as pl
import pytest

from genomics_microcosting.polars_costing import assay_totals, midpoint_components


@pytest.mark.parametrize("missing", ["Test", "Category", "Stage"])
def test_missing_stage_identity_is_not_silently_dropped(missing: str) -> None:
    """A missing category/stage must not disappear through nullable filters."""
    rows = pl.DataFrame(
        {
            "Test": ["Panel"],
            "Category": ["Labour"],
            "Stage": ["Preparation"],
            "LL": [1.0],
            "MP": [1.0],
            "UL": [1.0],
        },
    ).with_columns(pl.lit(None, dtype=pl.String).alias(missing))
    with pytest.raises(ValueError, match="Incomplete or duplicate"):
        assay_totals(rows)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_missing_or_nonfinite_cost_is_not_zero(value: float | None) -> None:
    """Native aggregation must not turn an unvalued input into a zero cost."""
    rows = pl.DataFrame(
        {
            "Test": ["Panel"],
            "Category": ["Labour"],
            "Stage": ["Preparation"],
            "LL": [value],
            "MP": [1.0],
            "UL": [1.0],
        },
    )
    with pytest.raises(ValueError, match="numeric stage cost"):
        assay_totals(rows)


@pytest.mark.parametrize("difference", [-0.01, 0.01])
def test_exact_one_cent_reconciliation_is_accepted(difference: float) -> None:
    """Retain the original inclusive one-cent policy at both boundaries."""
    rows = pl.DataFrame(
        {
            "Test": ["Panel", "Panel"],
            "Category": ["Labour", "Labour"],
            "MP": [0.0, difference],
        },
    )
    result = midpoint_components(rows)
    if result.item(0, "subtotal") != difference:
        raise AssertionError(result)


@pytest.mark.parametrize("difference", [-0.02, 0.02])
def test_larger_reconciliation_error_is_rejected(difference: float) -> None:
    """Require the same reconciliation policy for positive and negative errors."""
    rows = pl.DataFrame(
        {
            "Test": ["Panel", "Panel"],
            "Category": ["Labour", "Labour"],
            "MP": [0.0, difference],
        },
    )
    with pytest.raises(ValueError, match="no longer reconciles"):
        midpoint_components(rows)
