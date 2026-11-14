#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to list all sheets in the Excel workbook and their basic information."""

import json
import logging
import sys
from pathlib import Path

from openpyxl import load_workbook

logger = logging.getLogger(__name__)

CELL_PREVIEW_LIMIT = 3


def list_excel_sheets() -> None:
    """List all sheets in the Excel workbook."""
    # Try to find the Excel file
    possible_paths = [
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
        "data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx",
    ]

    excel_file_path = None
    for path in possible_paths:
        if Path(path).exists():
            excel_file_path = path
            break

    if not excel_file_path:
        sys.stdout.write("No Excel file found" + "\n")
        return

    sys.stdout.write(f"Found Excel file: {excel_file_path}" + "\n")

    # Load the workbook
    wb = load_workbook(excel_file_path, read_only=True, data_only=True)

    sys.stdout.write(f"\nAvailable sheets ({len(wb.sheetnames)} total):" + "\n")
    sys.stdout.write(str("=" * 50) + "\n")

    sheet_info = []

    for i, sheet_name in enumerate(wb.sheetnames, 1):
        try:
            ws = wb[sheet_name]
            # Get dimensions
            rows = ws.max_row
            cols = ws.max_column

            # Get first few cells to understand structure
            first_row = []
            for col in range(1, min(6, cols + 1)):  # First 5 columns
                cell_value = ws.cell(row=1, column=col).value
                first_row.append(str(cell_value) if cell_value is not None else "")

            info = {
                "index": i,
                "name": sheet_name,
                "dimensions": f"{rows} rows x {cols} columns",
                "first_row": first_row,
            }
            sheet_info.append(info)

            sys.stdout.write(f"{i:2d}. {sheet_name}" + "\n")
            sys.stdout.write(f"     Dimensions: {rows} rows x {cols} columns" + "\n")
            sys.stdout.write(f"     First row: {', '.join(first_row[:3])}" + "\n")
            if len(first_row) > CELL_PREVIEW_LIMIT:
                sys.stdout.write(
                    f"                ... and {len(first_row) - 3} more columns" + "\n",
                )
            sys.stdout.write("\n")

        except Exception as e:
            logger.exception("Could not complete list excel sheets")
            sys.stdout.write(f"{i:2d}. {sheet_name} - Error: {e}" + "\n")
            continue

    wb.close()

    # Save sheet information to JSON
    output_file = "data/metadata/excel_sheets_info.json"
    with Path(output_file).open("w") as f:
        json.dump(sheet_info, f, indent=2)
    sys.stdout.write(f"Sheet information saved to {output_file}" + "\n")


if __name__ == "__main__":
    list_excel_sheets()
