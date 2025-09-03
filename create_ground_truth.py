import pandas as pd
from pathlib import Path

from unimelb_phd_phase_1.sheet_manager import SheetManager

def main():
    """
    Creates the ground_truth.parquet file from the "Detailed Table" sheet.
    """
    # Initialize the SheetManager to get the data
    sheet_manager = SheetManager()
    detailed_table_df = sheet_manager.get_data("Detailed Table")

    # Identify input and output columns
    output_cols = [col for col in detailed_table_df.columns if "Unit Cost" in str(col)]
    input_cols = [col for col in detailed_table_df.columns if col not in output_cols]

    # Create the ground truth DataFrame
    ground_truth_df = detailed_table_df[input_cols + output_cols]

    # Save the ground truth data
    prepared_dir = Path(__file__).resolve().parent / "data" / "prepared"
    prepared_dir.mkdir(exist_ok=True)
    ground_truth_path = prepared_dir / "ground_truth.parquet"
    ground_truth_df.to_parquet(ground_truth_path)
    print(f"Saved ground truth data to {ground_truth_path}")

if __name__ == "__main__":
    main()
