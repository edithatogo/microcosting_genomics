# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect a cell in the synthetic Excel fixture."""

import sys

import openpyxl


def debug_excel() -> None:
    """Display the value of cell A2 in the fixture."""
    sys.stdout.write("Starting Excel debug script...\n")

    # Load the workbook
    workbook = openpyxl.load_workbook("tests/test_data.xlsx")

    try:
        sys.stdout.write(f"Value of A2: {workbook['Sheet1']['A2'].value}\n")
    finally:
        workbook.close()


if __name__ == "__main__":
    debug_excel()
