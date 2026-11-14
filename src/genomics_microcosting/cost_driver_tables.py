# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Source-backed Polars cost contributions with explicit valuation selection."""

import hashlib
import json
from pathlib import Path

import polars as pl

from .excel_utils import load_sheet_with_headers
from .subtotal_audit import audit_subtotals


def summarise_cost_drivers(frame: pl.DataFrame, *, cost_column: str) -> pl.DataFrame:
    """Summarise selected source rows within assay, retaining pricing gaps.

    The caller must select component and unresolved unpriced rows explicitly.
    Source subtotal rows must not be mixed with their component rows.
    """
    keys = ["Test", "Category", "Sub-Category"]
    selected = frame.select(*keys, pl.col(cost_column).cast(pl.Float64).alias("cost"))
    if selected.filter(
        pl.col("cost").is_not_null() & ~pl.col("cost").is_finite(),
    ).height:
        message = "Nonfinite source costs cannot be aggregated"
        raise ValueError(message)
    grouped = selected.group_by(keys, maintain_order=True).agg(
        pl.len().alias("Source_Rows"),
        pl.col("cost").count().alias("Priced_Rows"),
        pl.when(pl.col("cost").count() > 0)
        .then(pl.col("cost").sum())
        .otherwise(None)
        .alias("Absolute_Value"),
    )
    return grouped.with_columns(
        (pl.col("Source_Rows") - pl.col("Priced_Rows")).alias("Unpriced_Rows"),
        pl.when(pl.col("Absolute_Value").sum().over("Test") != 0)
        .then(
            100
            * pl.col("Absolute_Value")
            / pl.col("Absolute_Value").sum().over("Test"),
        )
        .otherwise(None)
        .alias("Percentage_of_Priced_Cost"),
    ).sort(["Test", "Absolute_Value"], descending=[False, True], nulls_last=True)


def qualify_cost_rows(frame: pl.DataFrame, *, cost_column: str) -> pl.DataFrame:
    """Retain every source row and identify explicit totals before aggregation."""
    labelled = (
        frame.with_columns(
            pl.col("Test").alias("Source_Test"),
            pl.col("Category").alias("Source_Category"),
            pl.col("Sub-Category").alias("Source_Sub_Category"),
        )
        .with_row_index("Source_Row", offset=5)
        .with_columns(
            pl.col("Test").forward_fill(),
        )
        .with_columns(pl.col("Category").forward_fill().over("Test"))
        .with_columns(
            pl.col("Sub-Category").forward_fill().over("Test", "Category"),
        )
    )
    total = pl.col("Step").str.contains(r"(?i)^\s*total\b").fill_null(value=False)
    component = pl.all_horizontal(
        pl.col("Test").is_not_null(),
        pl.col("Category").is_not_null(),
        pl.col("Sub-Category").is_not_null(),
        pl.col("Step").is_not_null(),
    )
    return labelled.with_columns(
        pl.when(total)
        .then(pl.lit("subtotal"))
        .when(component & pl.col(cost_column).is_not_null())
        .then(pl.lit("component"))
        .when(component)
        .then(pl.lit("unpriced_or_heading"))
        .when(pl.col(cost_column).is_not_null())
        .then(pl.lit("unresolved_priced"))
        .otherwise(pl.lit("header_or_blank"))
        .alias("Row_Role"),
    )


def write_source_cost_report(
    workbook: str,
    output_dir: str,
    *,
    cost_column: str,
) -> None:
    """Save source row roles, component contributions and a labelled report."""
    source = Path(workbook)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    frame = load_sheet_with_headers(
        source,
        "Detailed Table",
        header_rows=4,
        string_columns=["Test", "Category", "Sub-Category", "Step"],
    )
    audit = qualify_cost_rows(frame, cost_column=cost_column)
    contributions = summarise_cost_drivers(
        audit.filter(pl.col("Row_Role").is_in(["component", "unpriced_or_heading"])),
        cost_column=cost_column,
    )
    audit.write_parquet(destination / "source-row-audit.parquet")
    contributions.write_parquet(destination / "cost-contributions.parquet")
    contributions.write_csv(destination / "cost-contributions.csv")
    subtotal_checks = audit_subtotals(workbook)
    subtotal_checks.write_csv(destination / "subtotal-reconciliation.csv")
    roles = audit.group_by("Row_Role").len().to_dicts()
    report = (
        "# Source-backed cost contributions\n\n"
        f"Valuation column: {cost_column}. Currency and price year follow the "
        "source workbook.\n\n"
        "Only priced component values are summed. Explicit totals and unresolved "
        "priced rows remain in the row audit. Percentages use priced component cost "
        "within each assay; "
        "Unpriced or heading rows remain separately in the row audit and are counted "
        "as unpriced in group totals; missing prices are not assumed zero. "
        "This is a component contribution report, not "
        "a reconciliation to every workbook subtotal or a replacement for published "
        "test prices.\n\n"
        "Subtotal reconciliation: see subtotal-reconciliation.csv. "
        "Alternative branches are not combined automatically.\n\n" + str(contributions)
    )
    (destination / "report.md").write_text(report)
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        message = "Source workbook changed during report generation"
        raise RuntimeError(message)
    manifest = {
        "source_sha256": source_hash,
        "cost_column": cost_column,
        "row_roles": roles,
        "model_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in destination.iterdir()
            if p.name != "manifest.json"
        },
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
