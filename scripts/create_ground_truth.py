# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Create ground truth dataset for Phase 4 validation.

Extract input and calculated unit cost columns from the detailed table.
to create an immutable ground truth dataset for validation purposes.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_ground_truth_dataset() -> pd.DataFrame:
    """Create ground truth dataset from detailed table."""
    # Load the detailed table
    detailed_path = Path("data/prepared/detailed_table.parquet")
    if not detailed_path.exists():
        message = f"Detailed table not found at {detailed_path}"
        raise FileNotFoundError(message)

    logger.info("Loading detailed table...")
    df = pd.read_parquet(detailed_path)
    logger.info("Loaded %s rows with %s columns", len(df), len(df.columns))

    # Define input and output columns based on analysis
    input_columns = [
        "Estimates Quantity of Use per Test LL LL",
        "Price (AUD $/unit) LL LL",
        "Estimate Estimate",  # Lower estimate
        "UL UL",  # Upper estimate
        "DSA DSA LL SA",  # DSA cost
        "LL NSW",  # NSW cost
        "LL QLD",  # QLD cost
        "LL WA",  # WA cost
    ]

    output_columns = [
        "Unit Cost (AUD $/unit) LL LL",
        "Estimate Estimate_3",  # Unit cost estimate
        "UL UL_3",  # Unit cost upper limit
    ]

    # Add descriptive columns
    descriptive_columns = [
        "Test Test Test",
        "Category Category Category",
        "Sub-Category Sub-Category Sub-Category",
        "Step Step Step",
    ]

    # Combine all columns we want to keep
    all_columns = descriptive_columns + input_columns + output_columns

    # Filter to only existing columns
    available_columns = [col for col in all_columns if col in df.columns]
    missing_columns = [col for col in all_columns if col not in df.columns]

    if missing_columns:
        logger.warning("Missing columns: %s", missing_columns)

    logger.info("Using %s columns: %s", len(available_columns), available_columns)

    # Create ground truth dataset
    ground_truth = df[available_columns].copy()

    # Filter to rows that have meaningful data (not all NaN in key columns)
    key_data_columns = input_columns + output_columns
    available_key_columns = [col for col in key_data_columns if col in df.columns]

    # Keep rows that have at least some data in key columns
    meaningful_rows = ground_truth[available_key_columns].notna().any(axis=1)
    ground_truth = ground_truth[meaningful_rows]

    logger.info(
        "Ground truth dataset: %s rows with %s columns",
        len(ground_truth),
        len(ground_truth.columns),
    )

    # Create output directory
    output_dir = Path("data/ground_truth")
    output_dir.mkdir(exist_ok=True)

    # Save as parquet (immutable format)
    output_path = output_dir / "ground_truth.parquet"
    ground_truth.to_parquet(output_path)
    logger.info("Saved ground truth dataset to %s", output_path)

    # Also save as CSV for easier inspection
    csv_path = output_dir / "ground_truth.csv"
    ground_truth.to_csv(csv_path, index=False)
    logger.info("Saved ground truth dataset to %s", csv_path)

    # Print summary statistics
    sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
    sys.stdout.writelines(("GROUND TRUTH DATASET SUMMARY", "\n"))
    sys.stdout.writelines((str("=" * 60), "\n"))
    sys.stdout.writelines((f"Total rows: {len(ground_truth)}", "\n"))
    sys.stdout.writelines((f"Total columns: {len(ground_truth.columns)}", "\n"))

    sys.stdout.writelines((f"\nDescriptive columns: {len(descriptive_columns)}", "\n"))
    sys.stdout.writelines(
        (
            (
                "Input columns: "
                f"{len([col for col in input_columns if col in ground_truth.columns])}"
            ),
            "\n",
        ),
    )
    sys.stdout.writelines(
        (
            (
                "Output columns: "
                f"{len([col for col in output_columns if col in ground_truth.columns])}"
            ),
            "\n",
        ),
    )

    sys.stdout.writelines(("\nData completeness:", "\n"))
    for col in available_key_columns:
        if col in ground_truth.columns:
            non_null = ground_truth[col].notna().sum()
            sys.stdout.writelines(
                (
                    (
                        f"  {col}: {non_null}/{len(ground_truth)} ("
                        f"{non_null / len(ground_truth) * 100:.1f}%)"
                    ),
                    "\n",
                ),
            )

    sys.stdout.writelines(("\nFiles saved:", "\n"))
    sys.stdout.writelines((f"  - {output_path}", "\n"))
    sys.stdout.writelines((f"  - {csv_path}", "\n"))

    return ground_truth


if __name__ == "__main__":
    create_ground_truth_dataset()
