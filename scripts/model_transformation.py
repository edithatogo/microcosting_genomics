#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Model Transformation Engine.

This script transforms original genomic models into standardized format
using the templates and rules defined in the configuration files.

The transformation process:
1. Loads original model data
2. Applies standardization mappings
3. Validates against templates
4. Generates standardized output files
5. Creates transformation reports
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

COST_COMPARISON_TOLERANCE = 0.01

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class TransformationResult:
    """Container for transformation results."""

    model_name: str
    original_rows: int
    transformed_rows: int
    transformations_applied: dict[str, int]
    validation_passed: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    output_path: str | None


@dataclass
class ModelTemplate:
    """Template for a standardized model."""

    name: str
    required_columns: list[str]
    optional_columns: list[str]
    column_order: list[str]
    data_types: dict[str, str]
    validation_rules: dict[str, Any]
    default_values: dict[str, Any]


class ModelTransformationEngine:
    """Engine for transforming models to standardized format."""

    def __init__(
        self,
        config_path: str = "config/standard_categories.yaml",
        templates_dir: str = "config/templates",
    ) -> None:
        """Set the category configuration and model output location."""
        self.config_path = Path(config_path)
        self.templates_dir = Path(templates_dir)
        self.config = self.load_config()
        self.templates = self.load_templates()

        self.models = [
            "Panel",
            "WES (P)",
            "WES (T)",
            "WGS",
            "WGS (T)",
        ]

    def load_config(self) -> dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            message = f"Configuration file not found: {self.config_path}"
            raise FileNotFoundError(message)

        with self.config_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_templates(self) -> dict[str, ModelTemplate]:
        """Load all available templates."""
        templates = {}

        if not self.templates_dir.exists():
            logger.warning("Templates directory not found: %s", self.templates_dir)
            return templates

        # Load all JSON template files
        for json_file in self.templates_dir.glob("*_template.json"):
            try:
                with Path(json_file).open(encoding="utf-8") as f:
                    template_data = json.load(f)

                # Convert default_values back from strings
                default_values = {}
                for k, v in template_data["default_values"].items():
                    if v == "NaT":
                        default_values[k] = pd.NaT
                    elif v == "":
                        default_values[k] = ""
                    else:
                        try:
                            # Try to convert numeric strings
                            if "." in str(v):
                                default_values[k] = float(v)
                            else:
                                default_values[k] = int(v)
                        except ValueError, TypeError:
                            default_values[k] = v

                template = ModelTemplate(
                    name=template_data["name"],
                    required_columns=template_data["required_columns"],
                    optional_columns=template_data["optional_columns"],
                    column_order=template_data["column_order"],
                    data_types=template_data["data_types"],
                    validation_rules=template_data["validation_rules"],
                    default_values=default_values,
                )

                template_key = template_data["name"].replace("_template", "")
                templates[template_key] = template

            except Exception:
                logger.exception("Error loading template %s", json_file)

        return templates

    def get_template_for_model(self, model_name: str) -> ModelTemplate:
        """Get the appropriate template for a model."""
        # Try model-specific template first
        model_key = (
            model_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        )
        if model_key in self.templates:
            return self.templates[model_key]

        # Fall back to base template
        if "base" in self.templates:
            return self.templates["base"]

        message = f"No suitable template found for model {model_name}"
        raise ValueError(message)

    def load_original_model(self, model_name: str) -> pd.DataFrame | None:
        """Load original model data."""
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

    def apply_standardization_mappings(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict[str, int]]:
        """Apply all standardization mappings to the dataframe."""
        transformations = {
            "category_mappings": 0,
            "subcategory_mappings": 0,
            "data_type_conversions": 0,
            "missing_value_fills": 0,
        }

        df_copy = df.copy()

        # Apply category mappings
        category_mappings = self.config.get("standardization_mappings", {}).get(
            "category_mappings",
            {},
        )
        if "Category" in df_copy.columns and category_mappings:
            original_categories = df_copy["Category"].copy()
            df_copy["Category"] = df_copy["Category"].map(
                lambda x: category_mappings.get(x, x) if pd.notna(x) else x,
            )
            transformations["category_mappings"] = sum(
                1
                for orig, mapped in zip(
                    original_categories,
                    df_copy["Category"],
                    strict=False,
                )
                if orig != mapped and pd.notna(orig) and orig in category_mappings
            )

        # Apply subcategory mappings
        subcategory_mappings = self.config.get("standardization_mappings", {}).get(
            "subcategory_mappings",
            {},
        )
        if "Sub-Category" in df_copy.columns and subcategory_mappings:
            original_subcats = df_copy["Sub-Category"].copy()
            df_copy["Sub-Category"] = df_copy["Sub-Category"].map(
                lambda x: subcategory_mappings.get(x, x) if pd.notna(x) else x,
            )
            transformations["subcategory_mappings"] = sum(
                1
                for orig, mapped in zip(
                    original_subcats,
                    df_copy["Sub-Category"],
                    strict=False,
                )
                if orig != mapped and pd.notna(orig) and orig in subcategory_mappings
            )

        return df_copy, transformations

    def _apply_type_conversions(
        self,
        df_copy: pd.DataFrame,
        template: ModelTemplate,
        transformations: dict[str, int],
    ) -> None:
        # Apply data type conversions
        for col, dtype in template.data_types.items():
            if col in df_copy.columns:
                try:
                    if dtype == "category":
                        # Get unique values including defaults, then create categorical
                        unique_values = df_copy[col].dropna().unique()
                        df_copy[col] = pd.Categorical(
                            df_copy[col],
                            categories=unique_values,
                        )
                        transformations["data_types_converted"] += 1
                    elif dtype == "datetime64[ns]":
                        df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce")
                        transformations["data_types_converted"] += 1
                    elif dtype == "float64":
                        df_copy[col] = pd.to_numeric(
                            df_copy[col],
                            errors="coerce",
                        ).astype("float64")
                        transformations["data_types_converted"] += 1
                    elif dtype == "int64":
                        df_copy[col] = pd.to_numeric(
                            df_copy[col],
                            errors="coerce",
                        ).astype("int64")
                        transformations["data_types_converted"] += 1
                    elif dtype == "string":
                        df_copy[col] = df_copy[col].astype("string")
                        transformations["data_types_converted"] += 1
                except Exception as e:
                    logger.warning(
                        "Could not convert column %s to %s: %s",
                        col,
                        dtype,
                        e,
                        exc_info=True,
                    )

    def apply_template_formatting(
        self,
        df: pd.DataFrame,
        template: ModelTemplate,
    ) -> tuple[pd.DataFrame, dict[str, int]]:
        """Apply template formatting to the dataframe."""
        transformations = {
            "columns_reordered": 0,
            "missing_columns_added": 0,
            "data_types_converted": 0,
            "default_values_applied": 0,
        }

        df_copy = df.copy()

        # Add missing columns with default values
        for col in template.column_order:
            if col not in df_copy.columns:
                default_value = template.default_values.get(col, "")
                df_copy[col] = default_value
                transformations["missing_columns_added"] += 1

        # Reorder columns according to template
        existing_columns = [
            col for col in template.column_order if col in df_copy.columns
        ]
        df_copy = df_copy[existing_columns]
        transformations["columns_reordered"] = 1

        # Fill missing values with defaults BEFORE type conversion
        for col, default_value in template.default_values.items():
            if col in df_copy.columns:
                if pd.isna(default_value):
                    # Don't fill NaT values
                    continue
                mask = df_copy[col].isna()
                if mask.any():
                    df_copy.loc[mask, col] = default_value
                    transformations["default_values_applied"] += mask.sum()

        self._apply_type_conversions(df_copy, template, transformations)

        return df_copy, transformations

    def _append_cost_warnings(self, df: pd.DataFrame, warnings: list[str]) -> None:
        # Check cost calculations if numeric columns exist
        if (
            "Unit Cost (AUD $/unit)" in df.columns
            and "Units" in df.columns
            and "Total Cost (AUD)" in df.columns
        ):
            try:
                # Convert to numeric for calculation check
                unit_cost = pd.to_numeric(df["Unit Cost (AUD $/unit)"], errors="coerce")
                units = pd.to_numeric(df["Units"], errors="coerce")
                total_cost = pd.to_numeric(df["Total Cost (AUD)"], errors="coerce")

                # Check if total = unit * units (allowing for small rounding
                # differences)
                calculated_total = unit_cost * units
                mask = (~pd.isna(calculated_total)) & (~pd.isna(total_cost))
                if mask.any():
                    diff = np.abs(calculated_total[mask] - total_cost[mask])
                    max_diff = diff.max()
                    if (
                        max_diff > COST_COMPARISON_TOLERANCE
                    ):  # Allow for 1 cent difference
                        warnings.append(".2f")
            except Exception as e:
                logger.exception("Could not complete validate transformed model")
                warnings.append(f"Could not validate cost calculations: {e}")

    def _append_subcategory_warnings(
        self,
        df: pd.DataFrame,
        template: ModelTemplate,
        present_categories: set[str],
        warnings: list[str],
    ) -> None:
        # Check minimum subcategories
        min_subcategories = template.validation_rules.get("minimum_subcategories", {})
        for category, min_count in min_subcategories.items():
            if category in present_categories:
                subcats = (
                    df[df["Category"] == category]["Sub-Category"].dropna().unique()
                )
                if len(subcats) < min_count:
                    warnings.append(
                        "Category '"
                        f"{category}"
                        "' has "
                        f"{len(subcats)}"
                        " subcategories, minimum is "
                        f"{min_count}",
                    )

    def validate_transformed_model(
        self,
        df: pd.DataFrame,
        template: ModelTemplate,
        _model_name: str,
    ) -> tuple[bool, list[str], list[str]]:
        """Validate the transformed model against template rules."""
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("Transformed model is empty")
            return False, errors, warnings

        # Check required columns
        missing_required = set(template.required_columns) - set(df.columns)
        if missing_required:
            errors.append(f"Missing required columns: {', '.join(missing_required)}")

        # Check required categories
        required_categories = template.validation_rules.get("required_categories", [])
        present_categories = set(df["Category"].dropna().unique())
        missing_categories = set(required_categories) - present_categories
        if missing_categories:
            errors.append(
                f"Missing required categories: {', '.join(missing_categories)}",
            )

        self._append_subcategory_warnings(df, template, present_categories, warnings)

        # Check for invalid categories
        standard_categories = set(
            template.validation_rules.get("standard_categories", []),
        )
        invalid_categories = present_categories - standard_categories
        if invalid_categories:
            warnings.append(
                f"Non-standard categories present: {', '.join(invalid_categories)}",
            )

        # Check data integrity
        for col in template.required_columns:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    warnings.append(f"Column '{col}' has {null_count} null values")

        self._append_cost_warnings(df, warnings)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def transform_model(self, model_name: str) -> TransformationResult:
        """Transform a single model to standardized format."""
        logger.info("Starting transformation of %s", model_name)

        # Load original data
        original_df = self.load_original_model(model_name)
        if original_df is None:
            return TransformationResult(
                model_name=model_name,
                original_rows=0,
                transformed_rows=0,
                transformations_applied={},
                validation_passed=False,
                validation_errors=["Could not load original model data"],
                validation_warnings=[],
                output_path=None,
            )

        original_rows = len(original_df)

        # Get appropriate template
        try:
            template = self.get_template_for_model(model_name)
        except ValueError as e:
            return TransformationResult(
                model_name=model_name,
                original_rows=original_rows,
                transformed_rows=0,
                transformations_applied={},
                validation_passed=False,
                validation_errors=[str(e)],
                validation_warnings=[],
                output_path=None,
            )

        # Apply standardization mappings
        df_step1, mappings_transforms = self.apply_standardization_mappings(original_df)

        # Apply template formatting
        df_step2, template_transforms = self.apply_template_formatting(
            df_step1,
            template,
        )

        # Combine transformations
        all_transformations = {**mappings_transforms, **template_transforms}

        # Validate the transformed model
        is_valid, errors, warnings = self.validate_transformed_model(
            df_step2,
            template,
            model_name,
        )

        # Save transformed model
        output_path = None
        if is_valid and not df_step2.empty:
            output_dir = Path("data/standardized")
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = (
                f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
                "_standardized.csv"
            )
            output_path = str(output_dir / filename)

            df_step2.to_csv(output_path, index=False)
            logger.info("Saved transformed model to: %s", output_path)

        result = TransformationResult(
            model_name=model_name,
            original_rows=original_rows,
            transformed_rows=len(df_step2) if df_step2 is not None else 0,
            transformations_applied=all_transformations,
            validation_passed=is_valid,
            validation_errors=errors,
            validation_warnings=warnings,
            output_path=output_path,
        )

        logger.info(
            "Completed transformation of %s: %s rows, %s transformations applied",
            model_name,
            result.transformed_rows,
            sum(all_transformations.values()),
        )
        return result

    def transform_all_models(self) -> dict[str, TransformationResult]:
        """Transform all models to standardized format."""
        results = {}

        for model_name in self.models:
            try:
                result = self.transform_model(model_name)
                results[model_name] = result

                status = "✅" if result.validation_passed else "❌"
                logger.info("%s Transformed %s", status, model_name)

                if result.validation_errors:
                    logger.error("  Errors: %s", ", ".join(result.validation_errors))
                if result.validation_warnings:
                    logger.warning(
                        "  Warnings: %s",
                        ", ".join(result.validation_warnings),
                    )

            except Exception as e:
                logger.exception("Failed to transform %s", model_name)
                results[model_name] = TransformationResult(
                    model_name=model_name,
                    original_rows=0,
                    transformed_rows=0,
                    transformations_applied={},
                    validation_passed=False,
                    validation_errors=[str(e)],
                    validation_warnings=[],
                    output_path=None,
                )

        return results

    def _append_model_results(
        self,
        report: list[str],
        results: list[TransformationResult],
    ) -> None:
        # Individual model results
        report.append("## Model Transformation Results")
        for model_name, result in results.items():
            status = "✅ PASS" if result.validation_passed else "❌ FAIL"
            report.append(f"### {model_name} - {status}")
            report.append(f"- **Original Rows**: {result.original_rows}")
            report.append(f"- **Transformed Rows**: {result.transformed_rows}")
            report.append(
                "- **Transformations Applied**: "
                f"{sum(result.transformations_applied.values())}",
            )

            if result.transformations_applied:
                report.append("- **Transformation Details**:")
                for transform_type, count in result.transformations_applied.items():
                    if count > 0:
                        report.append(
                            f"  - {transform_type.replace('_', ' ').title()}: {count}",
                        )

            if result.validation_errors:
                report.append("- **Errors**:")
                report.extend(f"  - {error}" for error in result.validation_errors)

            if result.validation_warnings:
                report.append("- **Warnings**:")
                report.extend(
                    f"  - {warning}" for warning in result.validation_warnings
                )

            if result.output_path:
                report.append(f"- **Output File**: {result.output_path}")

            report.append("")

    def generate_transformation_report(
        self,
        results: dict[str, TransformationResult],
    ) -> str:
        """Generate a comprehensive transformation report."""
        report = []
        report.append("# Model Transformation Report")
        report.append(
            "Generated: "
            f"{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        )
        report.append("")

        # Summary
        total_models = len(results)
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_transformations = sum(
            sum(r.transformations_applied.values()) for r in results.values()
        )

        report.append("## Summary")
        report.append(f"- **Models Processed**: {total_models}")
        report.append(f"- **Successfully Transformed**: {successful_models}")
        report.append(
            f"- **Success Rate**: {successful_models / total_models * 100:.1f}%",
        )
        report.append(f"- **Total Transformations Applied**: {total_transformations}")
        report.append("")

        self._append_model_results(report, results)

        # Overall assessment
        report.append("## Overall Assessment")

        if successful_models == total_models:
            report.append("🎉 **All models successfully transformed!**")
            report.append(
                "The transformation engine has successfully converted all models",
            )
            report.append(
                "to standardized format according to the defined templates and rules.",
            )
        else:
            failed_models = [
                name for name, result in results.items() if not result.validation_passed
            ]
            report.append(
                "⚠️ **"
                f"{total_models - successful_models}"
                " model(s) failed transformation**",
            )
            report.append(f"Failed models: {', '.join(failed_models)}")
            report.append(
                "Review the errors above and adjust the templates or "
                "transformation rules as needed.",
            )

        # Transformation statistics
        if total_transformations > 0:
            report.append("")
            report.append("## Transformation Statistics")
            all_transform_types = set()
            for result in results.values():
                all_transform_types.update(result.transformations_applied.keys())

            for transform_type in sorted(all_transform_types):
                total_count = sum(
                    r.transformations_applied.get(transform_type, 0)
                    for r in results.values()
                )
                if total_count > 0:
                    report.append(
                        "- **"
                        f"{transform_type.replace('_', ' ').title()}"
                        "**: "
                        f"{total_count}",
                    )

        return "\n".join(report)

    def save_report(
        self,
        report: str,
        output_path: str = "docs/model_transformation.md",
    ) -> None:
        """Save the transformation report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with Path(output_file).open("w", encoding="utf-8") as f:
            f.write(report)

        logger.info("Transformation report saved to: %s", output_file)


def main() -> None:
    """Transform the model data and save the results."""
    engine = ModelTransformationEngine()

    try:
        logger.info("Starting model transformation process...")
        logger.info("Models to transform: %s", ", ".join(engine.models))
        logger.info("")

        # Transform all models
        results = engine.transform_all_models()

        # Generate and save report
        logger.info("Generating transformation report...")
        report = engine.generate_transformation_report(results)
        engine.save_report(report)

        # Print summary
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_transformations = sum(
            sum(r.transformations_applied.values()) for r in results.values()
        )

        logger.info("")
        logger.info("Transformation Summary:")
        logger.info("- Models processed: %s", len(results))
        logger.info("- Successfully transformed: %s", successful_models)
        logger.info("- Failed: %s", len(results) - successful_models)
        logger.info("- Total transformations applied: %s", total_transformations)
        logger.info(".1f")

        if successful_models == len(results):
            logger.info("🎉 All models successfully transformed!")
        else:
            logger.info("⚠️ Some transformations failed. Check the report for details.")

    except Exception:
        logger.exception("Error during transformation")
        raise


if __name__ == "__main__":
    main()
