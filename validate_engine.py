import pandas as pd
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager
from unimelb_phd_phase_1.config import load_config

def validate_engine():
    """
    Validates the CalculationEngine against the ground truth data.
    """
    print("Initializing CalculationEngine...")

    config = load_config()
    workbook_key = "validation"
    try:
        workbook_path = config["workbooks"][workbook_key]["path"]
        sheet_name = next(iter(config["workbooks"][workbook_key]["sheets"]))
    except (KeyError, StopIteration) as e:
        raise KeyError(f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}") from e

    sheet_manager = SheetManager(workbook_path)
    engine = CalculationEngine(sheet_manager=sheet_manager)

    print("CalculationEngine initialized.")

    print("Loading ground truth data from Parquet file...")
    sanitized_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '_')).rstrip()
    sanitized_name = sanitized_name.lower().replace(' ', '_')
    ground_truth_path = f"data/prepared/{sanitized_name}.parquet"
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

    # To ensure comparable columns, flatten any MultiIndex to a single level.
    if isinstance(ground_truth_df.columns, pd.MultiIndex):
        ground_truth_df.columns = [' '.join(map(str, col)).strip().replace('nan ', '') for col in ground_truth_df.columns.values]
    if isinstance(results_df.columns, pd.MultiIndex):
        results_df.columns = [' '.join(map(str, col)).strip().replace('nan ', '') for col in results_df.columns.values]

    # Extract the 'Unit Cost (AUD $/test)' columns for comparison from flattened dataframes.
    ground_truth_costs = ground_truth_df.filter(like='Unit Cost (AUD $/test)', axis=1)
    calculated_costs = results_df.filter(like='Unit Cost (AUD $/test)', axis=1)

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
