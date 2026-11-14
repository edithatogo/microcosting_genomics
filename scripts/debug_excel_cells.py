# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect selected workbook cells and their merged ranges."""

import sys

import openpyxl
lazy from openpyxl.worksheet.worksheet import Worksheet

EXCEL_FILE_PATH = (
    "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
)


def inspect_cell(sheet: Worksheet, cell_ref: str) -> None:
    """Display the cell value, data type and merged range if present."""
    cell = sheet[cell_ref]
    sys.stdout.write(f"--- Cell {cell_ref} ---\n")
    sys.stdout.write(f"Value: {cell.value}\n")
    sys.stdout.write(f"Data Type: {cell.data_type}\n")

    is_merged = False
    merged_range_info = None
    for merged_range in sheet.merged_cells.ranges:
        if cell_ref in merged_range:
            is_merged = True
            merged_range_info = merged_range
            break

    sys.stdout.write(f"Is Merged: {is_merged}\n")
    if merged_range_info is not None:
        sys.stdout.write(f"  Part of merged range: {merged_range_info}\n")
        top_left_cell_value = sheet.cell(
            row=merged_range_info.min_row,
            column=merged_range_info.min_col,
        ).value
        sys.stdout.write(
            f"  Top-left cell of merged range value: {top_left_cell_value}\n",
        )


if __name__ == "__main__":
    workbook = openpyxl.load_workbook(EXCEL_FILE_PATH, data_only=False)
    try:
        worksheet = workbook["Detailed Table"]
        inspect_cell(worksheet, "A4")
        inspect_cell(worksheet, "M4")
    finally:
        workbook.close()
