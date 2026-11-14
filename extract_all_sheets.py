# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Export workbook sheets for inspection."""

import csv
import sys
from pathlib import Path

import openpyxl

# Corrected path assuming the script is run from the project root
DATA_DIR = Path.cwd() / "data"
EXTRACTED_DIR = DATA_DIR / "extracted"
EXTRACTED_DIR.mkdir(exist_ok=True)

# Load workbook with formulas
workbook_formulas = openpyxl.load_workbook(
    DATA_DIR
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    data_only=False,
)
# Load workbook with values
workbook_values = openpyxl.load_workbook(
    DATA_DIR
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
    data_only=True,
)

for sheet_name in workbook_formulas.sheetnames:
    sheet_formulas = workbook_formulas[sheet_name]
    sheet_values = workbook_values[sheet_name]

    # Sanitize sheet name for filename
    safe_sheet_name = (
        sheet_name.replace(" ", "_")
        .replace("-", "_")
        .replace("+", "")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
    )

    # Extract formulas
    formula_file_path = EXTRACTED_DIR / f"{safe_sheet_name}_formulas.csv"
    with Path(formula_file_path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in sheet_formulas.rows:
            writer.writerow([cell.value for cell in row])

    # Extract values
    value_file_path = EXTRACTED_DIR / f"{safe_sheet_name}_values.csv"
    with Path(value_file_path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in sheet_values.rows:
            writer.writerow([cell.value for cell in row])

sys.stdout.writelines(
    (
        (
            "Extracted formulas and values for all "
            f"{len(workbook_formulas.sheetnames)} sheets to {EXTRACTED_DIR}"
        ),
        "\n",
    ),
)
