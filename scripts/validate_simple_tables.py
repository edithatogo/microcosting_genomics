# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check calculated values for supporting workbook tables."""

import sys
from pathlib import Path

import pandas as pd

from genomics_microcosting.calculation_engine import CalculationEngine

NUMERIC_COMPARISON_TOLERANCE = 1e-6


def validate_simple_tables() -> None:
    """Validate simple reference tables using CalculationEngine."""
    engine = CalculationEngine()

    data_dir = Path(__file__).resolve().parents[0] / "data" / "prepared"
    tables = {
        "2. Labor Prices": data_dir / "2._labor_prices.parquet",
        "3. Estimates": data_dir / "3._estimates.parquet",
    }

    for sheet_name, parquet_path in tables.items():
        sys.stdout.write(f"\n--- Validating {sheet_name} ---" + "\n")
        ground_truth = pd.read_parquet(parquet_path)

        results, errors = engine.run_engine(sheet_name, fail_on_error=False)
        if errors:
            sys.stdout.write("Errors while computing formulas:" + "\n")
            for e in errors:
                sys.stdout.write(str(e) + "\n")

        gt_aligned, res_aligned = ground_truth.align(results, join="inner", axis=1)
        diff = (gt_aligned - res_aligned).abs()

        sys.stdout.write(f"Total cells compared: {diff.size}" + "\n")
        sys.stdout.write(
            "Number of differences: "
            f"{(diff > NUMERIC_COMPARISON_TOLERANCE).sum().sum()}"
            "\n",
        )
        sys.stdout.write(f"Maximum absolute difference: {diff.max().max()}" + "\n")
        sys.stdout.write(f"Mean absolute difference: {diff.mean().mean()}" + "\n")


if __name__ == "__main__":
    validate_simple_tables()
