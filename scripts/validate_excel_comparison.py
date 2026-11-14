#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Enhanced Model Validation Against Original Excel.

This script validates that the enhanced models maintain data integrity
compared to the original Excel workbooks.
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


class ExcelValidator:
    """Validates enhanced models against original Excel data."""

    def __init__(self, excel_path: str, enhanced_dir: str = "data/enhanced") -> None:
        """Set the workbook and enhanced input directory for comparison."""
        self.excel_path = Path(excel_path)
        self.enhanced_dir = Path(enhanced_dir)
        self.models = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]

    def load_excel_workbook(self) -> dict[str, pd.DataFrame]:
        """Load all sheets from the Excel workbook."""
        logger.info("Loading Excel workbook: %s", self.excel_path)

        try:
            # Load the workbook
            wb = openpyxl.load_workbook(self.excel_path, data_only=True)

            sheets_data = {}
            for sheet_name in wb.sheetnames:
                df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
                sheets_data[sheet_name] = df
                logger.info("Loaded sheet '%s': %s", sheet_name, df.shape)

        except Exception:
            logger.exception("Error loading Excel workbook")
            return {}
        else:
            return sheets_data

    def load_enhanced_model(self, model_name: str) -> pd.DataFrame | None:
        """Load an enhanced model."""
        filename = (
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_enhanced.csv"
        )
        filepath = self.enhanced_dir / filename

        if not filepath.exists():
            logger.warning("Enhanced model not found: %s", filepath)
            return None

        try:
            df = pd.read_csv(filepath)
            logger.info("Loaded enhanced model '%s': %s", model_name, df.shape)
        except Exception:
            logger.exception("Error loading enhanced model %s", model_name)
            return None
        else:
            return df

    def find_model_sheet_mapping(
        self,
        excel_sheets: dict[str, pd.DataFrame],
    ) -> dict[str, str]:
        """Find which Excel sheets correspond to which models."""
        mapping = {}

        # Common patterns for sheet names
        sheet_patterns = {
            "Panel": ["panel", "Panel"],
            "WES (P)": ["wes p", "wes_p", "WES P", "WES_P"],
            "WES (T)": ["wes t", "wes_t", "WES T", "WES_T"],
            "WGS (P)": ["wgs p", "wgs_p", "WGS P", "WGS_P"],
            "WGS (T)": ["wgs t", "wgs_t", "WGS T", "WGS_T"],
        }

        for model_name, patterns in sheet_patterns.items():
            for sheet_name in excel_sheets:
                if any(pattern.lower() in sheet_name.lower() for pattern in patterns):
                    mapping[model_name] = sheet_name
                    logger.info("Mapped %s -> %s", model_name, sheet_name)
                    break

        return mapping

    def compare_numeric_columns(
        self,
        original_df: pd.DataFrame,
        enhanced_df: pd.DataFrame,
        _model_name: str,
    ) -> dict[str, dict]:
        """Compare numeric columns between original and enhanced data."""
        results = {}

        # Find numeric columns in both datasets
        original_numeric = original_df.select_dtypes(include=[np.number]).columns
        enhanced_numeric = enhanced_df.select_dtypes(include=[np.number]).columns

        # Find common numeric columns
        common_numeric = set(original_numeric) & set(enhanced_numeric)

        for col in common_numeric:
            original_values = pd.to_numeric(original_df[col], errors="coerce")
            enhanced_values = pd.to_numeric(enhanced_df[col], errors="coerce")

            # Remove NaN values for comparison
            original_clean = original_values.dropna()
            enhanced_clean = enhanced_values.dropna()

            if len(original_clean) == 0:
                results[col] = {
                    "status": "no_data",
                    "message": "No numeric data in original",
                }
                continue

            if len(enhanced_clean) == 0:
                results[col] = {
                    "status": "no_data",
                    "message": "No numeric data in enhanced",
                }
                continue

            # Calculate differences
            min_diff = abs(original_clean.min() - enhanced_clean.min())
            max_diff = abs(original_clean.max() - enhanced_clean.max())
            mean_diff = abs(original_clean.mean() - enhanced_clean.mean())

            # Check if values are essentially the same (within tolerance)
            tolerance = 0.01  # 1% tolerance for floating point comparisons
            max_relative_diff = (
                max(
                    abs(
                        (original_clean - enhanced_clean).dropna()
                        / original_clean.dropna().replace(0, 1e-10),
                    ),
                ).max()
                if len(original_clean) == len(enhanced_clean)
                else float("inf")
            )

            if max_relative_diff < tolerance:
                status = "valid"
                message = f"Values match within {tolerance * 100:.1f}% tolerance"
            else:
                status = "warning"
                message = f"Values differ by up to {max_relative_diff * 100:.1f}%"

            results[col] = {
                "status": status,
                "message": message,
                "original_count": len(original_clean),
                "enhanced_count": len(enhanced_clean),
                "min_diff": min_diff,
                "max_diff": max_diff,
                "mean_diff": mean_diff,
            }

        return results

    def validate_model_integrity(
        self,
        model_name: str,
        excel_sheets: dict[str, pd.DataFrame],
        sheet_mapping: dict[str, str],
    ) -> dict:
        """Validate a single model's data integrity."""
        logger.info("Validating model: %s", model_name)

        # Load enhanced model
        enhanced_df = self.load_enhanced_model(model_name)
        if enhanced_df is None:
            return {"status": "error", "message": "Could not load enhanced model"}

        # Find corresponding Excel sheet
        if model_name not in sheet_mapping:
            return {
                "status": "warning",
                "message": "No corresponding Excel sheet found",
            }

        sheet_name = sheet_mapping[model_name]
        if sheet_name not in excel_sheets:
            return {
                "status": "error",
                "message": f"Excel sheet '{sheet_name}' not found",
            }

        original_df = excel_sheets[sheet_name]

        # Compare numeric columns
        numeric_comparison = self.compare_numeric_columns(
            original_df,
            enhanced_df,
            model_name,
        )

        # Overall assessment
        valid_columns = sum(
            1
            for col, result in numeric_comparison.items()
            if result.get("status") == "valid"
        )
        warning_columns = sum(
            1
            for col, result in numeric_comparison.items()
            if result.get("status") == "warning"
        )
        total_columns = len(numeric_comparison)

        if valid_columns == total_columns:
            overall_status = "valid"
            message = f"All {total_columns} numeric columns validated successfully"
        elif valid_columns > warning_columns:
            overall_status = "mostly_valid"
            message = (
                f"{valid_columns}"
                "/"
                f"{total_columns}"
                " columns valid, "
                f"{warning_columns}"
                " with warnings"
            )
        else:
            overall_status = "needs_review"
            message = f"Only {valid_columns}/{total_columns} columns fully valid"

        return {
            "status": overall_status,
            "message": message,
            "original_rows": len(original_df),
            "enhanced_rows": len(enhanced_df),
            "numeric_columns_compared": total_columns,
            "valid_columns": valid_columns,
            "warning_columns": warning_columns,
            "column_details": numeric_comparison,
        }

    def validate_all_models(self) -> dict[str, dict]:
        """Validate all enhanced models against original Excel data."""
        logger.info("Starting comprehensive model validation...")

        # Load Excel workbook
        excel_sheets = self.load_excel_workbook()
        if not excel_sheets:
            logger.error("Could not load Excel workbook")
            return {}

        # Find sheet mappings
        sheet_mapping = self.find_model_sheet_mapping(excel_sheets)
        logger.info(
            "Found mappings for %s/%s models",
            len(sheet_mapping),
            len(self.models),
        )

        # Validate each model
        results = {}
        for model_name in self.models:
            result = self.validate_model_integrity(
                model_name,
                excel_sheets,
                sheet_mapping,
            )
            results[model_name] = result

            status_emoji = {
                "valid": "✅",
                "mostly_valid": "⚠️",
                "needs_review": "❌",
                "warning": "⚠️",
                "error": "❌",
            }.get(result.get("status", "unknown"), "❓")

            logger.info(
                "%s %s: %s",
                status_emoji,
                model_name,
                result.get("message", "Unknown status"),
            )

        # Summary
        valid_count = sum(1 for r in results.values() if r.get("status") == "valid")
        mostly_valid_count = sum(
            1 for r in results.values() if r.get("status") == "mostly_valid"
        )
        needs_review_count = sum(
            1 for r in results.values() if r.get("status") in ["needs_review", "error"]
        )

        summary = {
            "total_models": len(self.models),
            "valid_models": valid_count,
            "mostly_valid_models": mostly_valid_count,
            "needs_review_models": needs_review_count,
            "validation_rate": (valid_count + mostly_valid_count)
            / len(self.models)
            * 100,
            "model_results": results,
        }

        logger.info(
            "Validation Summary: %s valid, %s mostly valid, %s need review",
            valid_count,
            mostly_valid_count,
            needs_review_count,
        )
        return summary


def main() -> None:
    """Compare the enhanced data with the reference workbook."""
    excel_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return

    validator = ExcelValidator(excel_path)
    results = validator.validate_all_models()

    # Print summary
    sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
    sys.stdout.writelines(("ENHANCED MODEL VALIDATION SUMMARY", "\n"))
    sys.stdout.writelines((str("=" * 60), "\n"))
    sys.stdout.writelines((f"Total Models: {results['total_models']}", "\n"))
    sys.stdout.writelines((f"Valid Models: {results['valid_models']}", "\n"))
    sys.stdout.writelines((f"Mostly Valid: {results['mostly_valid_models']}", "\n"))
    sys.stdout.writelines((f"Needs Review: {results['needs_review_models']}", "\n"))
    sys.stdout.writelines((".1f", "\n"))
    sys.stdout.writelines(("\n",))

    for model_name, result in results["model_results"].items():
        status = result.get("status", "unknown")
        message = result.get("message", "No details")
        sys.stdout.writelines((f"{model_name}: {status.upper()} - {message}", "\n"))


if __name__ == "__main__":
    main()
