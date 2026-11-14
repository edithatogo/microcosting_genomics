# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Report scenario prices and simulation draws retained in the original source files."""

import json
from pathlib import Path
from typing import Protocol, cast

import openpyxl
import pandera.polars as pa
import polars as pl
from pydantic import BaseModel, Field, FiniteFloat

_FIRST_ASSAY_COLUMN = 3
_ARCHIVED_DRAW_COUNT = 10000


class _MinimumCheck(Protocol):
    def __call__(self, min_value: int) -> pa.Check: ...


class ArchivedCurve(BaseModel):
    """Stored assay label and all cost draws in source order."""

    name: str
    x: list[FiniteFloat] = Field(
        min_length=_ARCHIVED_DRAW_COUNT,
        max_length=_ARCHIVED_DRAW_COUNT,
    )


SCENARIO_SCHEMA = pa.DataFrameSchema(
    {
        "parameter": pa.Column(str),
        "scenario": pa.Column(str),
        "assay": pa.Column(str),
        "cost": pa.Column(float, checks=cast("_MinimumCheck", pa.Check.ge)(0)),
    },
    strict=True,
    unique=["parameter", "scenario", "assay"],
)


def scenario_costs(path: str | Path) -> pl.DataFrame:
    """Read and validate workbook scenario prices and baseline changes."""
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(book["DSA - Tornado Actual"].values)
    finally:
        book.close()
    records = [
        {"parameter": row[0], "scenario": str(row[1]), "assay": assay, "cost": row[col]}
        for row in rows[3:]
        if row[0] and row[1] is not None
        for col, assay in enumerate(rows[2])
        if col >= _FIRST_ASSAY_COLUMN and assay is not None
    ]
    table = SCENARIO_SCHEMA.validate(pl.DataFrame(records))
    baseline = table.filter(pl.col("scenario").str.contains("base case")).select(
        "parameter",
        "assay",
        pl.col("cost").alias("baseline"),
    )
    result = table.join(baseline, on=["parameter", "assay"], how="left", validate="m:1")
    if (
        result["cost"].null_count()
        or result["baseline"].null_count()
        or result.select("parameter", "scenario", "assay").is_duplicated().any()
    ):
        message = "Incomplete or ambiguous workbook scenario"
        raise ValueError(message)
    return result.with_columns(
        (100 * (pl.col("cost") / pl.col("baseline") - 1)).alias("change_percent"),
    )


def archived_draws(path: str | Path) -> pl.DataFrame:
    """Summarise the unique validated five-assay simulation draw set."""
    cells = json.loads(Path(path).read_text())["cells"]
    candidates: list[list[dict[str, object]]] = []
    for cell in cells:
        for output in cell.get("outputs", []):
            curves = (
                output.get("data", {})
                .get("application/vnd.plotly.v1+json", {})
                .get("data", [])
            )
            if {c.get("name") for c in curves} == {
                "Panel",
                "ES-P",
                "ES-T",
                "GS-P",
                "GS-T",
            } and all(
                isinstance(c.get("x"), list) and len(c["x"]) == _ARCHIVED_DRAW_COUNT
                for c in curves
            ):
                candidates.append(cast("list[dict[str, object]]", curves))
    if not candidates or any(curves != candidates[0] for curves in candidates):
        message = "No unambiguous archived five-assay draw set"
        raise ValueError(message)
    frames: list[pl.DataFrame] = []
    for curve in candidates[0]:
        validated = ArchivedCurve.model_validate(curve)
        values = pl.Series("cost", validated.x, dtype=pl.Float64)
        if values.null_count() or not values.is_finite().all():
            message = "Missing or nonfinite simulation draw"
            raise ValueError(message)
        frames.append(pl.DataFrame({"assay": validated.name, "cost": values}))
    return (
        pl.concat(frames)
        .group_by("assay", maintain_order=True)
        .agg(
            pl.len().alias("draws"),
            pl.col("cost").mean().alias("mean"),
            pl.col("cost").median().alias("median"),
            pl.col("cost").quantile(0.025, interpolation="linear").alias("lower"),
            pl.col("cost").quantile(0.975, interpolation="linear").alias("upper"),
        )
    )


def markdown_table(frame: pl.DataFrame) -> str:
    """Render the evidence table with two decimal places for floats."""
    return "\n".join(
        [
            " | ".join(frame.columns),
            " | ".join(["---"] * frame.width),
            *(
                " | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in row)
                for row in frame.iter_rows()
            ),
        ],
    )
