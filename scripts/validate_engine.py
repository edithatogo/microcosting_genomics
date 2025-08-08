from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from unimelb_phd_phase_1.calculation_engine import CalculationEngine

PREPARED_DIR = Path(__file__).resolve().parents[0] / "data" / "prepared"
TOLERANCE = 1e-4


def _sheet_from_file(path: Path, workbook_path: str) -> str:
    """Return the workbook sheet name for a prepared parquet file."""
    stem = path.stem
    if stem == "ground_truth":
        return (
            "1. Detailed Table" if "Supp Tables" in workbook_path else "Detailed Table"
        )

    match = re.match(r"(\d+)\._(.+)", stem)
    if match:
        num, name = match.groups()
        clean = name.replace("_", " ").title()
        return f"{num}. {clean}"
    return stem


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten a DataFrame's columns to simple strings."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [
            " ".join(str(p) for p in tup if pd.notna(p)).strip() for tup in df.columns
        ]
    return df


def validate_engine() -> None:
    """Validate the calculation engine across all prepared tables."""
    workbook_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    print("Initializing CalculationEngine...")
    engine = CalculationEngine(workbook_path)

    # Ensure the R1 workbook sheet is loaded as '1. Detailed Table'
    if "Supp Tables" in workbook_path and "1. Detailed Table" not in engine.sheets:
        engine.sheet_configs["1. Detailed Table"] = engine.sheet_configs.pop(
            "Detailed Table"
        )
        engine._load_all_sheets()

    print("CalculationEngine initialized.")

    for parquet_path in sorted(PREPARED_DIR.glob("*.parquet")):
        if parquet_path.name.startswith("detailed_table_"):
            continue

        sheet_name = _sheet_from_file(parquet_path, workbook_path)
        if sheet_name not in engine.sheets:
            print(f"Sheet '{sheet_name}' not found in workbook, skipping")
            continue

        print(f"\n--- Validating table: {sheet_name} ---")
        ground_truth = pd.read_parquet(parquet_path)
        results, errors = engine.run_engine(sheet_name, fail_on_error=False)

        if errors:
            print(f"Encountered {len(errors)} calculation errors")

        ground_truth = _flatten_columns(ground_truth).reset_index(drop=True)
        results = _flatten_columns(results).reset_index(drop=True)

        common_cols = [c for c in ground_truth.columns if c in results.columns]
        gt = ground_truth[common_cols].select_dtypes("number")
        calc = results[common_cols].apply(pd.to_numeric, errors="coerce")

        gt, calc = gt.align(calc, join="inner", axis=1)
        diff = gt - calc
        abs_diff = diff.abs()

        total_cells = abs_diff.size
        mismatches = int((abs_diff > TOLERANCE).sum().sum())
        max_diff = abs_diff.max().max()
        mean_diff = abs_diff.mean().mean()

        print(f"Total cells compared: {total_cells}")
        print(f"Number of differences: {mismatches}")
        print(f"Maximum absolute difference: {max_diff}")
        print(f"Mean absolute difference: {mean_diff}")

        rows_with_diff = abs_diff.gt(TOLERANCE).any(axis=1)
        if rows_with_diff.any():
            print("Rows with significant differences:")
            combined = pd.concat(
                {
                    "expected": gt[rows_with_diff],
                    "calculated": calc[rows_with_diff],
                    "diff": diff[rows_with_diff],
                },
                axis=1,
            )
            print(combined)


if __name__ == "__main__":
    validate_engine()
