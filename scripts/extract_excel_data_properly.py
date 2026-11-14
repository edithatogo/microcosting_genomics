#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Proper Excel Data Extraction with Calculated Values.

This script extracts data from the Excel workbook preserving all calculated values
instead of formulas, addressing the critical data integrity issue.
"""

import logging
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ExcelDataExtractor:
    """Extracts calculated values from Excel workbook."""

    def __init__(self, excel_path: str) -> None:
        """Select the workbook and configure sheet extraction."""
        self.excel_path = Path(excel_path)
        self.wb = None

    def load_workbook(self, *, data_only: bool = True) -> None:
        """Load Excel workbook with calculated values."""
        logger.info("Loading Excel workbook: %s", self.excel_path)
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=data_only)
        logger.info("Loaded %s sheets", len(self.wb.sheetnames))

    def extract_labour_usage_data(self) -> pd.DataFrame:
        """Extract labour usage data with calculated values."""
        if self.wb is None:
            self.load_workbook()

        ws = self.wb["Labour - Usage - VCGS"]

        # Convert to pandas DataFrame
        data = []
        data.extend(row for row in ws.iter_rows(values_only=True))

        df = pd.DataFrame(data)

        # Clean up the data - skip header rows
        df_clean = df.iloc[3:].reset_index(drop=True)  # Skip first 3 rows (headers)

        # Set proper column names from row 0 (after skipping headers)
        column_names = []
        header_row = df.iloc[2]  # Row 2 contains the actual headers
        for col_name in header_row:
            if col_name is None or str(col_name).strip() == "":
                column_names.append(f"Unnamed_{len(column_names)}")
            else:
                column_names.append(str(col_name).strip())

        df_clean.columns = column_names

        # Convert numeric columns
        for col in df_clean.columns:
            try:
                # Try to convert to numeric
                numeric_series = pd.to_numeric(df_clean[col], errors="coerce")
                if numeric_series.notna().sum() > 0:  # If we have numeric data
                    df_clean[col] = numeric_series
            except ValueError, TypeError:
                pass  # Keep as object if conversion fails

        logger.info("Extracted Labour Usage data: %s", df_clean.shape)
        return df_clean

    def split_by_test_type(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Split the detailed table by test type (Panel, WES, WGS)."""
        test_types = {}

        # Get unique test types
        unique_tests = df["Test"].dropna().unique()
        logger.info("Found test types: %s", list(unique_tests))

        for test_type in unique_tests:
            if pd.isna(test_type):
                continue

            # Filter data for this test type
            test_df = df[df["Test"] == test_type].copy()

            # Clean up empty rows
            test_df = test_df.dropna(how="all")

            # Map to our model naming convention
            model_name = self.map_test_type_to_model(test_type)
            test_types[model_name] = test_df

            logger.info("Extracted %s: %s", model_name, test_df.shape)

        return test_types

    def map_test_type_to_model(self, test_type: str) -> str:
        """Map Excel test type to our model naming convention."""
        test_type = str(test_type).lower()

        if "panel" in test_type:
            return "Panel"
        if "wes" in test_type and "p" in test_type:
            return "WES (P)"
        if "wes" in test_type and "t" in test_type:
            return "WES (T)"
        if "wgs" in test_type and "p" in test_type:
            return "WGS (P)"
        if "wgs" in test_type and "t" in test_type:
            return "WGS (T)"
        return str(test_type).title()

    def standardize_columns(self, df: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """Standardize column names to match template requirements."""
        # Define column mapping
        column_mapping = {
            "Test": "Test",
            "Category": "Category",
            "Sub-Category": "Sub-Category",
            "Step": "Item",  # Map Step to Item
            "Quantity of Use per Test": "Units",
            "Price (AUD $/unit)": "Unit Cost (AUD $/unit)",
            "Unit Cost (AUD $/unit)": "Unit Cost (AUD $/unit)",
        }

        # Rename columns
        df_renamed = df.rename(columns=column_mapping)

        # Add missing required columns with default values
        required_columns = [
            "Test",
            "Category",
            "Sub-Category",
            "Item",
            "Unit Cost (AUD $/unit)",
            "Units",
            "Total Cost (AUD)",
            "Notes",
            "Supplier",
            "Catalogue Number",
            "Batch/Lot Number",
            "Expiry Date",
            "Storage Conditions",
            "Quality Control",
            "References",
        ]

        for col in required_columns:
            if col not in df_renamed.columns:
                if col == "Test":
                    df_renamed[col] = model_name
                elif col in ["Unit Cost (AUD $/unit)", "Units", "Total Cost (AUD)"]:
                    df_renamed[col] = 0.0
                else:
                    df_renamed[col] = ""

        # Calculate Total Cost if Unit Cost and Units are available
        if (
            "Unit Cost (AUD $/unit)" in df_renamed.columns
            and "Units" in df_renamed.columns
        ):
            try:
                unit_cost_numeric = pd.to_numeric(
                    df_renamed["Unit Cost (AUD $/unit)"],
                    errors="coerce",
                )
                units_numeric = pd.to_numeric(df_renamed["Units"], errors="coerce")
                df_renamed["Total Cost (AUD)"] = unit_cost_numeric * units_numeric
            except Exception as e:
                logger.warning("Could not calculate Total Cost: %s", e, exc_info=True)
                df_renamed["Total Cost (AUD)"] = 0.0

        # Reorder columns to match template
        return df_renamed[required_columns]

    def save_extracted_data(
        self,
        test_data: dict[str, pd.DataFrame],
        output_dir: str = "data/extracted_correct",
    ) -> None:
        """Save extracted data to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for model_name, df in test_data.items():
            filename = (
                f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
                "_extracted.csv"
            )
            filepath = output_path / filename

            df.to_csv(filepath, index=False)
            logger.info("Saved %s to %s", model_name, filepath)

    def validate_extracted_data(
        self,
        test_data: dict[str, pd.DataFrame],
    ) -> dict[str, dict]:
        """Validate that extracted data has meaningful numeric values."""
        validation_results = {}

        for model_name, df in test_data.items():
            # Check for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            total_numeric = len(numeric_cols)

            # Check for non-zero values
            meaningful_data = 0
            total_rows = len(df)

            for col in numeric_cols:
                try:
                    non_zero_count = int((df[col].notna() & (df[col] != 0)).sum())
                    if non_zero_count > 0:
                        meaningful_data += 1
                except TypeError, AttributeError:
                    # If there's any issue with the sum operation, assume no meaningful
                    # data
                    pass

            # Check for required columns
            required_cols = [
                "Test",
                "Category",
                "Item",
                "Unit Cost (AUD $/unit)",
                "Units",
            ]
            present_required = sum(1 for col in required_cols if col in df.columns)

            validation_results[model_name] = {
                "rows": total_rows,
                "columns": len(df.columns),
                "numeric_columns": total_numeric,
                "meaningful_numeric_columns": meaningful_data,
                "required_columns_present": present_required,
                "data_quality_score": (meaningful_data / max(total_numeric, 1)) * 100,
            }

        return validation_results


def main() -> None:
    """Extract the workbook tables using their expected headers."""
    excel_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return

    # Extract data
    extractor = ExcelDataExtractor(excel_path)
    labour_df = extractor.extract_labour_usage_data()

    # Split by test type
    test_data = extractor.split_by_test_type(labour_df)

    # Standardize and save
    standardized_data = {}
    for model_name, df in test_data.items():
        standardized_df = extractor.standardize_columns(df, model_name)
        standardized_data[model_name] = standardized_df

    # Save extracted data
    extractor.save_extracted_data(standardized_data)

    # Validate results
    validation = extractor.validate_extracted_data(standardized_data)

    # Print summary
    sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
    sys.stdout.writelines(("EXCEL DATA EXTRACTION RESULTS", "\n"))
    sys.stdout.writelines((str("=" * 60), "\n"))

    total_rows = sum(result["rows"] for result in validation.values())
    sys.stdout.writelines((f"Total rows extracted: {total_rows}", "\n"))
    sys.stdout.writelines((f"Models extracted: {len(standardized_data)}", "\n"))

    sys.stdout.writelines(("\nModel Details:", "\n"))
    for model_name, result in validation.items():
        sys.stdout.writelines((f"  {model_name}:", "\n"))
        sys.stdout.writelines((f"    Rows: {result['rows']}", "\n"))
        sys.stdout.writelines((f"    Columns: {result['columns']}", "\n"))
        sys.stdout.writelines(
            (f"    Numeric columns: {result['numeric_columns']}", "\n"),
        )
        sys.stdout.writelines(
            (
                f"    Meaningful data: {result['meaningful_numeric_columns']} columns",
                "\n",
            ),
        )
        sys.stdout.writelines(
            (f"    Data quality: {result['data_quality_score']:.1f}%", "\n"),
        )
    sys.stdout.writelines(
        ("\n✅ Data extraction complete with calculated values preserved!", "\n"),
    )


if __name__ == "__main__":
    main()
