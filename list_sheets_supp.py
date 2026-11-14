# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""List worksheets in the supplemental input workbook."""

import sys
lazy from pathlib import Path

import openpyxl


def list_sheet_names(file_path: str | Path) -> None:
    """List the sheet names in an Excel file."""
    workbook = openpyxl.load_workbook(file_path, read_only=True)
    sys.stdout.writelines(("Sheet names:", "\n"))
    for sheet_name in workbook.sheetnames:
        sys.stdout.writelines((f"- {sheet_name}", "\n"))


if __name__ == "__main__":
    list_sheet_names(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    )
