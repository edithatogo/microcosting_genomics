# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Export multiple sheets from the microcosting workbook to CSV files.

Data files are stored in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

import csv
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).resolve().parents[0] / "data"
workbook = openpyxl.load_workbook(
    DATA_DIR
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm",
)

sheets_to_export = [
    "At a Glance",
    "Summary Table",
    "Detailed Table",
    "Process",
    "Labour - Costs - VCGS",
    "Cons -  Costs and Util - VCGS",
    "Eq - Costs and Usage - VCGS",
]

for sheet_name in sheets_to_export:
    sheet = workbook[sheet_name]
    with Path(DATA_DIR / f"{sheet_name}.csv").open("w", newline="") as f:
        c = csv.writer(f)
        for r in sheet.rows:
            c.writerow([cell.value for cell in r])
