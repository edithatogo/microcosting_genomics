#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Automated Standardization Engine.

This script implements automated standardization of genomic testing models
using the rules defined in the standard_categories.yaml configuration file.

The engine:
1. Loads original model data
2. Applies standardization mappings
3. Validates standardized structure
4. Generates standardized model files
5. Runs validation checks
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

MINIMUM_COLUMN_COUNT = 3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class StandardizationResult:
    """Container for standardization results."""

    model_name: str
    original_rows: int
    standardized_rows: int
    categories_mapped: int
    subcategories_mapped: int
    validation_passed: bool
    validation_errors: list[str]
    validation_warnings: list[str]


@dataclass
class StandardizedModel:
    """Container for a standardized model."""

    name: str
    dataframe: pd.DataFrame
    metadata: dict[str, Any]


class AutomatedStandardizationEngine:
    """Engine for automated model standardization."""

    def __init__(self, config_path: str = "config/standard_categories.yaml") -> None:
        """Load the category and subcategory mapping rules."""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.models = [
            "Panel",
            "WES (P)",
            "WES (T)",
            "WGS (P)",
            "WGS (T)",
        ]

    def load_config(self) -> dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            message = f"Configuration file not found: {self.config_path}"
            raise FileNotFoundError(message)

        with self.config_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_original_model(self, model_name: str) -> pd.DataFrame | None:
        """Load original model data from the detailed table."""
        data_path = Path("data/Detailed Table.csv")

        if not data_path.exists():
            logger.error("Data file not found: %s", data_path)
            return None

        try:
            # Load and find the model's data
            df = pd.read_csv(data_path, header=None)

            # Find header row
            header_row_idx: int | None = None
            for idx in range(len(df)):
                row = df.iloc[idx]
                if "Test" in str(row.values) and "Category" in str(row.values):
                    header_row_idx = idx
                    break

            if header_row_idx is None:
                logger.error("Could not find header row")
                return None

            # Read with correct header
            df = pd.read_csv(data_path, header=header_row_idx)

            # Extract model data
            return self.extract_model_data(df, model_name)

        except Exception:
            logger.exception("Error loading model %s", model_name)
            return None

    def extract_model_data(
        self,
        df: pd.DataFrame,
        model_name: str,
    ) -> pd.DataFrame | None:
        """Extract data for a specific model."""
        # Find all rows with non-empty Test values
        test_rows = df[df["Test"].notna()].index.tolist()

        for i, row_idx in enumerate(test_rows):
            test_value = df.loc[row_idx, "Test"]

            if test_value == model_name:
                # Collect all rows for this test
                start_idx = row_idx
                end_idx = test_rows[i + 1] if i + 1 < len(test_rows) else len(df)

                test_df = df.loc[start_idx : end_idx - 1].copy()
                test_df["Test"] = test_df["Test"].fillna(test_value)
                return test_df

        return None

    def apply_category_mappings(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Apply category standardization mappings."""
        if df is None or df.empty:
            return df, 0

        df_copy = df.copy()
        mappings_applied = 0

        category_mappings = self.config.get("standardization_mappings", {}).get(
            "category_mappings",
            {},
        )

        if "Category" in df_copy.columns and category_mappings:
            # Apply mappings
            df_copy["Category"] = df_copy["Category"].map(
                lambda x: category_mappings.get(x, x) if pd.notna(x) else x,
            )

            # Count how many mappings were applied
            original_categories = df["Category"].fillna("")
            mapped_categories = df_copy["Category"].fillna("")
            mappings_applied = sum(
                1
                for orig, mapped in zip(
                    original_categories,
                    mapped_categories,
                    strict=False,
                )
                if orig != mapped and orig in category_mappings
            )

        return df_copy, mappings_applied

    def apply_subcategory_mappings(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Apply subcategory standardization mappings."""
        if df is None or df.empty:
            return df, 0

        df_copy = df.copy()
        mappings_applied = 0

        subcategory_mappings = self.config.get("standardization_mappings", {}).get(
            "subcategory_mappings",
            {},
        )

        if "Sub-Category" in df_copy.columns and subcategory_mappings:
            # Apply mappings
            df_copy["Sub-Category"] = df_copy["Sub-Category"].map(
                lambda x: subcategory_mappings.get(x, x) if pd.notna(x) else x,
            )

            # Count how many mappings were applied
            original_subcats = df["Sub-Category"].fillna("")
            mapped_subcats = df_copy["Sub-Category"].fillna("")
            mappings_applied = sum(
                1
                for orig, mapped in zip(original_subcats, mapped_subcats, strict=False)
                if orig != mapped and orig in subcategory_mappings
            )

        return df_copy, mappings_applied

    def add_model_specific_subcategories(
        self,
        df: pd.DataFrame,
        model_name: str,
    ) -> pd.DataFrame:
        """Add model-specific subcategories if applicable."""
        if df is None or df.empty:
            return df

        df_copy = df.copy()
        model_specific = self.config.get("model_specific_subcategories", {}).get(
            model_name,
            {},
        )

        if model_specific:
            logger.info(
                "Adding model-specific subcategories for %s: %s",
                model_name,
                model_specific,
            )

            # For now, we'll log this but not modify the data structure
            # In a full implementation, this would add missing subcategories
            # based on the model-specific configuration

        return df_copy

    def validate_standardized_model(
        self,
        df: pd.DataFrame,
        _model_name: str,
    ) -> tuple[bool, list[str], list[str]]:
        """Validate that the standardized model meets requirements."""
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("Model data is empty")
            return False, errors, warnings

        # Check required categories
        required_categories = self.config.get("validation_rules", {}).get(
            "required_categories",
            [],
        )
        present_categories = set(df["Category"].dropna().unique())

        missing_categories = set(required_categories) - present_categories
        if missing_categories:
            errors.append(
                f"Missing required categories: {', '.join(missing_categories)}",
            )

        # Check minimum subcategories
        min_subcategories = self.config.get("validation_rules", {}).get(
            "minimum_subcategories",
            {},
        )
        for category, min_count in min_subcategories.items():
            if category in present_categories:
                subcats = (
                    df[df["Category"] == category]["Sub-Category"].dropna().unique()
                )
                if len(subcats) < min_count:
                    warnings.append(
                        (
                            f"Category '{category}' has {len(subcats)}"
                            " subcategories, minimum is "
                            f"{min_count}"
                        ),
                    )

        # Check for unmapped categories/subcategories
        standard_categories = set(self.config.get("standard_categories", []))
        non_standard_categories = present_categories - standard_categories
        if non_standard_categories:
            warnings.append(
                (
                    "Non-standard categories present: "
                    f"{', '.join(non_standard_categories)}"
                ),
            )

        # Check data integrity
        if len(df) == 0:
            errors.append("No data rows found")
        elif len(df.columns) < MINIMUM_COLUMN_COUNT:
            warnings.append(
                f"Model has few columns ({len(df.columns)}), may be incomplete",
            )

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def standardize_model(self, model_name: str) -> StandardizationResult:
        """Standardize a single model."""
        logger.info("Starting standardization of %s", model_name)

        # Load original data
        original_df = self.load_original_model(model_name)
        if original_df is None:
            return StandardizationResult(
                model_name=model_name,
                original_rows=0,
                standardized_rows=0,
                categories_mapped=0,
                subcategories_mapped=0,
                validation_passed=False,
                validation_errors=["Could not load original model data"],
                validation_warnings=[],
            )

        original_rows = len(original_df)

        # Apply category mappings
        df_step1, cat_mappings = self.apply_category_mappings(original_df)

        # Apply subcategory mappings
        df_step2, subcat_mappings = self.apply_subcategory_mappings(df_step1)

        # Add model-specific subcategories
        standardized_df = self.add_model_specific_subcategories(df_step2, model_name)

        # Validate the standardized model
        is_valid, errors, warnings = self.validate_standardized_model(
            standardized_df,
            model_name,
        )

        # Save the standardized model
        if standardized_df is not None and not standardized_df.empty:
            self.save_standardized_model(model_name, standardized_df)

        result = StandardizationResult(
            model_name=model_name,
            original_rows=original_rows,
            standardized_rows=len(standardized_df)
            if standardized_df is not None
            else 0,
            categories_mapped=cat_mappings,
            subcategories_mapped=subcat_mappings,
            validation_passed=is_valid,
            validation_errors=errors,
            validation_warnings=warnings,
        )

        logger.info(
            "Completed standardization of %s: %s rows, %s mappings applied",
            model_name,
            result.standardized_rows,
            cat_mappings + subcat_mappings,
        )
        return result

    def standardize_all_models(self) -> dict[str, StandardizationResult]:
        """Standardize all models."""
        results = {}

        for model_name in self.models:
            try:
                result = self.standardize_model(model_name)
                results[model_name] = result

                status = "✅" if result.validation_passed else "❌"
                logger.info("%s Standardized %s", status, model_name)

                if result.validation_errors:
                    logger.error("  Errors: %s", ", ".join(result.validation_errors))
                if result.validation_warnings:
                    logger.warning(
                        "  Warnings: %s",
                        ", ".join(result.validation_warnings),
                    )

            except Exception as e:
                logger.exception("Failed to standardize %s", model_name)
                results[model_name] = StandardizationResult(
                    model_name=model_name,
                    original_rows=0,
                    standardized_rows=0,
                    categories_mapped=0,
                    subcategories_mapped=0,
                    validation_passed=False,
                    validation_errors=[str(e)],
                    validation_warnings=[],
                )

        return results

    def save_standardized_model(
        self,
        model_name: str,
        df: pd.DataFrame,
        output_dir: str = "data/standardized",
    ) -> None:
        """Save a standardized model to file."""
        if df is None or df.empty:
            logger.warning("Cannot save empty model: %s", model_name)
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_standardized.csv"
        )
        filepath = output_path / filename

        df.to_csv(filepath, index=False)
        logger.info("Saved standardized model to: %s", filepath)

    def generate_standardization_report(
        self,
        results: dict[str, StandardizationResult],
    ) -> str:
        """Generate a comprehensive standardization report."""
        report = []
        report.append("# Automated Standardization Report")
        report.append(
            "Generated: "
            f"{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        )
        report.append("")

        # Summary
        total_models = len(results)
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_mappings = sum(
            r.categories_mapped + r.subcategories_mapped for r in results.values()
        )

        report.append("## Summary")
        report.append(f"- **Models Processed**: {total_models}")
        report.append(f"- **Successfully Standardized**: {successful_models}")
        report.append(
            f"- **Success Rate**: {successful_models / total_models * 100:.1f}%",
        )
        report.append(f"- **Total Mappings Applied**: {total_mappings}")
        report.append("")

        # Individual model results
        report.append("## Model Standardization Results")
        for model_name, result in results.items():
            status = "✅ PASS" if result.validation_passed else "❌ FAIL"
            report.append(f"### {model_name} - {status}")
            report.append(f"- **Original Rows**: {result.original_rows}")
            report.append(f"- **Standardized Rows**: {result.standardized_rows}")
            report.append(f"- **Categories Mapped**: {result.categories_mapped}")
            report.append(f"- **Subcategories Mapped**: {result.subcategories_mapped}")

            if result.validation_errors:
                report.append("- **Errors**:")
                report.extend(f"  - {error}" for error in result.validation_errors)

            if result.validation_warnings:
                report.append("- **Warnings**:")
                report.extend(
                    f"  - {warning}" for warning in result.validation_warnings
                )

            report.append("")

        # Overall assessment
        report.append("## Overall Assessment")

        if successful_models == total_models:
            report.append("🎉 **All models successfully standardized!**")
            report.append(
                (
                    "The automated standardization process has successfully transformed"
                    " all models"
                ),
            )
            report.append("according to the defined rules and validation criteria.")
        else:
            failed_models = [
                name for name, result in results.items() if not result.validation_passed
            ]
            report.append(
                (
                    f"⚠️ **{total_models - successful_models}"
                    " model(s) failed standardization**"
                ),
            )
            report.append(f"Failed models: {', '.join(failed_models)}")
            report.append(
                (
                    "Review the errors above and adjust the standardization rules as "
                    "needed."
                ),
            )

        return "\n".join(report)

    def save_report(
        self,
        report: str,
        output_path: str = "docs/automated_standardization.md",
    ) -> None:
        """Save the standardization report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with Path(output_file).open("w", encoding="utf-8") as f:
            f.write(report)

        logger.info("Standardization report saved to: %s", output_file)


def main() -> None:
    """Run the model standardization."""
    engine = AutomatedStandardizationEngine()

    try:
        logger.info("Starting automated standardization process...")
        logger.info("Models to standardize: %s", ", ".join(engine.models))
        logger.info("")

        # Standardize all models
        results = engine.standardize_all_models()

        # Generate and save report
        logger.info("Generating standardization report...")
        report = engine.generate_standardization_report(results)
        engine.save_report(report)

        # Print summary
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_mappings = sum(
            r.categories_mapped + r.subcategories_mapped for r in results.values()
        )

        logger.info("")
        logger.info("Standardization Summary:")
        logger.info("- Models processed: %s", len(results))
        logger.info("- Successfully standardized: %s", successful_models)
        logger.info("- Failed: %s", len(results) - successful_models)
        logger.info("- Total mappings applied: %s", total_mappings)
        logger.info(".1f")

        if successful_models == len(results):
            logger.info("🎉 All models successfully standardized!")
        else:
            logger.info("⚠️ Some standardizations failed. Check the report for details.")

    except Exception:
        logger.exception("Error during standardization")
        raise


if __name__ == "__main__":
    main()
