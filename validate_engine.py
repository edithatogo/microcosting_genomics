import pandas as pd
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

def validate_engine():
    """
    Validates the CalculationEngine against the ground truth data.
    """
    print("Initializing CalculationEngine...")

    # Path to the Excel workbook used for validation. The R1 workbook (Nov 2023)
    # uses a sheet named ``"1. Detailed Table"`` while earlier versions simply
    # use ``"Detailed Table"``.
    workbook_path = (
        "data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx"
    )

    # Determine the correct sheet name based on the workbook being used.
    sheet_name = (
        "1. Detailed Table"
        if "Supp Tables" in workbook_path
        else "Detailed Table"
    )

    engine = CalculationEngine(workbook_path)

    # Update the CalculationEngine configuration if the workbook uses the
    # ``"1. Detailed Table"`` sheet name.
    if sheet_name != "Detailed Table":
        engine.sheet_configs[sheet_name] = engine.sheet_configs.pop("Detailed Table")

    print("CalculationEngine initialized.")

    print("Loading ground truth data from Parquet file...")
    ground_truth_path = "data/prepared/ground_truth.parquet"
    ground_truth_df = pd.read_parquet(ground_truth_path)
    print("Ground truth data loaded.")

    print("Running calculation engine...")
    results_df, errors = engine.run_engine(sheet_name, fail_on_error=False)
    print("Calculation engine finished.")

    if errors:
        print("\n--- Calculation Errors ---")
        for error in errors:
            print(f"Cell: {error['cell']}, Formula: {error['formula']}, Error: {error['error']}")
        print("--------------------------\n")

    # Extract the 'Unit Cost (AUD $/test)' columns for comparison
    ground_truth_costs = ground_truth_df.xs('Unit Cost (AUD $/test)', level=0, axis=1)
    calculated_costs = results_df.xs('Unit Cost (AUD $/test)', level=0, axis=1)

    # Align the dataframes to ensure comparison is correct
    ground_truth_costs, calculated_costs = ground_truth_costs.align(calculated_costs, join='inner', axis=0)

    # Calculate the difference
    diff = ground_truth_costs - calculated_costs
    abs_diff = diff.abs()

    # Summary of differences
    print("\nValidation Summary:")
    print("===================")
    print(f"Total cells compared: {abs_diff.size}")
    print(f"Number of differences: {abs_diff[abs_diff > 0.0001].count().sum()}")
    print(f"Maximum absolute difference: {abs_diff.max().max()}")
    print(f"Mean absolute difference: {abs_diff.mean().mean()}")

    # Display rows with significant differences
    significant_diffs = abs_diff[abs_diff > 0.0001].any(axis=1)
    if significant_diffs.any():
        print("\nRows with significant differences:")
        print(ground_truth_df[significant_diffs])
        print(results_df[significant_diffs])
        print(diff[significant_diffs])

if __name__ == "__main__":
    validate_engine()
