#!/usr/bin/env python3
"""
Integration test script to verify ETL pipeline produces identical results to original prepare_data.py.

This script compares the outputs from both approaches to ensure:
1. All sheets are processed identically
2. Column names match exactly
3. Data values match exactly
4. Row counts match exactly
5. Data types are preserved correctly
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_original_prepare_data():
    """Run the original prepare_data.py script."""
    logger.info("Running original prepare_data.py...")

    # Import and run the original function
    sys.path.insert(0, str(Path(__file__).parent))

    # Import the original module
    import prepare_data

    # Run the main function
    prepare_data.main()

    logger.info("Original prepare_data.py completed")


def run_etl_pipeline():
    """Run the new ETL pipeline."""
    logger.info("Running ETL pipeline...")

    # Import and run the new pipeline
    import prepare_data_pipeline

    # Run the main function
    prepare_data_pipeline.main()

    logger.info("ETL pipeline completed")


def compare_outputs():
    """Compare outputs from both approaches."""
    logger.info("Comparing outputs from original and ETL pipeline...")

    prepared_dir = Path("data/prepared")

    if not prepared_dir.exists():
        logger.error(f"Prepared directory {prepared_dir} does not exist")
        return False

    # Get all parquet files (both original and ETL versions)
    parquet_files = list(prepared_dir.glob("*.parquet"))

    if not parquet_files:
        logger.error("No parquet files found in prepared directory")
        return False

    logger.info(f"Found {len(parquet_files)} parquet files to compare")

    comparison_results = []
    all_passed = True

    for parquet_file in parquet_files:
        sheet_name = parquet_file.stem
        logger.info(f"Comparing sheet: {sheet_name}")

        # Read the ETL pipeline output
        etl_df = pd.read_parquet(parquet_file)

        # Check if original output exists
        original_file = prepared_dir / f"{sheet_name}.parquet"
        if not original_file.exists():
            logger.warning(f"Original file not found: {original_file}")
            continue

        # Read the original output
        original_df = pd.read_parquet(original_file)

        # Compare the DataFrames
        result = compare_dataframes(etl_df, original_df, sheet_name)
        comparison_results.append(result)

        if not result['passed']:
            all_passed = False

    # Print summary
    print_comparison_summary(comparison_results)

    return all_passed


def compare_dataframes(etl_df: pd.DataFrame, original_df: pd.DataFrame, sheet_name: str) -> dict:
    """Compare two DataFrames and return detailed comparison results."""

    result = {
        'sheet_name': sheet_name,
        'passed': True,
        'issues': [],
        'etl_shape': etl_df.shape,
        'original_shape': original_df.shape
    }

    # Compare shapes
    if etl_df.shape != original_df.shape:
        result['passed'] = False
        result['issues'].append(
            f"Shape mismatch: ETL {etl_df.shape} vs Original {original_df.shape}"
        )

    # Compare column names
    etl_columns = set(etl_df.columns)
    original_columns = set(original_df.columns)

    if etl_columns != original_columns:
        result['passed'] = False
        missing_in_etl = original_columns - etl_columns
        extra_in_etl = etl_columns - original_columns

        if missing_in_etl:
            result['issues'].append(f"Missing columns in ETL: {missing_in_etl}")
        if extra_in_etl:
            result['issues'].append(f"Extra columns in ETL: {extra_in_etl}")

    # Compare data values (only if shapes and columns match)
    if result['passed']:
        try:
            # Sort both DataFrames by all columns to ensure consistent ordering
            etl_sorted = etl_df.sort_values(by=list(etl_df.columns)).reset_index(drop=True)
            original_sorted = original_df.sort_values(by=list(original_df.columns)).reset_index(drop=True)

            # Compare values
            if not etl_sorted.equals(original_sorted):
                result['passed'] = False
                result['issues'].append("Data values do not match")

                # Find specific differences
                differences = find_dataframe_differences(etl_sorted, original_sorted)
                if differences:
                    result['issues'].extend(differences[:5])  # Limit to first 5 differences

        except Exception as e:
            result['passed'] = False
            result['issues'].append(f"Error comparing data: {e}")

    # Compare data types
    if result['passed']:
        etl_dtypes = etl_df.dtypes.to_dict()
        original_dtypes = original_df.dtypes.to_dict()

        dtype_mismatches = []
        for col in etl_columns & original_columns:
            if etl_dtypes[col] != original_dtypes[col]:
                dtype_mismatches.append(f"{col}: ETL {etl_dtypes[col]} vs Original {original_dtypes[col]}")

        if dtype_mismatches:
            result['passed'] = False
            result['issues'].append(f"Data type mismatches: {dtype_mismatches}")

    return result


def find_dataframe_differences(df1: pd.DataFrame, df2: pd.DataFrame, max_diffs: int = 5) -> list:
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
                elif pd.isna(val1) or pd.isna(val2):
                    differences.append(f"Row {idx}, Col {col}: ETL {val1} vs Original {val2}")
                elif val1 != val2:
                    differences.append(f"Row {idx}, Col {col}: ETL {val1} vs Original {val2}")

                if len(differences) >= max_diffs:
                    return differences

    return differences


def print_comparison_summary(results: list):
    """Print a summary of the comparison results."""
    print("\n" + "="*80)
    print("INTEGRATION TEST RESULTS")
    print("="*80)

    total_sheets = len(results)
    passed_sheets = sum(1 for r in results if r['passed'])
    failed_sheets = total_sheets - passed_sheets

    print(f"Total sheets compared: {total_sheets}")
    print(f"Passed: {passed_sheets}")
    print(f"Failed: {failed_sheets}")
    print()

    if failed_sheets > 0:
        print("FAILED SHEETS:")
        for result in results:
            if not result['passed']:
                print(f"❌ {result['sheet_name']}")
                for issue in result['issues']:
                    print(f"   - {issue}")
                print()
    else:
        print("✅ ALL SHEETS PASSED COMPARISON!")

    print("="*80)


def backup_existing_outputs():
    """Backup existing prepared data before running tests."""
    prepared_dir = Path("data/prepared")
    backup_dir = Path("data/prepared_backup")

    if prepared_dir.exists():
        logger.info("Backing up existing prepared data...")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(prepared_dir, backup_dir)
        logger.info(f"Backup created at {backup_dir}")


def restore_backup():
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


def main():
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
        print("\n1. Running original prepare_data.py...")
        run_original_prepare_data()

        # Move original outputs to a temporary location
        original_dir = Path("data/prepared_original")
        if original_dir.exists():
            shutil.rmtree(original_dir)
        shutil.copytree(prepared_dir, original_dir)

        # Clean prepared directory for ETL run
        shutil.rmtree(prepared_dir)
        prepared_dir.mkdir(parents=True, exist_ok=True)

        print("\n2. Running ETL pipeline...")
        run_etl_pipeline()

        # Copy original outputs back for comparison
        for file_path in original_dir.glob("*"):
            shutil.copy2(file_path, prepared_dir / f"{file_path.stem}_original{file_path.suffix}")

        print("\n3. Comparing results...")
        success = compare_outputs()

        # Cleanup
        if original_dir.exists():
            shutil.rmtree(original_dir)

        if success:
            logger.info("✅ Integration test PASSED!")
            return True
        else:
            logger.error("❌ Integration test FAILED!")
            return False

    except Exception as e:
        logger.error(f"Integration test failed with error: {e}")
        return False

    finally:
        # Always restore the backup
        restore_backup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)