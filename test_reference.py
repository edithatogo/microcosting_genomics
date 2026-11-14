#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cross-sheet reference resolution."""

import re
import sys

import openpyxl

# Load workbook
wb = openpyxl.load_workbook(
    "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    data_only=True,
)

# Test resolving a specific reference
formula = "='Labour - Usage - VCGS'!C5"
sys.stdout.writelines((f"Testing formula: {formula}", "\n"))

# Match pattern
pattern = r"'([^']+)'!([A-Z]+)(\d+)"
match = re.match(pattern, formula.strip())

if match:
    sheet_name, col_letter, row_num = match.groups()
    sys.stdout.writelines((f"Sheet: {sheet_name}", "\n"))
    sys.stdout.writelines((f"Column: {col_letter}", "\n"))
    sys.stdout.writelines((f"Row: {row_num}", "\n"))

    # Get the sheet
    ws = wb[sheet_name]

    # Convert column letter to index
    col_index = 0
    for char in col_letter.upper():
        col_index = col_index * 26 + (ord(char) - ord("A") + 1)
    col_index -= 1

    sys.stdout.writelines((f"Column index: {col_index}", "\n"))

    # Get the value
    row_index = int(row_num) - 1
    sys.stdout.writelines((f"Row index: {row_index}", "\n"))

    # Get all data from the sheet first
    data = []
    data.extend(row for row in ws.iter_rows(values_only=True))

    import pandas as pd

    df = pd.DataFrame(data)
    sys.stdout.writelines((f"Sheet shape: {df.shape}", "\n"))

    if row_index < len(df) and col_index < len(df.columns):
        value = df.iloc[row_index, col_index]
        sys.stdout.writelines((f"Value at [{row_index}, {col_index}]: {value}", "\n"))
        sys.stdout.writelines((f"Value type: {type(value)}", "\n"))
    else:
        sys.stdout.writelines(
            (
                (
                    "Index out of bounds: row "
                    f"{row_index}"
                    "/"
                    f"{len(df)}"
                    ", col "
                    f"{col_index}"
                    "/"
                    f"{len(df.columns)}"
                ),
                "\n",
            ),
        )
else:
    sys.stdout.writelines(("No match found", "\n"))
