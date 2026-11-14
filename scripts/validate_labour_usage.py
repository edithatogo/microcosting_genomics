# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Compare labour usage with the prepared ground truth."""

import sys

lazy import pandas as pd

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

ERROR_PREVIEW_LIMIT = 5


def _sheet_discrepancies(
    ground_truth_df: pd.DataFrame,
    calculated_df: pd.DataFrame,
    engine: CalculationEngine,
    sheet_name: str,
) -> list[dict]:
    # Compare the results
    discrepancies = []
    for r_idx in range(ground_truth_df.shape[0]):
        for c_idx in range(ground_truth_df.shape[1]):
            excel_value = ground_truth_df.iloc[r_idx, c_idx]
            calculated_value = calculated_df.iloc[r_idx, c_idx]

            # Simple comparison, can be improved for float tolerance
            if str(excel_value) != str(calculated_value):
                formula = engine.get_cell_formula(
                    sheet_name,
                    f"{chr(ord('A') + c_idx)}{r_idx + 1}",
                )
                discrepancies.append(
                    {
                        "cell": f"{chr(ord('A') + c_idx)}{r_idx + 1}",
                        "formula": formula,
                        "excel_value": excel_value,
                        "calculated_value": calculated_value,
                    },
                )

    return discrepancies


def validate_sheet(sheet_name: str) -> None:
    """Compare calculated labour usage with the prepared workbook values."""
    sys.stdout.write(f"--- Validating Sheet: {sheet_name} ---" + "\n")

    # Initialize the sheet manager and engine
    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)

    # Get the ground truth values from the original Excel file
    ground_truth_df = sheet_manager.get_ground_truth(sheet_name)
    if ground_truth_df is None:
        sys.stdout.write(f"Could not load ground truth for sheet: {sheet_name}" + "\n")
        return

    # Run the engine to calculate the values
    result = engine.run_engine(sheet_name)
    if result is None or result[0] is None:
        sys.stdout.write(f"Engine failed to run on sheet: {sheet_name}" + "\n")
        return

    calculated_df, errors = result
    if errors:
        sys.stdout.write(f"Engine encountered {len(errors)} errors:" + "\n")
        for error in errors[:5]:  # Show first 5 errors
            sys.stdout.write(f"  {error}" + "\n")
        if len(errors) > ERROR_PREVIEW_LIMIT:
            sys.stdout.write(f"  ... and {len(errors) - 5} more errors" + "\n")
        return

    discrepancies = _sheet_discrepancies(
        ground_truth_df,
        calculated_df,
        engine,
        sheet_name,
    )

    if discrepancies:
        sys.stdout.write("Discrepancies found:" + "\n")
        for d in discrepancies:
            sys.stdout.write(str(d) + "\n")
    else:
        sys.stdout.write(
            f"Success! No discrepancies found for sheet: {sheet_name}" + "\n",
        )


if __name__ == "__main__":
    validate_sheet("Labour - Usage - VCGS")
