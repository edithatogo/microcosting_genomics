# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replay midpoint costs from the ordered summary export (stage rows then subtotal)."""

import polars as pl

RECONCILIATION_TOLERANCE = 0.01


def midpoint_components(source: pl.DataFrame) -> pl.DataFrame:
    """Reconcile each ordered stage group with its supplied final subtotal."""
    rows = source.filter(pl.col("Test").is_not_null())
    result = rows.group_by("Test", "Category", maintain_order=True).agg(
        pl.col("MP").last().alias("subtotal"),
        pl.col("MP").slice(0, pl.len() - 1).sum().alias("stage_sum"),
    )
    if result.filter(
        pl.col("subtotal").is_null()
        | ((pl.col("subtotal") - pl.col("stage_sum")).abs() > RECONCILIATION_TOLERANCE),
    ).height:
        message = "Ordered summary no longer reconciles to its final subtotal"
        raise ValueError(message)
    return result


def assay_totals(rows: pl.DataFrame) -> pl.DataFrame:
    """Aggregate individual stage components; the original sheet marks zero with '-'."""
    settings = ["LL", "MP", "UL"]
    subtotal = (
        (pl.col("Category") == "Total") | (pl.col("Stage") == "Total")
    ).fill_null(value=False)
    detail = rows.filter(~subtotal)
    detail = detail.with_columns(
        pl.col(settings).cast(pl.String).replace("-", "0").cast(pl.Float64),
    )
    if (
        detail.select(
            pl.any_horizontal(pl.col("Test", "Category", "Stage").is_null()).any(),
        ).item()
        or detail.select("Test", "Category", "Stage").is_duplicated().any()
    ):
        message = "Incomplete or duplicate stage record"
        raise ValueError(message)
    if detail.select(
        pl.any_horizontal(
            pl.col(settings).is_null() | ~pl.col(settings).is_finite(),
        ).any(),
    ).item():
        message = "Incomplete or nonfinite numeric stage cost"
        raise ValueError(message)
    return detail.group_by("Test", maintain_order=True).agg(pl.col(settings).sum())
