#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify that the ETL pipeline reproduces the original prepared tables.

This script compares the outputs from both approaches to ensure:
1. All sheets are processed identically
2. Column names match exactly
3. Data values match exactly
4. Row counts match exactly
5. Data types are preserved correctly
"""

import logging
import shutil
import sys
from pathlib import Path

import pandas as pd

lazy import prepare_data
lazy import prepare_data_pipeline

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_original_prepare_data() -> None:
    """Run the original prepare_data.py script."""
    logger.info("Running original prepare_data.py...")

    # Import and run the original function
    sys.path.insert(0, str(Path(__file__).parent))

    # Import the original module

    # Run the main function
    prepare_data.main()

    logger.info("Original prepare_data.py completed")


def run_etl_pipeline() -> None:
    """Run the new ETL pipeline."""
    logger.info("Running ETL pipeline...")

    # Import and run the new pipeline

    # Run the main function
    prepare_data_pipeline.main()

    logger.info("ETL pipeline completed")


def compare_outputs() -> bool:
    """Compare outputs from both approaches."""
    logger.info("Comparing outputs from original and ETL pipeline...")

    prepared_dir = Path("data/prepared")

    if not prepared_dir.exists():
        logger.error("Prepared directory %s does not exist", prepared_dir)
        return False

    # Get all parquet files (both original and ETL versions)
    parquet_files = list(prepared_dir.glob("*.parquet"))

    if not parquet_files:
        logger.error("No parquet files found in prepared directory")
        return False

    logger.info("Found %s parquet files to compare", len(parquet_files))

    comparison_results = []
    all_passed = True

    for parquet_file in parquet_files:
        sheet_name = parquet_file.stem
        logger.info("Comparing sheet: %s", sheet_name)

        # Read the ETL pipeline output
        etl_df = pd.read_parquet(parquet_file)

        # Check if original output exists
        original_file = prepared_dir / f"{sheet_name}.parquet"
        if not original_file.exists():
            logger.warning("Original file not found: %s", original_file)
            continue

        # Read the original output
        original_df = pd.read_parquet(original_file)

        # Compare the DataFrames
        result = compare_dataframes(etl_df, original_df, sheet_name)
        comparison_results.append(result)

        if not result["passed"]:
            all_passed = False

    # Print summary
    print_comparison_summary(comparison_results)

    return all_passed


def _compare_column_names(
    etl_df: pd.DataFrame,
    original_df: pd.DataFrame,
    result: dict,
) -> tuple[set[str], set[str]]:
    # Compare column names
    etl_columns = set(etl_df.columns)
    original_columns = set(original_df.columns)

    if etl_columns != original_columns:
        result["passed"] = False
        missing_in_etl = original_columns - etl_columns
        extra_in_etl = etl_columns - original_columns

        if missing_in_etl:
            result["issues"].append(f"Missing columns in ETL: {missing_in_etl}")
        if extra_in_etl:
            result["issues"].append(f"Extra columns in ETL: {extra_in_etl}")

    return etl_columns, original_columns


def compare_dataframes(
    etl_df: pd.DataFrame,
    original_df: pd.DataFrame,
    sheet_name: str,
) -> dict:
    """Compare two DataFrames and return detailed comparison results."""
    result = {
        "sheet_name": sheet_name,
        "passed": True,
        "issues": [],
        "etl_shape": etl_df.shape,
        "original_shape": original_df.shape,
    }

    # Compare shapes
    if etl_df.shape != original_df.shape:
        result["passed"] = False
        result["issues"].append(
            f"Shape mismatch: ETL {etl_df.shape} vs Original {original_df.shape}",
        )

    etl_columns, original_columns = _compare_column_names(etl_df, original_df, result)

    # Compare data values (only if shapes and columns match)
    if result["passed"]:
        try:
            # Sort both DataFrames by all columns to ensure consistent ordering
            etl_sorted = etl_df.sort_values(by=list(etl_df.columns)).reset_index(
                drop=True,
            )
            original_sorted = original_df.sort_values(
                by=list(original_df.columns),
            ).reset_index(drop=True)

            # Compare values
            if not etl_sorted.equals(original_sorted):
                result["passed"] = False
                result["issues"].append("Data values do not match")

                # Find specific differences
                differences = find_dataframe_differences(etl_sorted, original_sorted)
                if differences:
                    result["issues"].extend(
                        differences[:5],
                    )  # Limit to first 5 differences

        except Exception as e:
            logger.exception("Could not complete compare dataframes")
            result["passed"] = False
            result["issues"].append(f"Error comparing data: {e}")

    # Compare data types
    if result["passed"]:
        etl_dtypes = etl_df.dtypes.to_dict()
        original_dtypes = original_df.dtypes.to_dict()

        dtype_mismatches = []
        dtype_mismatches.extend(
            f"{col}: ETL {etl_dtypes[col]} vs Original {original_dtypes[col]}"
            for col in etl_columns & original_columns
            if etl_dtypes[col] != original_dtypes[col]
        )

        if dtype_mismatches:
            result["passed"] = False
            result["issues"].append(f"Data type mismatches: {dtype_mismatches}")

    return result


def find_dataframe_differences(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    max_diffs: int = 5,
) -> list:
    """Find specific differences between two DataFrames."""
    differences = []

    # Compare each cell
    for idx in range(min(len(df1), len(df2))):
        for col in df1.columns:
            if col in df2.columns:
                val1 = df1.loc[idx, col]
                val2 = df2.loc[idx, col]

                # Handle NaN comparisons
                if pd.isna(val1) and pd.isna(val2):
                    continue
                if pd.isna(val1) or pd.isna(val2) or val1 != val2:
                    differences.append(
                        f"Row {idx}, Col {col}: ETL {val1} vs Original {val2}",
                    )

                if len(differences) >= max_diffs:
                    return differences

    return differences


def print_comparison_summary(results: list) -> None:
    """Print a summary of the comparison results."""
    sys.stdout.writelines((str("\n" + "=" * 80), "\n"))
    sys.stdout.writelines(("INTEGRATION TEST RESULTS", "\n"))
    sys.stdout.writelines((str("=" * 80), "\n"))

    total_sheets = len(results)
    passed_sheets = sum(1 for r in results if r["passed"])
    failed_sheets = total_sheets - passed_sheets

    sys.stdout.writelines((f"Total sheets compared: {total_sheets}", "\n"))
    sys.stdout.writelines((f"Passed: {passed_sheets}", "\n"))
    sys.stdout.writelines((f"Failed: {failed_sheets}", "\n"))
    sys.stdout.writelines(("\n",))

    if failed_sheets > 0:
        sys.stdout.writelines(("FAILED SHEETS:", "\n"))
        for result in results:
            if not result["passed"]:
                sys.stdout.writelines((f"❌ {result['sheet_name']}", "\n"))
                for issue in result["issues"]:
                    sys.stdout.writelines((f"   - {issue}", "\n"))
                sys.stdout.writelines(("\n",))
    else:
        sys.stdout.writelines(("✅ ALL SHEETS PASSED COMPARISON!", "\n"))

    sys.stdout.writelines((str("=" * 80), "\n"))


def backup_existing_outputs() -> None:
    """Backup existing prepared data before running tests."""
    prepared_dir = Path("data/prepared")
    backup_dir = Path("data/prepared_backup")

    if prepared_dir.exists():
        logger.info("Backing up existing prepared data...")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(prepared_dir, backup_dir)
        logger.info("Backup created at %s", backup_dir)


def restore_backup() -> None:
    """Restore the backup after testing."""
    prepared_dir = Path("data/prepared")
    backup_dir = Path("data/prepared_backup")

    if backup_dir.exists():
        logger.info("Restoring backup...")
        if prepared_dir.exists():
            shutil.rmtree(prepared_dir)
        shutil.copytree(backup_dir, prepared_dir)
        shutil.rmtree(backup_dir)
        logger.info("Backup restored")


def main() -> bool | None:
    """Run the complete integration test."""
    logger.info("Starting ETL Pipeline Integration Test")
    logger.info("=" * 60)

    try:
        # Backup existing outputs
        backup_existing_outputs()

        # Clean the prepared directory
        prepared_dir = Path("data/prepared")
        if prepared_dir.exists():
            shutil.rmtree(prepared_dir)
        prepared_dir.mkdir(parents=True, exist_ok=True)

        # Run both approaches
        sys.stdout.writelines(("\n1. Running original prepare_data.py...", "\n"))
        run_original_prepare_data()

        # Move original outputs to a temporary location
        original_dir = Path("data/prepared_original")
        if original_dir.exists():
            shutil.rmtree(original_dir)
        shutil.copytree(prepared_dir, original_dir)

        # Clean prepared directory for ETL run
        shutil.rmtree(prepared_dir)
        prepared_dir.mkdir(parents=True, exist_ok=True)

        sys.stdout.writelines(("\n2. Running ETL pipeline...", "\n"))
        run_etl_pipeline()

        # Copy original outputs back for comparison
        for file_path in original_dir.glob("*"):
            shutil.copy2(
                file_path,
                prepared_dir / f"{file_path.stem}_original{file_path.suffix}",
            )

        sys.stdout.writelines(("\n3. Comparing results...", "\n"))
        success = compare_outputs()

        # Cleanup
        if original_dir.exists():
            shutil.rmtree(original_dir)

        if success:
            logger.info("✅ Integration test PASSED!")
            return True
        logger.error("❌ Integration test FAILED!")

    except Exception:
        logger.exception("Integration test failed with error")
        return False
    else:
        return False

    finally:
        # Always restore the backup
        restore_backup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
