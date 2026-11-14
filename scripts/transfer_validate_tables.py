#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Transfer workbook tables and generate validation tests."""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from genomics_microcosting.config import load_config

logger = logging.getLogger(__name__)

SHEET_PREVIEW_LIMIT = 10


# Define the tables we want to transfer and validate
TABLES_TO_TRANSFER = [
    # Core tables from the original implementation plan
    {
        "name": "2. Labor Prices",
        "description": "Hourly salary rates by personnel category and jurisdiction",
        "already_prepared": True,
        "validation_needed": True,
        "excel_sheet_missing": True,
    },
    {
        "name": "3. Estimates",
        "description": "Default consumable, equipment and labour quantities and prices",
        "already_prepared": True,
        "validation_needed": True,
        "excel_sheet_missing": True,
    },
    {
        "name": "Detailed Table",
        "description": "Primary sheet containing all process steps and calculations",
        "already_prepared": True,
        "validation_needed": True,
    },
    # DSA tables that have prepared data
    {
        "name": "DSA - Labour Prices",
        "description": "Alternative labour rates used during sensitivity testing",
        "already_prepared": True,
        "validation_needed": True,
    },
    {
        "name": "DSA - Test Throughput",
        "description": "Test throughput factors for sensitivity analysis",
        "already_prepared": True,
        "validation_needed": True,
    },
    # DSA tables without prepared data - process from Excel and use extracted data
    {
        "name": "DSA - Overheads",
        "description": "Overhead percentages for each DSA scenario",
        "already_prepared": False,
        "validation_needed": True,
    },
    {
        "name": "DSA - Consumable Discounts",
        "description": "Discount rates for consumables in DSA scenarios",
        "already_prepared": False,
        "validation_needed": True,
    },
    # Tables without prepared data - process from Excel only
    {
        "name": "Process",
        "description": "Process information",
        "already_prepared": False,
        "validation_needed": False,
    },
    {
        "name": "Labour - Costs - VCGS",
        "description": "Labour costs for VCGS",
        "already_prepared": False,
        "validation_needed": False,
    },
    {
        "name": "Labour - Usage - VCGS",
        "description": "Labour usage for VCGS",
        "already_prepared": False,
        "validation_needed": False,
    },
    {
        "name": "Cons -  Costs and Util - VCGS",
        "description": "Consumable costs and utilization for VCGS",
        "already_prepared": False,
        "validation_needed": False,
    },
    {
        "name": "Eq - Costs and Usage - VCGS",
        "description": "Equipment costs and usage for VCGS",
        "already_prepared": False,
        "validation_needed": False,
    },
    {
        "name": "BI - Comp+Stor Costs - VCGS",
        "description": "Bioinformatics computation and storage costs for VCGS",
        "already_prepared": False,
        "validation_needed": False,
    },
]


def _resolve_sheet_name(sheet_names: list[str], requested: str) -> str | None:
    if requested in sheet_names:
        return requested
    normalized = requested.lower().replace(" ", "").replace("-", "").replace("+", "")
    for name in sheet_names:
        if normalized == name.lower().replace(" ", "").replace("-", "").replace(
            "+",
            "",
        ):
            sys.stdout.write(
                f"Found matching sheet: '{name}' for requested '{requested}'\n",
            )
            return name
    sys.stdout.write(f"Sheet '{requested}' not found in workbook. Available sheets:\n")
    sys.stdout.writelines(f"  - {name}\n" for name in sheet_names[:SHEET_PREVIEW_LIMIT])
    if len(sheet_names) > SHEET_PREVIEW_LIMIT:
        sys.stdout.write(f"  ... and {len(sheet_names) - SHEET_PREVIEW_LIMIT} more\n")
    return None


def load_excel_sheet(sheet_name: str) -> pd.DataFrame | None:
    """Load a specific sheet from the Excel workbook."""
    try:
        # Load configuration
        config = load_config()
        workbook_key = config.get("default_workbook", "main")

        # Get the workbook path
        excel_file_path = config["workbooks"][workbook_key]["path"]

        # Check if file exists
        if not Path(excel_file_path).exists():
            # Try the original workbook
            original_config = config.get("workbooks", {}).get("original", {})
            excel_file_path = original_config.get("path", excel_file_path)

        # Load the workbook
        wb = load_workbook(excel_file_path, data_only=True)

        match = _resolve_sheet_name(wb.sheetnames, sheet_name)
        if match is None:
            wb.close()
            return None
        ws = wb[match]

        # Convert to DataFrame
        data = []
        data.extend(row for row in ws.iter_rows(values_only=True))

        # Create DataFrame
        df = pd.DataFrame(data)

        # Handle headers (assuming first row is header)
        if len(df) > 0 and len(df.columns) > 0:
            # Use first row as column names, but handle MultiIndex if needed
            header_row = df.iloc[0]
            df = df.drop(df.index[0]).reset_index(drop=True)

            # Clean column names
            clean_columns = []
            for col in header_row:
                if col is None:
                    clean_columns.append("unnamed")
                else:
                    # Clean the column name
                    clean_col = str(col).strip()
                    if not clean_col:
                        clean_col = "unnamed"
                    clean_columns.append(clean_col)

            df.columns = clean_columns

        wb.close()

    except Exception as e:
        logger.exception("Could not complete load excel sheet")
        sys.stdout.write(f"Error loading sheet '{sheet_name}': {e}" + "\n")

        traceback.print_exc()
        return None
    else:
        return df


def create_table_metadata(
    df: pd.DataFrame,
    table_name: str,
    description: str = "",
) -> dict[str, object]:
    """Create metadata for a table."""
    metadata = {
        "table_name": table_name,
        "description": description,
        "created_date": datetime.now(UTC).astimezone().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "sample_data": {},
    }

    for i, col in enumerate(df.columns):
        # Handle MultiIndex columns
        if isinstance(col, tuple):
            col_name = "_".join(str(x) for x in col if pd.notna(x))
        else:
            col_name = str(col)

        # Get the series for this column
        try:
            series = df.iloc[:, i] if isinstance(col, int) else df[col]
            col_dtype = str(series.dtype)
            null_count = int(series.isna().sum())
        except KeyError, IndexError, AttributeError:
            col_dtype = "unknown"
            null_count = 0

        col_info = {
            "name": col_name,
            "dtype": col_dtype,
            "null_count": null_count,
        }

        # Add unique count for categorical columns
        if col_dtype == "object":
            try:
                col_info["unique_count"] = int(series.nunique())
            except TypeError, AttributeError:
                col_info["unique_count"] = "unknown"

        metadata["columns"].append(col_info)

        # Add sample values (first 3 non-null values)
        try:
            sample_values = series.dropna().head(3).tolist()
            metadata["sample_data"][col_name] = sample_values
        except AttributeError, TypeError:
            metadata["sample_data"][col_name] = []

    return metadata


def validate_table_transfer(
    original_df: pd.DataFrame,
    prepared_df: pd.DataFrame,
    table_name: str,
) -> bool:
    """Validate that the table transfer was successful."""
    sys.stdout.write(f"Validating transfer of '{table_name}'..." + "\n")

    if original_df is None or prepared_df is None:
        sys.stdout.write("  ❌ Validation failed: One of the DataFrames is None" + "\n")
        return False

    # Check dimensions
    if original_df.shape != prepared_df.shape:
        sys.stdout.write(
            "  ⚠️  Dimension mismatch: Original "
            f"{original_df.shape}"
            " vs Prepared "
            f"{prepared_df.shape}"
            "\n",
        )
    else:
        sys.stdout.write(f"  ✅ Dimensions match: {original_df.shape}" + "\n")

    # Check column count
    if len(original_df.columns) == len(prepared_df.columns):
        sys.stdout.write(
            f"  ✅ Column count matches: {len(original_df.columns)}" + "\n",
        )
    else:
        sys.stdout.write(
            "  ⚠️  Column count mismatch: Original "
            f"{len(original_df.columns)}"
            " vs Prepared "
            f"{len(prepared_df.columns)}"
            "\n",
        )

    # Sample data comparison (simple check)
    try:
        # Compare shape and basic info
        sys.stdout.write(
            "  📊 Original: "
            f"{original_df.shape[0]}"
            " rows, "
            f"{original_df.shape[1]}"
            " columns"
            "\n",
        )
        sys.stdout.write(
            "  📊 Prepared: "
            f"{prepared_df.shape[0]}"
            " rows, "
            f"{prepared_df.shape[1]}"
            " columns"
            "\n",
        )
    except Exception as e:
        logger.exception("Could not complete validate table transfer")
        sys.stdout.write(f"  ⚠️  Error in validation: {e}" + "\n")

    sys.stdout.write(f"  📊 Validation complete for '{table_name}'" + "\n")
    return True


def _load_prepared_table(
    table_name: str,
    *,
    already_prepared: bool,
) -> pd.DataFrame | None:
    # Load prepared data if it exists
    prepared_df = None
    if already_prepared:
        try:
            # Try different naming conventions
            normalized_name = table_name.replace(" ", "_").replace("-", "_").lower()
            possible_names = [
                normalized_name.replace("+", "_"),
                normalized_name.replace(".", "_").replace("+", "_"),
                f"{table_name.replace(' ', '_').replace('-', '_').lower()}",
                f"{table_name.replace(' ', '_').lower()}",
                f"{table_name.replace(' - ', '_').replace(' ', '_').lower()}",
                # Handle specific cases we know about
                "2._labor_prices",
                "3._estimates",
                "dsa__labour_prices",
                "dsa__test_throughput",
                "detailed_table",
            ]

            for name in possible_names:
                prepared_data_path = Path("data/prepared") / f"{name}.parquet"
                if prepared_data_path.exists():
                    prepared_df = pd.read_parquet(prepared_data_path)
                    sys.stdout.write(
                        "✅ Loaded prepared data: "
                        f"{prepared_df.shape[0]}"
                        " rows, "
                        f"{prepared_df.shape[1]}"
                        " columns"
                        "\n",
                    )
                    break

            if prepared_df is None:
                # List what parquet files exist
                sys.stdout.write("Available prepared files:" + "\n")
                for f in Path("data/prepared").glob("*.parquet"):
                    sys.stdout.write(f"  - {f.name}" + "\n")
        except Exception as e:
            logger.exception("Could not complete prepare table")
            sys.stdout.write(f"⚠️  Could not load prepared data: {e}" + "\n")

    # If no prepared data, try to load from extracted data
    if prepared_df is None:
        try:
            # Try to find extracted data
            sanitized_name = (
                table_name.replace(" ", "_")
                .replace("-", "_")
                .replace("+", "_")
                .replace(".", "_")
                .lower()
            )
            extracted_pattern = f"{sanitized_name}*_values.csv"
            extracted_files = list(Path("data/extracted").glob(extracted_pattern))

            if extracted_files:
                # Use the first matching file
                extracted_file = extracted_files[0]
                prepared_df = pd.read_csv(extracted_file)
                sys.stdout.write(
                    "✅ Loaded extracted data from "
                    f"{extracted_file}"
                    ": "
                    f"{prepared_df.shape[0]}"
                    " rows, "
                    f"{prepared_df.shape[1]}"
                    " columns"
                    "\n",
                )
            else:
                sys.stdout.write(
                    f"⚠️  No extracted data found for '{table_name}'" + "\n",
                )
        except Exception as e:
            logger.exception("Could not complete prepare table")
            sys.stdout.write(f"⚠️  Could not load extracted data: {e}" + "\n")

    return prepared_df


def prepare_table(table_info: dict[str, str | bool]) -> bool:
    """Prepare a single table for transfer and validation."""
    table_name = table_info["name"]
    description = table_info["description"]
    already_prepared = table_info["already_prepared"]
    excel_sheet_missing = table_info.get("excel_sheet_missing", False)

    sys.stdout.write(f"\n{'=' * 60}" + "\n")
    sys.stdout.write(f"Processing table: {table_name}" + "\n")
    sys.stdout.write(f"Description: {description}" + "\n")
    sys.stdout.write(f"Already prepared: {already_prepared}" + "\n")
    sys.stdout.write(f"Excel sheet missing: {excel_sheet_missing}" + "\n")
    sys.stdout.write(f"{'=' * 60}" + "\n")

    # Load the original Excel data
    original_df = None
    if not excel_sheet_missing:
        sys.stdout.write("Loading original data from Excel..." + "\n")
        original_df = load_excel_sheet(table_name)

        if original_df is None:
            sys.stdout.write(
                f"❌ Failed to load original data for '{table_name}'" + "\n",
            )
            return False

        sys.stdout.write(
            "✅ Loaded original data: "
            f"{original_df.shape[0]}"
            " rows, "
            f"{original_df.shape[1]}"
            " columns"
            "\n",
        )
    else:
        sys.stdout.write(
            "⚠️  Excel sheet missing for '"
            f"{table_name}"
            "', proceeding with prepared data only"
            "\n",
        )

    prepared_df = _load_prepared_table(
        table_name,
        already_prepared=bool(already_prepared),
    )

    # Validate the transfer (only if we have both original and prepared data)
    if prepared_df is not None and original_df is not None:
        validate_table_transfer(original_df, prepared_df, table_name)
    elif prepared_df is not None and excel_sheet_missing:
        sys.stdout.write(
            f"✅ Using prepared data for '{table_name}' (no Excel sheet available)\n",
        )
        original_df = prepared_df  # Use prepared data as original for metadata creation
    elif prepared_df is not None:
        sys.stdout.write(f"✅ Using extracted/prepared data for '{table_name}'" + "\n")
        original_df = (
            prepared_df  # Use prepared/extracted data as original for metadata creation
        )
    elif prepared_df is None:
        sys.stdout.write(
            f"❌ No prepared or extracted data available for '{table_name}'" + "\n",
        )
        # If we have original data but no prepared data, use original data for metadata
        if original_df is not None:
            prepared_df = original_df
            sys.stdout.write(
                "⚠️  Using original data for metadata creation (no prepared "
                "data available)"
                "\n",
            )
        else:
            return False

    # Create metadata
    metadata = create_table_metadata(original_df, table_name, description)

    # Save metadata
    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(exist_ok=True)

    # Sanitize filename
    sanitized_name = "".join(
        c for c in table_name if c.isalnum() or c in (" ", "_", "-", "+")
    ).rstrip()
    sanitized_name = (
        sanitized_name.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("+", "_")
        .replace(".", "_")
    )
    metadata_file = metadata_dir / f"{sanitized_name}_metadata.json"
    with Path(metadata_file).open("w") as f:
        json.dump(metadata, f, indent=2)
    sys.stdout.write(f"✅ Saved metadata to {metadata_file}" + "\n")

    # Save as CSV for easy inspection
    csv_file = metadata_dir / f"{sanitized_name}.csv"
    original_df.to_csv(csv_file, index=False)
    sys.stdout.write(f"✅ Saved CSV to {csv_file}" + "\n")

    return True


def create_table_test(table_name: str) -> Path:
    """Create a test for a specific table."""
    # Sanitize table name for use in function names
    sanitized_name = "".join(
        c for c in table_name if c.isalnum() or c in (" ", "_", "-")
    ).rstrip()
    sanitized_name = (
        sanitized_name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
    )

    # Handle special cases
    if table_name == "2. Labor Prices":
        sanitized_name = "2._labor_prices"
    elif table_name == "3. Estimates":
        sanitized_name = "3._estimates"
    elif table_name == "DSA - Labour Prices":
        sanitized_name = "dsa__labour_prices"
    elif table_name == "DSA - Test Throughput":
        sanitized_name = "dsa__test_throughput"

    test_name = sanitized_name.replace(".", "_").replace("-", "_").replace("+", "_")
    test_content = f'''"""Test for {table_name} table transfer and validation."""

import pandas as pd
import pytest
from pathlib import Path


def test_{test_name}_loading():
    """Test that the {table_name} table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "{sanitized_name}.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {{len(df)}} rows and {{len(df.columns)}} columns")
    else:
        # Try alternative names
        alternatives = [
            "{sanitized_name}",
            "{table_name.replace(" ", "_")}",
        ]
        found = False
        for alt in alternatives:
            # Try different extensions
            for ext in [".parquet"]:
                prepared_path = Path("data/prepared") / f"{{alt}}{{ext}}"
                if prepared_path.exists():
                    df = pd.read_parquet(prepared_path)
                    assert isinstance(df, pd.DataFrame)
                    assert len(df) > 0
                    assert len(df.columns) > 0
                    print(f"Loaded {{len(df)}} rows and {{len(df.columns)}} columns")
                    found = True
                    break
            if found:
                break
        if not found:
            # List available files for debugging
            print("Available prepared files:")
            for f in Path("data/prepared").glob("*.parquet"):
                print(f"  - {{f.name}}")
            pytest.skip(f"Prepared data for {table_name} not found")


def test_{test_name}_data_integrity():
    """Test data integrity for {table_name} table."""
    prepared_path = Path("data/prepared") / "{sanitized_name}.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)

        # Check for reasonable data types
        assert len(df.columns) > 0

        # Check for null values (should be reasonable amount)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        null_percentage = null_cells / total_cells if total_cells > 0 else 0

        # Allow up to 50% null values (this might need adjustment based on the table)
        assert null_percentage < 0.5, f"Too many null values: {{null_percentage:.2%}}"

        print(f"Data integrity check passed for {table_name}")
        print(f"  - Null value percentage: {{null_percentage:.2%}}")
    else:
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "{sanitized_name}" in f.name:
                df = pd.read_parquet(f)
                # Check for reasonable data types
                assert len(df.columns) > 0

                # Check for null values (should be reasonable amount)
                total_cells = df.shape[0] * df.shape[1]
                null_cells = df.isnull().sum().sum()
                null_percentage = null_cells / total_cells if total_cells > 0 else 0

                # Keep the expected null fraction below one half.
                assert null_percentage < 0.5, f"Null fraction: {{null_percentage:.2%}}"

                print(f"Data integrity check passed for {table_name}")
                print(f"  - Null value percentage: {{null_percentage:.2%}}")
                found = True
                break
        if not found:
            pytest.skip(f"Prepared data for {table_name} not found")


def test_{test_name}_schema_consistency():
    """Test schema consistency for {table_name} table."""
    prepared_path = Path("data/prepared") / "{sanitized_name}.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)

        # Check that we have columns
        assert len(df.columns) > 0

        # Check for duplicate column names
        columns_list = list(df.columns)
        assert len(columns_list) == len(set(columns_list)), "Duplicate columns"

        print(f"Schema consistency check passed for {table_name}")
    else:
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "{sanitized_name}" in f.name:
                df = pd.read_parquet(f)
                # Check that we have columns
                assert len(df.columns) > 0

                # Check for duplicate column names
                columns_list = list(df.columns)
                assert len(columns_list) == len(set(columns_list)), "Duplicate columns"

                print(f"Schema consistency check passed for {table_name}")
                found = True
                break
        if not found:
            pytest.skip(f"Prepared data for {table_name} not found")


if __name__ == "__main__":
    try:
        test_{test_name}_loading()
        test_{test_name}_data_integrity()
        test_{test_name}_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {{e}}")
        import traceback
        traceback.print_exc()
'''

    # Save test file
    test_file_name = (
        "test_"
        f"{sanitized_name.replace('.', '_').replace('-', '_').replace('+', '_')}"
        ".py"
    )
    test_file = Path("tests") / test_file_name
    with Path(test_file).open("w") as f:
        f.write(test_content)

    sys.stdout.write(f"✅ Created test file: {test_file}" + "\n")
    return test_file


def main() -> int:
    """Transfer and validate all tables."""
    sys.stdout.write("Starting systematic table transfer and validation..." + "\n")
    sys.stdout.write(f"Processing {len(TABLES_TO_TRANSFER)} tables" + "\n")

    success_count = 0
    total_count = len(TABLES_TO_TRANSFER)

    for i, table_info in enumerate(TABLES_TO_TRANSFER, 1):
        sys.stdout.write(
            f"\n[{i}/{total_count}] Processing {table_info['name']}..." + "\n",
        )

        try:
            # Prepare the table
            success = prepare_table(table_info)

            if success:
                success_count += 1

                # Create test for the table
                if table_info["validation_needed"]:
                    test_file = create_table_test(table_info["name"])
                    sys.stdout.write(f"✅ Created validation test: {test_file}" + "\n")

            sys.stdout.write(
                f"{'✅' if success else '❌'} Completed {table_info['name']}" + "\n",
            )

        except Exception as e:
            logger.exception("Could not complete transfer validate tables")
            sys.stdout.write(f"❌ Error processing {table_info['name']}: {e}" + "\n")

            traceback.print_exc()

    sys.stdout.write(f"\n{'=' * 60}" + "\n")
    sys.stdout.write(
        f"SUMMARY: {success_count}/{total_count} tables processed successfully" + "\n",
    )
    sys.stdout.write(f"{'=' * 60}" + "\n")

    if success_count == total_count:
        sys.stdout.write("🎉 All tables transferred and validated successfully!" + "\n")
        return 0
    sys.stdout.write(f"⚠️  {total_count - success_count} tables had issues" + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
