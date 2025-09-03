#!/usr/bin/env python3
"""
Script to fully validate the calculation engine following the workflow in agents.md.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager


def establish_ground_truth():
    """Establish ground truth by creating or verifying ground_truth.parquet."""
    print("Establishing ground truth...")
    
    data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
    ground_truth_path = data_dir / "ground_truth.parquet"
    
    if ground_truth_path.exists():
        print(f"Ground truth file already exists at {ground_truth_path}")
        df = pd.read_parquet(ground_truth_path)
        print(f"Loaded ground truth with {len(df)} rows and {len(df.columns)} columns")
        return df
    else:
        print("Ground truth file not found. Please run prepare_data.py first.")
        return None


def validate_engine():
    """Validate the calculation engine against ground truth data."""
    print("Validating calculation engine...")
    
    try:
        # Load the ground truth data
        ground_truth_path = "data/prepared/ground_truth.parquet"
        ground_truth_df = pd.read_parquet(ground_truth_path)
        print(f"Loaded ground truth data with {len(ground_truth_df)} rows")

        # Initialize the CalculationEngine
        sheet_manager = SheetManager()
        engine = CalculationEngine(sheet_manager)
        print("Initialized CalculationEngine")

        # Run the engine to get the calculated results
        print("Running calculation engine...")
        results_df, errors = engine.run_engine()

        if errors:
            print("Errors occurred during calculation:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

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
            return False

        # For ground truth, use the correct column name
        ground_truth_col = "Unit Cost (AUD $/unit) LL"
        
        if ground_truth_col not in ground_truth_df.columns:
            print(f"Could not find {ground_truth_col} in ground truth data")
            print("Available columns in ground truth:", [col for col in ground_truth_df.columns if 'Unit Cost' in str(col)])
            return False

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
            return False

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
            print(f"\nNumber of significant errors: {len(significant_errors)}")
        else:
            print("\nNo significant errors found (all differences < 0.01)")
        
        # Calculate accuracy metrics
        total_compared = len(comparison_df)
        exact_matches = len(comparison_df[comparison_df["difference"] == 0])
        small_errors = len(comparison_df[comparison_df["difference"].abs() <= 0.01])
        large_errors = len(significant_errors)
        
        print(f"\nAccuracy Metrics:")
        print(f"  Total values compared: {total_compared}")
        print(f"  Exact matches: {exact_matches} ({exact_matches/total_compared*100:.2f}%)")
        print(f"  Small errors (≤0.01): {small_errors} ({small_errors/total_compared*100:.2f}%)")
        print(f"  Large errors (>0.01): {large_errors} ({large_errors/total_compared*100:.2f}%)")
        
        # Calculate mean absolute error and root mean square error
        mae = comparison_df["difference"].abs().mean()
        rmse = np.sqrt((comparison_df["difference"] ** 2).mean())
        
        print(f"  Mean Absolute Error: {mae:.6f}")
        print(f"  Root Mean Square Error: {rmse:.6f}")
        
        # Success criteria: < 1% of values have large errors
        error_rate = large_errors / total_compared
        if error_rate < 0.01:
            print(f"\n✅ VALIDATION PASSED: Error rate {error_rate:.4f} < 0.01")
            return True
        else:
            print(f"\n❌ VALIDATION FAILED: Error rate {error_rate:.4f} >= 0.01")
            return False

    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to validate the calculation engine."""
    print("Calculation Engine Validation")
    print("=" * 40)
    
    # Step 1: Establish ground truth
    ground_truth = establish_ground_truth()
    if ground_truth is None:
        print("Cannot proceed without ground truth data.")
        return 1
    
    # Step 2: Validate the engine
    success = validate_engine()
    
    if success:
        print("\n🎉 Calculation engine validation completed successfully!")
        return 0
    else:
        print("\n❌ Calculation engine validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())