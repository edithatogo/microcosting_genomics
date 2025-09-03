import pandas as pd
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager


def main():
    """
    Validates the CalculationEngine against the ground truth data.
    """
    # Load the ground truth data
    ground_truth_path = "data/prepared/ground_truth.parquet"
    ground_truth_df = pd.read_parquet(ground_truth_path)

    # Initialize the CalculationEngine
    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)

    # Run the engine to get the calculated results
    results_df, errors = engine.run_engine()

    if errors:
        print("Errors occurred during calculation:")
        for error in errors:
            print(f"  - {error}")

    # Compare the results with the ground truth
    # Handle multi-level columns in results_df
    unit_cost_col = None
    for col in results_df.columns:
        if isinstance(col, tuple) and 'Unit Cost (AUD $/unit)' in str(col):
            unit_cost_col = col
            break
    
    if unit_cost_col is None:
        print("Could not find Unit Cost column in results")
        print("Available columns:", [col for col in results_df.columns if 'Unit Cost' in str(col)][:10])
        return

    # For ground truth, use the correct column name
    ground_truth_col = "Unit Cost (AUD $/unit) LL"
    
    if ground_truth_col not in ground_truth_df.columns:
        print(f"Could not find {ground_truth_col} in ground truth data")
        print("Available columns in ground truth:", [col for col in ground_truth_df.columns if 'Unit Cost' in str(col)])
        return

    # Extract the unit cost data from results (it's a DataFrame, not a Series)
    calculated_data = results_df[unit_cost_col]
    
    # If it's a DataFrame with one column, extract that column
    if isinstance(calculated_data, pd.DataFrame):
        # Get the first (and likely only) column from the DataFrame
        calculated_series = calculated_data.iloc[:, 0]
    else:
        calculated_series = calculated_data

    print(f"Ground truth data shape: {ground_truth_df[ground_truth_col].shape}")
    print(f"Calculated data shape: {calculated_series.shape}")
    
    # Check how many valid values we have
    valid_calculated = pd.to_numeric(calculated_series, errors='coerce')
    valid_ground_truth = pd.to_numeric(ground_truth_df[ground_truth_col], errors='coerce')
    
    print(f"Valid calculated values: {valid_calculated.notna().sum()}")
    print(f"Valid ground truth values: {valid_ground_truth.notna().sum()}")
    
    # Only compare where both values are valid
    comparison_mask = valid_calculated.notna() & valid_ground_truth.notna()
    print(f"Values that can be compared: {comparison_mask.sum()}")
    
    if comparison_mask.sum() == 0:
        print("No valid values to compare. This is expected if required sheets are not available.")
        return

    comparison_df = pd.DataFrame({
        "ground_truth": valid_ground_truth[comparison_mask],
        "calculated": valid_calculated[comparison_mask],
    })
    
    # Calculate differences
    comparison_df["difference"] = comparison_df["ground_truth"] - comparison_df["calculated"]
    comparison_df["percentage_error"] = (comparison_df["difference"] / comparison_df["ground_truth"]) * 100

    print("\nValidation Summary:")
    print(comparison_df.describe())

    # Identify and display significant errors
    significant_errors = comparison_df[comparison_df["difference"].abs() > 0.01]
    if not significant_errors.empty:
        print("\nSignificant Errors (difference > 0.01):")
        print(significant_errors)
    else:
        print("\nNo significant errors found (all differences < 0.01)")


if __name__ == "__main__":
    main()