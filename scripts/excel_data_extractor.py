#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Excel Data Extraction with Value Preservation.

This script properly extracts data from Excel workbooks, preserving calculated values
instead of formulas to preserve the observed values used for validation.
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
    """Extracts data from Excel workbooks with calculated values preserved."""

    def __init__(self, excel_path: str, output_dir: str = "data/corrected") -> None:
        """Set the input workbook and corrected table destination."""
        self.excel_path = Path(excel_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Model configurations
        self.model_configs = {
            "Panel": {
                "sheet_patterns": ["detailed table", "panel", "summary table"],
                "expected_rows": 250,
                "key_columns": [
                    "Test Category",
                    "Item",
                    "Unit Cost",
                    "Units",
                    "Total Cost",
                ],
            },
            "WES (P)": {
                "sheet_patterns": ["wes p", "wes_p", "wes panel", "exome panel"],
                "expected_rows": 260,
                "key_columns": [
                    "Test Category",
                    "Item",
                    "Unit Cost",
                    "Units",
                    "Total Cost",
                ],
            },
            "WES (T)": {
                "sheet_patterns": ["wes t", "wes_t", "wes trio", "exome trio"],
                "expected_rows": 300,
                "key_columns": [
                    "Test Category",
                    "Item",
                    "Unit Cost",
                    "Units",
                    "Total Cost",
                ],
            },
            "WGS (P)": {
                "sheet_patterns": ["wgs p", "wgs_p", "wgs panel", "genome panel"],
                "expected_rows": 240,
                "key_columns": [
                    "Test Category",
                    "Item",
                    "Unit Cost",
                    "Units",
                    "Total Cost",
                ],
            },
            "WGS (T)": {
                "sheet_patterns": ["wgs t", "wgs_t", "wgs trio", "genome trio"],
                "expected_rows": 270,
                "key_columns": [
                    "Test Category",
                    "Item",
                    "Unit Cost",
                    "Units",
                    "Total Cost",
                ],
            },
        }

    def load_excel_with_values(self, sheet_name: str) -> pd.DataFrame | None:
        """Load Excel sheet with calculated values preserved."""
        try:
            # Use openpyxl directly to get calculated values
            wb = openpyxl.load_workbook(self.excel_path, data_only=True)
            ws = wb[sheet_name]

            # Convert to DataFrame
            data = []
            data.extend(row for row in ws.iter_rows(values_only=True))

            if not data:
                logger.warning("Sheet '%s' is empty", sheet_name)
                return None

            df = pd.DataFrame(data)

            # Set first row as header if it looks like headers
            if len(df) > 0:
                first_row = df.iloc[0].astype(str).str.strip()
                if (
                    first_row.notna().any()
                    and not first_row.str.match(r"^\d+\.?\d*$").any()
                ):
                    df.columns = first_row
                    df = df.iloc[1:].reset_index(drop=True)

            logger.info(
                "Loaded sheet '%s': %s with calculated values preserved",
                sheet_name,
                df.shape,
            )

        except Exception:
            logger.exception(
                "Error loading sheet '%s' with calculated values",
                sheet_name,
            )
            return None
        else:
            return df

    def find_best_sheet_for_model(self, _model_name: str) -> str | None:
        """Find the best matching Excel sheet for a given model."""
        # For now, use the comprehensive Detailed Table for all models
        # This contains data for Panel, WES, and WGS models
        return "Detailed Table"

    def _convert_numeric_candidates(self, df: pd.DataFrame) -> None:
        # Convert numeric columns that should be numeric
        numeric_candidates = []
        for col in df.columns:
            try:
                col_data = df[col]
                if hasattr(col_data, "dtype") and col_data.dtype == "object":
                    # Check if column contains mostly numeric data
                    sample_values = col_data.dropna().head(10)
                    if len(sample_values) > 0:
                        numeric_count = 0
                        for val in sample_values:
                            try:
                                float(
                                    str(val).replace("$", "").replace(",", "").strip(),
                                )
                                numeric_count += 1
                            except ValueError, AttributeError:
                                pass

                        if numeric_count >= len(sample_values) * 0.7:  # 70% numeric
                            numeric_candidates.append(col)
            except (KeyError, TypeError) as e:
                logger.warning("Error accessing column %s: %s", col, e)
                continue

        # Convert identified numeric columns
        for col in numeric_candidates:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    def clean_and_validate_data(
        self,
        df: pd.DataFrame,
        model_name: str,
    ) -> pd.DataFrame:
        """Clean and validate extracted data."""
        logger.info("Cleaning data for %s: %s", model_name, df.shape)

        # Remove completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        # Reset index after cleaning
        df = df.reset_index(drop=True)

        self._convert_numeric_candidates(df)

        # Validate expected structure
        config = self.model_configs[model_name]
        expected_rows = config["expected_rows"]

        if abs(len(df) - expected_rows) > expected_rows * 0.2:  # 20% tolerance
            logger.warning(
                "Row count mismatch for %s: expected ~%s, got %s",
                model_name,
                expected_rows,
                len(df),
            )

        # Check for key columns
        key_columns = config["key_columns"]
        found_columns = [col for col in key_columns if col in df.columns]
        missing_columns = [col for col in key_columns if col not in df.columns]

        if missing_columns:
            logger.warning(
                "Missing key columns for %s: %s",
                model_name,
                missing_columns,
            )
        if found_columns:
            logger.info("Found key columns for %s: %s", model_name, found_columns)

        return df

    def extract_model_from_detailed_table(
        self,
        df: pd.DataFrame,
        model_name: str,
    ) -> pd.DataFrame:
        """Extract data for a specific model from the Detailed Table."""
        # Known model boundaries in the Detailed Table (0-indexed)
        model_boundaries = {
            "Panel": (4, 260),  # Rows 5-260 (0-indexed: 4-259)
            "WES (P)": (260, 524),  # Rows 261-524 (0-indexed: 260-523)
            "WES (T)": (524, 824),  # Rows 525-824 (0-indexed: 524-823)
            "WGS (P)": (824, 1069),  # Rows 825-1069 (0-indexed: 824-1068)
            "WGS (T)": (1069, None),  # Rows 1070-end (0-indexed: 1069-end)
        }

        if model_name not in model_boundaries:
            logger.warning("No boundary information for model %s", model_name)
            return pd.DataFrame()

        start_idx, end_idx = model_boundaries[model_name]

        # Extract the model data
        if end_idx is None:
            model_df = df.iloc[start_idx:].copy()
        else:
            model_df = df.iloc[start_idx:end_idx].copy()

        # Clean up the data
        # Remove completely empty rows
        model_df = model_df.dropna(how="all")

        # Reset index
        model_df = model_df.reset_index(drop=True)

        logger.info(
            "Extracted %s rows for %s (rows %s to %s)",
            len(model_df),
            model_name,
            start_idx + 1,
            end_idx or "end",
        )
        return model_df

    def extract_model_data(self, model_name: str) -> pd.DataFrame | None:
        """Extract data for a specific model."""
        logger.info("Extracting data for model: %s", model_name)

        # Find best sheet (now always Detailed Table)
        sheet_name = self.find_best_sheet_for_model(model_name)
        if not sheet_name:
            return None

        # Load data with calculated values
        df = self.load_excel_with_values(sheet_name)
        if df is None:
            return None

        # Extract model-specific data from the detailed table
        model_df = self.extract_model_from_detailed_table(df, model_name)

        if model_df.empty:
            logger.warning("No data extracted for %s", model_name)
            return None

        # Clean and validate
        model_df = self.clean_and_validate_data(model_df, model_name)

        # Add metadata
        model_df.attrs["source_sheet"] = sheet_name
        model_df.attrs["extraction_method"] = "excel_data_only"
        model_df.attrs["model"] = model_name

        return model_df

    def validate_numeric_data_quality(self, df: pd.DataFrame, model_name: str) -> dict:
        """Validate the quality of numeric data in the extracted DataFrame."""
        quality_report = {
            "model": model_name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": 0,
            "non_zero_numeric_values": 0,
            "total_numeric_values": 0,
            "data_quality_score": 0.0,
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        quality_report["numeric_columns"] = len(numeric_cols)

        for col in numeric_cols:
            non_null = df[col].notna()
            non_zero = (df[col] != 0) & non_null

            quality_report["non_zero_numeric_values"] += non_zero.sum()
            quality_report["total_numeric_values"] += non_null.sum()

        # Calculate data quality score
        if quality_report["total_numeric_values"] > 0:
            quality_score = (
                quality_report["non_zero_numeric_values"]
                / quality_report["total_numeric_values"]
            )
            quality_report["data_quality_score"] = quality_score

        logger.info(
            "Data quality for %s: %s/%s non-zero values (%s)",
            model_name,
            quality_report["non_zero_numeric_values"],
            quality_report["total_numeric_values"],
            format(quality_report["data_quality_score"], ".1%"),
        )

        return quality_report

    def save_corrected_model(self, df: pd.DataFrame, model_name: str) -> str:
        """Save the corrected model data."""
        filename = (
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_corrected.csv"
        )
        filepath = self.output_dir / filename

        df.to_csv(filepath, index=False)
        logger.info("Saved corrected model to: %s", filepath)

        return str(filepath)

    def extract_all_models(self) -> dict[str, dict]:
        """Extract data for all models and return quality reports."""
        logger.info("Starting extraction of all models with value preservation...")

        results = {}

        for model_name in self.model_configs:
            logger.info("Processing %s...", model_name)

            # Extract data
            df = self.extract_model_data(model_name)

            if df is None:
                results[model_name] = {
                    "status": "failed",
                    "error": "Could not extract data",
                }
                continue

            # Validate data quality
            quality_report = self.validate_numeric_data_quality(df, model_name)

            # Save corrected data
            output_path = self.save_corrected_model(df, model_name)

            results[model_name] = {
                "status": "success",
                "output_path": output_path,
                "quality_report": quality_report,
                "source_sheet": df.attrs.get("source_sheet"),
                "shape": df.shape,
            }

        return results


def main() -> None:
    """Extract and save the corrected workbook tables."""
    excel_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return

    extractor = ExcelDataExtractor(excel_path)
    results = extractor.extract_all_models()

    # Print summary
    sys.stdout.writelines((str("\n" + "=" * 70), "\n"))
    sys.stdout.writelines(
        ("EXCEL DATA EXTRACTION WITH VALUE PRESERVATION - RESULTS", "\n"),
    )
    sys.stdout.writelines((str("=" * 70), "\n"))

    success_count = 0
    total_quality_score = 0

    for model_name, result in results.items():
        if result["status"] == "success":
            success_count += 1
            quality = result["quality_report"]
            total_quality_score += quality["data_quality_score"]

            sys.stdout.writelines((f"✅ {model_name}: SUCCESS", "\n"))
            sys.stdout.writelines((f"   Source Sheet: {result['source_sheet']}", "\n"))
            sys.stdout.writelines((f"   Shape: {result['shape']}", "\n"))
            sys.stdout.writelines(
                (
                    (
                        f"   Data Quality: {quality['non_zero_numeric_values']}/"
                        f"{quality['total_numeric_values']} non-zero values ("
                        f"{quality['data_quality_score']:.1%})"
                    ),
                    "\n",
                ),
            )
        else:
            sys.stdout.writelines(
                (
                    f"❌ {model_name}: FAILED - {result.get('error', 'Unknown error')}",
                    "\n",
                ),
            )

        sys.stdout.writelines(("\n",))

    if success_count > 0:
        avg_quality = total_quality_score / success_count
        sys.stdout.writelines(
            (f"Summary: {success_count}/5 models extracted successfully", "\n"),
        )
        sys.stdout.writelines((f"Average data quality: {avg_quality:.1%}", "\n"))
    else:
        sys.stdout.writelines(("❌ No models extracted successfully", "\n"))


if __name__ == "__main__":
    main()
