# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Extract formula and value CSVs from the detailed Excel sheet.

Data files are stored in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

import csv
import sys
from pathlib import Path

import openpyxl
from openpyxl.cell import MergedCell

# Define the output directory
DATA_DIR = Path(__file__).resolve().parents[0] / "data"
output_dir = DATA_DIR / "extracted"
Path(output_dir).mkdir(parents=True, exist_ok=True)

# Load the workbook to get formulas
workbook = openpyxl.load_workbook(
    DATA_DIR
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    data_only=False,
)

# Select the sheet
sheet_name = "Detailed Table"
sheet = workbook[sheet_name]

# Define file paths
values_file_path = str(Path(output_dir).joinpath(f"{sheet_name}_values.csv"))
formulas_file_path = str(Path(output_dir).joinpath(f"{sheet_name}_formulas.csv"))

# Extract formulas
with Path(formulas_file_path).open("w", newline="") as f:
    c = csv.writer(f)
    for row in sheet.rows:
        row_data = []
        for cell in row:
            if isinstance(cell, MergedCell):
                row_data.append("")  # Write empty string for merged cells
            else:
                row_data.append(cell.value)
        c.writerow(row_data)

# Now get values by loading with data_only=True
workbook_values = openpyxl.load_workbook(
    DATA_DIR
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    data_only=True,
)
sheet_values = workbook_values[sheet_name]

# Extract values
with Path(values_file_path).open("w", newline="") as f:
    c = csv.writer(f)
    for row in sheet_values.rows:
        row_data = []
        for cell in row:
            if isinstance(cell, MergedCell):
                row_data.append("")  # Write empty string for merged cells
            else:
                row_data.append(cell.value)
        c.writerow(row_data)

sys.stdout.writelines((f"Extracted values to {values_file_path}", "\n"))
sys.stdout.writelines((f"Extracted formulas to {formulas_file_path}", "\n"))
