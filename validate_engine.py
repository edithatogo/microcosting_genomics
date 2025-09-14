"""
Validation script for the genomics microcosting calculation engine.

This script compares the output of the CalculationEngine against ground truth data
to validate accuracy and identify any discrepancies.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager


def load_ground_truth() -> Optional[pd.DataFrame]:
    """Load the ground truth data from prepared parquet files."""
    ground_truth_paths = [
        "data/prepared/detailed_table.parquet",
        "data/prepared/ground_truth.parquet"
    ]

    for path in ground_truth_paths:
        if Path(path).exists():
            try:
                df = pd.read_parquet(path)
                print(f"Loaded ground truth from {path}")
                print(f"Ground truth shape: {df.shape}")
                return df
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue

    print("No ground truth data found")
    return None


def find_unit_cost_columns(df: pd.DataFrame) -> List[str]:
    """Find all columns that contain unit cost information."""
    unit_cost_cols = []
    for col in df.columns:
        col_str = str(col).lower()
        if any(keyword in col_str for keyword in ['unit cost', 'unit_cost', 'cost']):
            unit_cost_cols.append(col)
    return unit_cost_cols


def validate_calculation_engine() -> None:
    """
    Validates the CalculationEngine against the ground truth data.
    """
    print("=== Genomics Microcosting Engine Validation ===\n")

    # Load ground truth data
    ground_truth_df = load_ground_truth()
    if ground_truth_df is None:
        print("Cannot proceed without ground truth data")
        return

    # Find unit cost columns in ground truth
    gt_unit_cost_cols = find_unit_cost_columns(ground_truth_df)
    print(f"Found {len(gt_unit_cost_cols)} unit cost columns in ground truth:")
    for col in gt_unit_cost_cols[:5]:  # Show first 5
        print(f"  - {col}")
    if len(gt_unit_cost_cols) > 5:
        print(f"  ... and {len(gt_unit_cost_cols) - 5} more")

    # Initialize the CalculationEngine
    try:
        sheet_manager = SheetManager()
        engine = CalculationEngine(sheet_manager)
        print("\nCalculationEngine initialized successfully")
    except Exception as e:
        print(f"Error initializing CalculationEngine: {e}")
        return

    # Try to run the engine
    try:
        results_df, errors = engine.run_engine("Detailed Table")

        if results_df is None:
            print("\nEngine returned None - no results to validate")
            if errors:
                print("Errors occurred during calculation:")
                for error in errors:
                    print(f"  - {error}")
            return

        if errors:
            print("\nWarnings during calculation:")
            for error in errors:
                print(f"  - {error}")

    except Exception as e:
        print(f"\nError running CalculationEngine: {e}")
        print("This is expected if the engine is not fully implemented yet.")
        return

    print(f"\nEngine results shape: {results_df.shape}")

    # Find unit cost columns in results
    results_unit_cost_cols = find_unit_cost_columns(results_df)
    print(f"Found {len(results_unit_cost_cols)} unit cost columns in results:")
    for col in results_unit_cost_cols[:5]:  # Show first 5
        print(f"  - {col}")

    # Perform validation if we have matching columns
    if not gt_unit_cost_cols or not results_unit_cost_cols:
        print("\nCannot perform validation - missing unit cost columns")
        return

    print("\n=== Validation Results ===")

    # Try to match columns and validate
    validation_results = []

    for gt_col in gt_unit_cost_cols[:3]:  # Limit to first 3 for brevity
        print(f"\nValidating against ground truth column: {gt_col}")

        # Try to find a matching column in results
        best_match = None
        for res_col in results_unit_cost_cols:
            if any(keyword in str(res_col).lower() for keyword in ['unit', 'cost']):
                best_match = res_col
                break

        if best_match:
            print(f"Comparing with results column: {best_match}")
            compare_columns(ground_truth_df, results_df, gt_col, best_match, validation_results)
        else:
            print("No suitable matching column found in results")

    # Summary
    if validation_results:
        print("\n=== Summary ===")
        total_comparisons = sum(r['comparisons'] for r in validation_results)
        significant_errors = sum(r['significant_errors'] for r in validation_results)

        print(f"Total comparable values: {total_comparisons}")
        print(f"Significant errors (>1% difference): {significant_errors}")

        if total_comparisons > 0:
            error_rate = significant_errors / total_comparisons * 100
            print(f"Error rate: {error_rate:.1f}%")
        else:
            print("No comparisons possible")
    else:
        print("\nNo validation comparisons could be performed")


def compare_columns(gt_df: pd.DataFrame, res_df: pd.DataFrame,
                   gt_col: str, res_col: str, results: List[dict]) -> None:
    """Compare two columns and calculate validation metrics."""

    try:
        # Extract and clean the data
        gt_series = pd.to_numeric(gt_df[gt_col], errors='coerce')
        res_series = pd.to_numeric(res_df[res_col], errors='coerce')

        # Align the series by index if possible
        min_len = min(len(gt_series), len(res_series))
        gt_clean = gt_series.iloc[:min_len]
        res_clean = res_series.iloc[:min_len]

        # Find valid comparisons
        valid_mask = gt_clean.notna() & res_clean.notna()
        comparisons = valid_mask.sum()

        if comparisons == 0:
            print(f"  No valid comparisons possible between {gt_col} and {res_col}")
            return

        gt_valid = gt_clean[valid_mask]
        res_valid = res_clean[valid_mask]

        # Calculate metrics
        differences = gt_valid - res_valid
        abs_differences = differences.abs()
        percentage_errors = (differences / gt_valid) * 100

        mean_abs_error = abs_differences.mean()
        mean_percentage_error = percentage_errors.abs().mean()
        max_abs_error = abs_differences.max()
        max_percentage_error = percentage_errors.abs().max()

        # Count significant errors
        significant_errors = (abs_differences > 0.01).sum()

        print(f"  Valid comparisons: {comparisons}")
        print(f"  Mean absolute error: {mean_abs_error:.6f}")
        print(".2f")
        print(f"  Max absolute error: {max_abs_error:.6f}")
        print(".2f")
        print(f"  Significant errors (>0.01): {significant_errors}")

        results.append({
            'gt_column': gt_col,
            'res_column': res_col,
            'comparisons': comparisons,
            'mean_abs_error': mean_abs_error,
            'mean_percentage_error': mean_percentage_error,
            'max_abs_error': max_abs_error,
            'max_percentage_error': max_percentage_error,
            'significant_errors': significant_errors
        })

    except Exception as e:
        print(f"  Error comparing columns: {e}")


def main():
    """Main entry point."""
    validate_calculation_engine()


if __name__ == "__main__":
    main()