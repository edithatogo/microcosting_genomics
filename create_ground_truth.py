# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Extract prepared validation values from the detailed worksheet."""

import sys
from pathlib import Path

from genomics_microcosting.sheet_manager import SheetManager


def main() -> None:
    """Create the ground_truth.parquet file from the "Detailed Table" sheet."""
    # Initialize the SheetManager to get the data
    sheet_manager = SheetManager()
    detailed_table_df = sheet_manager.get_data("Detailed Table")

    if detailed_table_df is None:
        sys.stdout.writelines(("Error: Could not load Detailed Table data", "\n"))
        return

    # Identify input and output columns
    output_cols = [col for col in detailed_table_df.columns if "unit_cost" in str(col)]
    input_cols = [col for col in detailed_table_df.columns if col not in output_cols]

    # Create the ground truth DataFrame
    ground_truth_df = detailed_table_df[input_cols + output_cols]

    # Save the ground truth data
    prepared_dir = Path(__file__).resolve().parent / "data" / "prepared"
    prepared_dir.mkdir(exist_ok=True)
    ground_truth_path = prepared_dir / "ground_truth.parquet"
    ground_truth_df.to_parquet(ground_truth_path)
    sys.stdout.writelines((f"Saved ground truth data to {ground_truth_path}", "\n"))


if __name__ == "__main__":
    main()
