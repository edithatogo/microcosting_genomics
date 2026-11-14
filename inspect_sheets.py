# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect worksheet names, shapes and leading rows."""

import sys
lazy from pathlib import Path

import openpyxl


def inspect_sheets(file_path: str | Path) -> None:
    """Print the first 5 rows of each sheet in an Excel file."""
    workbook = openpyxl.load_workbook(file_path, read_only=True)
    for sheet_name in workbook.sheetnames:
        sys.stdout.writelines((f"--- Sheet: {sheet_name} ---", "\n"))
        sheet = workbook[sheet_name]
        for row in sheet.iter_rows(min_row=1, max_row=5):
            sys.stdout.writelines((str([cell.value for cell in row]), "\n"))
        sys.stdout.writelines(("\n", "\n"))


if __name__ == "__main__":
    inspect_sheets(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    )
