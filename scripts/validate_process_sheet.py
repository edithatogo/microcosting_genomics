# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Compare the process worksheet with the calculated results."""

import sys
from pathlib import Path

from src.genomics_microcosting.calculation_engine import CalculationEngine
from src.genomics_microcosting.sheet_manager import SheetManager

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))


def validate_process_sheet() -> None:
    """Compare calculated process data with the reference worksheet."""
    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)

    sheet_name = "Process"

    # Ensure the sheet is loaded
    if sheet_name not in sheet_manager.get_sheet_names():
        sys.stdout.write(f"Sheet '{sheet_name}' not found in the workbook." + "\n")
        return

    # Run the calculation engine on the "Process" sheet
    results_df, errors = engine.run_engine(sheet_name)

    if errors:
        sys.stdout.write(f"Errors found while calculating '{sheet_name}':" + "\n")
        for error in errors:
            sys.stdout.write(str(error) + "\n")
        return

    # Get the original data from the Excel file
    original_df = sheet_manager.get_data(sheet_name)

    # Compare the results
    comparison = results_df.compare(original_df)

    if comparison.empty:
        sys.stdout.write(
            f"Validation successful for '{sheet_name}'. No differences found." + "\n",
        )
    else:
        sys.stdout.write(
            f"Validation failed for '{sheet_name}'. Differences found:" + "\n",
        )
        sys.stdout.write(str(comparison) + "\n")


if __name__ == "__main__":
    validate_process_sheet()
