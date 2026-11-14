#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Comprehensive Excel Data Extraction with Cross-Sheet References.

This script properly extracts data from Excel workbooks by resolving cross-sheet
references and preserving calculated values.
"""

import contextlib
import logging
import re
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


class ComprehensiveExcelExtractor:
    """Extracts data from Excel with proper cross-sheet reference resolution."""

    def __init__(self, excel_path: str) -> None:
        """Select the workbook used for the comprehensive extraction."""
        self.excel_path = Path(excel_path)
        self.wb = None
        self.data_cache = {}

    def load_workbook(self) -> None:
        """Load Excel workbook with calculated values."""
        logger.info("Loading Excel workbook: %s", self.excel_path)
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        logger.info("Loaded %s sheets", len(self.wb.sheetnames))

    def extract_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """Extract data from a specific sheet."""
        if self.wb is None:
            self.load_workbook()

        if sheet_name in self.data_cache:
            return self.data_cache[sheet_name]

        ws = self.wb[sheet_name]

        # Convert to pandas DataFrame
        data = []
        data.extend(row for row in ws.iter_rows(values_only=True))

        df = pd.DataFrame(data)
        self.data_cache[sheet_name] = df

        logger.info("Extracted %s: %s", sheet_name, df.shape)
        return df

    def resolve_cross_sheet_reference(self, formula: str) -> float | None:
        """Resolve a cross-sheet reference to its calculated value."""
        if not formula or not isinstance(formula, str):
            return None

        # Match pattern like 'Sheet Name'!A1 or 'Sheet Name'!AN5
        pattern = r"'([^']+)'!([A-Z]+)(\d+)"
        match = re.match(pattern, formula.strip())

        if not match:
            return None

        sheet_name, col_letter, row_num = match.groups()

        try:
            # Get the referenced sheet
            ref_df = self.extract_sheet_data(sheet_name)
            # Convert column letter to index (A=0, B=1, etc.)
            col_index = self.column_letter_to_index(col_letter)

            # Convert row number to 0-based index
            row_index = int(row_num) - 1  # Excel is 1-based, pandas is 0-based

            if (
                ref_df.empty
                or row_index >= len(ref_df)
                or col_index >= len(ref_df.columns)
            ):
                return None

            value = ref_df.iloc[row_index, col_index]

            # Try to convert to numeric
            if pd.notna(value):
                try:
                    return float(str(value))
                except ValueError, TypeError:
                    return None

        except Exception as e:
            logger.debug(
                "Could not resolve reference %s: %s",
                formula,
                e,
                exc_info=True,
            )

        return None

    def column_letter_to_index(self, letter: str) -> int:
        """Convert Excel column letter to 0-based index."""
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result - 1

    def process_standardized_data(self, model_name: str) -> pd.DataFrame:
        """Process standardized CSV data and resolve cross-sheet references."""
        csv_path = Path(
            "data/standardized/"
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_standardized.csv",
        )

        if not csv_path.exists():
            logger.error("Standardized file not found: %s", csv_path)
            return pd.DataFrame()

        # Load the standardized data
        df = pd.read_csv(csv_path)
        logger.info("Loaded standardized %s: %s", model_name, df.shape)

        # Process each cell that contains a formula
        processed_df = df.copy()

        for row_idx in range(len(processed_df)):
            for col_idx, _col_name in enumerate(processed_df.columns):
                cell_value = processed_df.iloc[row_idx, col_idx]

                if (
                    isinstance(cell_value, str)
                    and cell_value.startswith("='")
                    and "'!" in cell_value
                ):
                    resolved_value = self.resolve_cross_sheet_reference(cell_value)
                    if resolved_value is not None:
                        processed_df.iloc[row_idx, col_idx] = resolved_value
                        logger.debug("Resolved %s -> %s", cell_value, resolved_value)
                    else:
                        logger.debug("Could not resolve %s", cell_value)

        # Convert appropriate columns to numeric
        for col in processed_df.columns:
            if col not in [
                "Test",
                "Category",
                "Sub-Category",
                "Step",
            ]:  # Keep text columns as text
                with contextlib.suppress(ValueError, TypeError):
                    processed_df[col] = pd.to_numeric(
                        processed_df[col],
                        errors="coerce",
                    )

        return processed_df

    def extract_all_models(self) -> dict[str, pd.DataFrame]:
        """Extract and process all genomic models."""
        models = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]
        extracted_data = {}

        for model_name in models:
            logger.info("Processing model: %s", model_name)
            df = self.process_standardized_data(model_name)

            if not df.empty:
                extracted_data[model_name] = df
                logger.info("Successfully processed %s: %s", model_name, df.shape)

        return extracted_data

    def validate_extracted_data(
        self,
        extracted_data: dict[str, pd.DataFrame],
    ) -> dict[str, dict]:
        """Validate the extracted data quality."""
        validation_results = {}

        for model_name, df in extracted_data.items():
            # Count numeric columns with actual values
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            meaningful_numeric = 0
            total_numeric_values = 0

            for col in numeric_cols:
                non_zero_count = (df[col].notna() & (df[col] != 0)).sum()
                if non_zero_count > 0:
                    meaningful_numeric += 1
                    total_numeric_values += non_zero_count

            validation_results[model_name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": len(numeric_cols),
                "meaningful_numeric_columns": meaningful_numeric,
                "total_numeric_values": total_numeric_values,
                "data_quality_score": (meaningful_numeric / max(len(numeric_cols), 1))
                * 100,
            }

        return validation_results

    def save_extracted_data(
        self,
        extracted_data: dict[str, pd.DataFrame],
        output_dir: str = "data/extracted_proper",
    ) -> None:
        """Save the properly extracted data."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for model_name, df in extracted_data.items():
            filename = (
                f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
                "_extracted.csv"
            )
            filepath = output_path / filename

            df.to_csv(filepath, index=False)
            logger.info("Saved %s to %s", model_name, filepath)


def main() -> None:
    """Run the comprehensive workbook extraction."""
    excel_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return

    # Extract data with cross-sheet reference resolution
    extractor = ComprehensiveExcelExtractor(excel_path)
    extracted_data = extractor.extract_all_models()

    # Validate results
    validation = extractor.validate_extracted_data(extracted_data)

    # Save extracted data
    extractor.save_extracted_data(extracted_data)

    # Print summary
    sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
    sys.stdout.writelines(("COMPREHENSIVE EXCEL DATA EXTRACTION RESULTS", "\n"))
    sys.stdout.writelines((str("=" * 60), "\n"))

    total_rows = sum(result["rows"] for result in validation.values())
    total_values = sum(result["total_numeric_values"] for result in validation.values())
    sys.stdout.writelines((f"Total rows processed: {total_rows}", "\n"))
    sys.stdout.writelines((f"Total numeric values extracted: {total_values}", "\n"))
    sys.stdout.writelines((f"Models processed: {len(extracted_data)}", "\n"))

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
            (f"    Total values: {result['total_numeric_values']}", "\n"),
        )
        sys.stdout.writelines(
            (f"    Data quality: {result['data_quality_score']:.1f}%", "\n"),
        )
    sys.stdout.writelines(("\n✅ Comprehensive data extraction complete!", "\n"))


if __name__ == "__main__":
    main()
