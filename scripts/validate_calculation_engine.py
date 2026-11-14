#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Compare the calculation engine with the prepared detailed table."""

import logging
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

logger = logging.getLogger(__name__)

ERROR_PREVIEW_LIMIT = 10
COST_COMPARISON_TOLERANCE = 0.01
ACCEPTABLE_ERROR_RATE = 0.01


def establish_ground_truth() -> pd.DataFrame | None:
    """Establish ground truth by creating or verifying ground_truth.parquet."""
    sys.stdout.write("Establishing ground truth..." + "\n")

    data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
    ground_truth_path = data_dir / "ground_truth.parquet"

    if ground_truth_path.exists():
        sys.stdout.write(
            f"Ground truth file already exists at {ground_truth_path}" + "\n",
        )
        df = pd.read_parquet(ground_truth_path)
        sys.stdout.write(
            f"Loaded ground truth with {len(df)} rows and {len(df.columns)} columns\n",
        )
        return df
    sys.stdout.write(
        "Ground truth file not found. Please run prepare_data.py first." + "\n",
    )
    return None


def _print_significant_errors(comparison_df: pd.DataFrame) -> pd.DataFrame:
    # Identify and display significant errors
    significant_errors = comparison_df[
        comparison_df["difference"].abs() > COST_COMPARISON_TOLERANCE
    ]
    if not significant_errors.empty:
        sys.stdout.write("\nSignificant Errors (difference > 0.01):" + "\n")
        sys.stdout.write(str(significant_errors) + "\n")
        sys.stdout.write(
            f"\nNumber of significant errors: {len(significant_errors)}" + "\n",
        )
    else:
        sys.stdout.write(
            "\nNo significant errors found (all differences < 0.01)" + "\n",
        )

    return significant_errors


def _compare_unit_costs(
    results_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
) -> bool | None:
    # Compare the results with the ground truth
    # Handle multi-level columns in results_df
    unit_cost_col = None
    for col in results_df.columns:
        if isinstance(col, tuple) and "Unit Cost (AUD $/unit)" in str(col):
            unit_cost_col = col
            break

    if unit_cost_col is None:
        sys.stdout.write("Could not find Unit Cost column in results" + "\n")
        sys.stdout.write(
            " ".join(
                (
                    "Available columns:",
                    str(
                        [col for col in results_df.columns if "Unit Cost" in str(col)][
                            :10
                        ],
                    ),
                ),
            )
            + "\n",
        )
        return False

    # For ground truth, use the correct column name
    ground_truth_col = "Unit Cost (AUD $/unit) LL"

    if ground_truth_col not in ground_truth_df.columns:
        sys.stdout.write(
            f"Could not find {ground_truth_col} in ground truth data" + "\n",
        )
        sys.stdout.write(
            " ".join(
                (
                    "Available columns in ground truth:",
                    str(
                        [
                            col
                            for col in ground_truth_df.columns
                            if "Unit Cost" in str(col)
                        ],
                    ),
                ),
            )
            + "\n",
        )
        return False

    # Extract the unit cost data from results (it's a DataFrame, not a Series)
    calculated_data = results_df[unit_cost_col]

    # If it's a DataFrame with one column, extract that column
    if isinstance(calculated_data, pd.DataFrame):
        # Get the first (and likely only) column from the DataFrame
        calculated_series = calculated_data.iloc[:, 0]
    else:
        calculated_series = calculated_data

    sys.stdout.write(
        f"Ground truth data shape: {ground_truth_df[ground_truth_col].shape}\n",
    )
    sys.stdout.write(f"Calculated data shape: {calculated_series.shape}" + "\n")

    # Check how many valid values we have
    valid_calculated = pd.to_numeric(calculated_series, errors="coerce")
    valid_ground_truth = pd.to_numeric(
        ground_truth_df[ground_truth_col],
        errors="coerce",
    )

    sys.stdout.write(
        f"Valid calculated values: {valid_calculated.notna().sum()}" + "\n",
    )
    sys.stdout.write(
        f"Valid ground truth values: {valid_ground_truth.notna().sum()}" + "\n",
    )

    # Only compare where both values are valid
    comparison_mask = valid_calculated.notna() & valid_ground_truth.notna()
    sys.stdout.write(f"Values that can be compared: {comparison_mask.sum()}" + "\n")

    if comparison_mask.sum() == 0:
        sys.stdout.write(
            "No valid values to compare. This is expected if required "
            "sheets are not available."
            "\n",
        )
        return False

    comparison_df = pd.DataFrame(
        {
            "ground_truth": valid_ground_truth[comparison_mask],
            "calculated": valid_calculated[comparison_mask],
        },
    )

    # Calculate differences
    comparison_df["difference"] = (
        comparison_df["ground_truth"] - comparison_df["calculated"]
    )
    comparison_df["percentage_error"] = (
        comparison_df["difference"] / comparison_df["ground_truth"]
    ) * 100

    sys.stdout.write("\nValidation Summary:" + "\n")
    sys.stdout.write(str(comparison_df.describe()) + "\n")

    significant_errors = _print_significant_errors(comparison_df)

    # Calculate accuracy metrics
    total_compared = len(comparison_df)
    exact_matches = len(comparison_df[comparison_df["difference"] == 0])
    small_errors = len(
        comparison_df[comparison_df["difference"].abs() <= COST_COMPARISON_TOLERANCE],
    )
    large_errors = len(significant_errors)

    sys.stdout.write("\nAccuracy Metrics:" + "\n")
    sys.stdout.write(f"  Total values compared: {total_compared}" + "\n")
    sys.stdout.write(
        f"  Exact matches: {exact_matches} ("
        f"{exact_matches / total_compared * 100:.2f}%)"
        "\n",
    )
    sys.stdout.write(
        f"  Small errors (\u22640.01): {small_errors} ("
        f"{small_errors / total_compared * 100:.2f}%)"
        "\n",
    )
    sys.stdout.write(
        f"  Large errors (>0.01): {large_errors} ("
        f"{large_errors / total_compared * 100:.2f}%)"
        "\n",
    )

    # Calculate mean absolute error and root mean square error
    mae = comparison_df["difference"].abs().mean()
    rmse = np.sqrt((comparison_df["difference"] ** 2).mean())

    sys.stdout.write(f"  Mean Absolute Error: {mae:.6f}" + "\n")
    sys.stdout.write(f"  Root Mean Square Error: {rmse:.6f}" + "\n")

    # Success criteria: < 1% of values have large errors
    error_rate = large_errors / total_compared
    if error_rate < ACCEPTABLE_ERROR_RATE:
        sys.stdout.write(
            f"\n✅ VALIDATION PASSED: Error rate {error_rate:.4f} < 0.01" + "\n",
        )
        return True
    sys.stdout.write(
        f"\n❌ VALIDATION FAILED: Error rate {error_rate:.4f} >= 0.01" + "\n",
    )
    return None


def validate_engine() -> bool | None:
    """Validate the calculation engine against ground truth data."""
    sys.stdout.write("Validating calculation engine..." + "\n")

    try:
        # Load the ground truth data
        ground_truth_path = "data/prepared/ground_truth.parquet"
        ground_truth_df = pd.read_parquet(ground_truth_path)
        sys.stdout.write(
            f"Loaded ground truth data with {len(ground_truth_df)} rows" + "\n",
        )

        # Initialize the CalculationEngine
        sheet_manager = SheetManager()
        engine = CalculationEngine(sheet_manager)
        sys.stdout.write("Initialized CalculationEngine" + "\n")

        # Run the engine to get the calculated results
        sys.stdout.write("Running calculation engine..." + "\n")
        results_df, errors = engine.run_engine("Detailed Table")

        if errors:
            sys.stdout.write("Errors occurred during calculation:" + "\n")
            for error in errors[:10]:  # Show first 10 errors
                sys.stdout.write(f"  - {error}" + "\n")
            if len(errors) > ERROR_PREVIEW_LIMIT:
                sys.stdout.write(f"  ... and {len(errors) - 10} more errors" + "\n")

        return _compare_unit_costs(results_df, ground_truth_df)

    except Exception as e:
        logger.exception("Could not complete validate engine")
        sys.stdout.write(f"Error during validation: {e}" + "\n")

        traceback.print_exc()
        return False
    else:
        return False


def main() -> int:
    """Validate the calculation engine."""
    sys.stdout.write("Calculation Engine Validation" + "\n")
    sys.stdout.write(str("=" * 40) + "\n")

    # Step 1: Establish ground truth
    ground_truth = establish_ground_truth()
    if ground_truth is None:
        sys.stdout.write("Cannot proceed without ground truth data." + "\n")
        return 1

    # Step 2: Validate the engine
    success = validate_engine()

    if success:
        sys.stdout.write(
            "\n🎉 Calculation engine validation completed successfully!" + "\n",
        )
        return 0
    sys.stdout.write("\n❌ Calculation engine validation failed!" + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
