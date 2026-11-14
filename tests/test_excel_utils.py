# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check workbook reading and multi-row headers."""

import hashlib
from pathlib import Path

import openpyxl
import polars as pl

from genomics_microcosting.excel_utils import load_sheet_with_headers


def test_load_sheet_with_headers() -> None:
    """Check load sheet with headers."""
    file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    df = load_sheet_with_headers(
        file,
        sheet_name="Detailed Table",
        header_rows=4,
        string_columns=["Test", "Category", "Sub-Category", "Step"],
    )
    if not (df.columns[0] == "Test"):
        raise AssertionError
    if not (df.dtypes[0] == pl.String):
        raise AssertionError
    if not (df.dtypes[4] == pl.Float64):
        raise AssertionError
    if not (df.item(0, 0) == "Panel"):
        raise AssertionError
    if not (df.item(0, 4) == 1.0):
        raise AssertionError


def test_merged_header_coordinates_and_data_preservation(tmp_path: Path) -> None:
    """Expand asymmetric merged ranges without changing source workbook bytes."""
    workbook = openpyxl.Workbook()
    sheet = workbook["Sheet"]
    sheet.title = "Costs"
    sheet.append(["Component", "Unit", "Costs", None])
    sheet.append([None, "Unit", "Low", "High"])
    sheet.append(["Labour", "hour", 1.25, 2.5])
    sheet.merge_cells("A1:A2")
    sheet.merge_cells("C1:D1")
    path = tmp_path / "headers.xlsx"
    workbook.save(path)
    workbook.close()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = load_sheet_with_headers(
        path,
        "Costs",
        header_rows=2,
        string_columns=["Component", "Unit"],
    )
    if not (result.columns == ["Component", "Unit", "Costs Low", "Costs High"]):
        raise AssertionError
    if not (result.row(0) == ("Labour", "hour", 1.25, 2.5)):
        raise AssertionError
    if not (hashlib.sha256(path.read_bytes()).hexdigest() == before):
        raise AssertionError
