#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Standardized script for preparing all sheets consistently.

Prepare the worksheets consistently across the microcosting analysis,
ensuring that all sheets are treated uniformly regardless of their source or purpose.
"""

import logging
import sys
import traceback

lazy import pandas as pd

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.sheet_manager import SheetManager

logger = logging.getLogger(__name__)


def create_sheet_metadata(df: pd.DataFrame, sheet_name: str) -> dict:
    """Create metadata for a sheet.

    Args:
        df (pd.DataFrame): DataFrame containing the sheet data
        sheet_name (str): Name of the sheet

    Returns:
        dict: Metadata about the sheet

    """
    metadata = {
        "sheet_name": sheet_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "data_types": {},
        "null_counts": {},
        "memory_usage_bytes": df.memory_usage(deep=True).sum(),
    }

    for col in df.columns:
        metadata["columns"].append(str(col))
        metadata["data_types"][str(col)] = str(df[col].dtype)
        metadata["null_counts"][str(col)] = int(df[col].isna().sum())

    return metadata


def prepare_sheet(
    sheet_name: str,
    sheet_manager: SheetManager,
    data_manager: DataManager,
) -> bool:
    """Prepare a single sheet with consistent handling.

    Args:
        sheet_name (str): Name of the sheet to prepare
        sheet_manager (SheetManager): Sheet manager instance
        data_manager (DataManager): Data manager instance

    Returns:
        bool: True if successfully prepared, False otherwise

    """
    sys.stdout.write(f"Preparing sheet: {sheet_name}" + "\n")

    try:
        # Load data from Excel
        df = sheet_manager.get_data(sheet_name)
        if df is None:
            sys.stdout.write(f"  Failed to load data for sheet '{sheet_name}'" + "\n")
            return False

        sys.stdout.write(f"  Loaded data with shape {df.shape}" + "\n")

        # Save in consistent formats
        success = data_manager.save_sheet(sheet_name, df, formats=["parquet", "csv"])

        if success:
            # Create and save metadata
            metadata = create_sheet_metadata(df, sheet_name)
            publication_success = data_manager.save_for_publication(
                sheet_name,
                df,
                metadata,
            )

            if publication_success:
                sys.stdout.write(f"  Successfully prepared sheet '{sheet_name}'" + "\n")
                return True
            sys.stdout.write(
                f"  Prepared sheet '{sheet_name}' but failed to save for publication\n",
            )
            return False
        sys.stdout.write(f"  Failed to save sheet '{sheet_name}'" + "\n")

    except Exception as e:
        logger.exception("Could not complete prepare sheet")
        sys.stdout.write(f"  Error preparing sheet '{sheet_name}': {e}" + "\n")
        return False
    else:
        return False


def main() -> int | None:
    """Prepare all sheets consistently."""
    sys.stdout.write("Preparing all sheets with consistent approach..." + "\n")
    sys.stdout.write(str("=" * 50) + "\n")

    try:
        # Initialize managers
        sheet_manager = SheetManager()
        data_manager = DataManager()

        # Get list of sheets to process
        sheet_names = sheet_manager.get_sheet_names()

        if not sheet_names:
            sys.stdout.write("No sheets found to process!" + "\n")
            return 1

        sys.stdout.write(f"Found {len(sheet_names)} sheets to process:" + "\n")
        for name in sheet_names:
            sys.stdout.write(f"  - {name}" + "\n")
        sys.stdout.write("\n")

        # Process each sheet
        success_count = 0
        for sheet_name in sheet_names:
            if prepare_sheet(sheet_name, sheet_manager, data_manager):
                success_count += 1
            sys.stdout.write("\n")

        sys.stdout.write(str("=" * 50) + "\n")
        sys.stdout.write(
            "Preparation complete: "
            f"{success_count}"
            "/"
            f"{len(sheet_names)}"
            " sheets processed successfully"
            "\n",
        )

        # Show available sheets
        available_sheets = data_manager.list_available_sheets()
        sys.stdout.write("\nAvailable sheets in prepared directory:" + "\n")
        for sheet, formats in available_sheets.items():
            sys.stdout.write(f"  - {sheet}: {', '.join(formats)}" + "\n")

        return 0 if success_count == len(sheet_names) else 1

    except Exception as e:
        logger.exception("Could not complete prepare all sheets")
        sys.stdout.write(f"Error in main preparation process: {e}" + "\n")

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
