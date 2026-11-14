# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check numeric preservation and alignment in the Polars workbook comparator."""

from hashlib import sha256
lazy from pathlib import Path

import polars as pl
import pytest
from openpyxl import Workbook

from genomics_microcosting.validate_engine import (
    ValidationResults,
    compare_columns_optimized,
    compare_engine_results,
    validation_succeeded,
    verify_engine_markers,
    verify_ground_truth_source,
)


def test_comparison_keeps_presence_disagreement() -> None:
    """Keep absent values visible even when paired numeric values agree."""
    reference = pl.DataFrame({"cost": ["1.0", None, "0", "not numeric"]})
    result = pl.DataFrame({"cost": [1.0, 2.0, 0.0, None]})
    comparison = compare_columns_optimized(reference, result, "cost", "cost")
    if not (comparison is not None):
        raise AssertionError
    if not (comparison["comparisons"] == len([1.0, 0.0])):
        raise AssertionError
    if not (comparison["significant_abs_errors"] == 0):
        raise AssertionError
    if not (comparison["data_quality"]["presence_disagreements"] == 1):
        raise AssertionError


def test_comparison_rejects_unaligned_rows() -> None:
    """Do not silently truncate mismatched workbook/result tables."""
    with pytest.raises(ValueError, match="row counts differ"):
        compare_columns_optimized(
            pl.DataFrame({"x": [1]}),
            pl.DataFrame({"x": [1, 2]}),
            "x",
            "x",
        )


def test_success_requires_all_comparisons_and_presence_agreement() -> None:
    """A saved success flag must meet the command's numerical acceptance gate."""
    metrics = {
        "total_comparisons": 2,
        "significant_errors": 0,
        "presence_disagreements": 0,
    }
    if not (validation_succeeded(metrics, 2, 2)):
        raise AssertionError
    if validation_succeeded(metrics, 1, 2):
        raise AssertionError
    if validation_succeeded({**metrics, "presence_disagreements": 1}, 2, 2):
        raise AssertionError
    if validation_succeeded({**metrics, "significant_errors": 1}, 2, 2):
        raise AssertionError
    if validation_succeeded({**metrics, "total_comparisons": 0}, 2, 2):
        raise AssertionError


def test_validation_requires_all_three_unit_costs_and_matching_rows() -> None:
    """Missing upper costs or changed row identity cannot yield a passing audit."""
    reference = pl.DataFrame(
        {
            "Test": ["WES"],
            "Category": ["Consumables"],
            "Sub-Category": [None],
            "Step": ["Reagent"],
            "Unit Cost (AUD $/unit) LL": [1.0],
            "Estimate_3": [2.0],
            "UL_3": [3.0],
        },
    )
    result = pl.DataFrame(
        {
            "Test": ["WES"],
            "Category": ["Consumables"],
            "Sub-Category": ["Library"],
            "Step": ["Reagent"],
            "Estimates Unit Cost (AUD $/unit) LL": [1.0],
            "Estimates Unit Cost (AUD $/unit) Estimate": [2.0],
            "Estimates Unit Cost (AUD $/unit) UL": [3.0],
        },
    )

    def fresh() -> ValidationResults:
        return {
            "timestamp": "",
            "success": False,
            "ground_truth_loaded": False,
            "engine_initialized": False,
            "engine_run": False,
            "validation_performed": False,
            "metrics": {},
            "errors": [],
            "column_matches": {},
            "validation_details": [],
        }

    complete = fresh()
    compare_engine_results(reference, result, complete)
    if (
        not complete["success"]
        or len(complete["column_matches"]) != len(reference.columns) - 4
    ):
        raise AssertionError
    missing = fresh()
    compare_engine_results(reference.drop("UL_3"), result, missing)
    if missing["success"] or not missing["errors"]:
        raise AssertionError
    different = fresh()
    compare_engine_results(
        reference,
        result.with_columns(pl.lit("Other").alias("Step")),
        different,
    )
    if different["success"] or not different["errors"]:
        raise AssertionError


def test_source_check_rejects_changed_values_and_excel_errors(tmp_path: Path) -> None:
    """The cached source, including discarded markers, is checked before parity."""
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        raise AssertionError
    sheet.title = "Detailed Table"
    sheet["M5"], sheet["N5"], sheet["O5"] = "-", 2.0, 3.0
    path = tmp_path / "source.xlsx"
    workbook.save(path)
    digest = sha256(path.read_bytes()).hexdigest()
    reference = pl.DataFrame(
        {
            "Unit Cost (AUD $/unit) LL": [None],
            "Estimate_3": [2.0],
            "UL_3": [3.0],
        },
    )
    counts = verify_ground_truth_source(reference, path, digest)
    if counts["Unit Cost (AUD $/unit) LL"] != 1:
        raise AssertionError
    with pytest.raises(ValueError, match="differs from source"):
        verify_ground_truth_source(
            reference.with_columns(pl.lit(4.0).alias("Estimate_3")),
            path,
            digest,
        )
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_ground_truth_source(reference, path, "0" * 64)
    sheet["M5"] = "#REF!"
    workbook.save(path)
    with pytest.raises(ValueError, match="Unaccounted source marker"):
        verify_ground_truth_source(
            reference,
            path,
            sha256(path.read_bytes()).hexdigest(),
        )


def test_engine_marker_check_rejects_changed_markers(tmp_path: Path) -> None:
    """Literal markers survive even when the numeric export drops them."""
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        raise AssertionError
    sheet.title = "Detailed Table"
    sheet["M5"], sheet["N5"], sheet["O5"] = "x3", 2.0, "-"
    path = tmp_path / "source.xlsx"
    workbook.save(path)
    result = pl.DataFrame(
        {
            "Estimates Unit Cost (AUD $/unit) LL": ["x3"],
            "Estimates Unit Cost (AUD $/unit) Estimate": [2.0],
            "Estimates Unit Cost (AUD $/unit) UL": ["-"],
        },
    )
    if verify_engine_markers(result, path) != len(["x3", "-"]):
        raise AssertionError
    for wrong in (None, "x1", ""):
        changed = result.with_columns(
            pl.lit(wrong).alias("Estimates Unit Cost (AUD $/unit) LL"),
        )
        with pytest.raises(ValueError, match="Source marker differs"):
            verify_engine_markers(changed, path)
