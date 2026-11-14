#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Phase 3: Data Quality Enhancement and Template Compliance.

This script implements comprehensive data transformation to ensure standardized models
comply with the established templates and achieve proper data quality standards.

Key improvements:
1. Template-compliant column structure
2. Missing data population from source
3. Excel formula evaluation/replacement
4. Column ordering and cleanup
5. Data validation and quality gates
"""

import json
import logging
import traceback
from pathlib import Path

import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataQualityEnhancer:
    """Enhanced data transformation engine for Phase 3."""

    def __init__(
        self,
        template_path: str = "config/templates/base_template.json",
    ) -> None:
        """Load the template used for data enhancement."""
        self.template_path = Path(template_path)
        self.template = self.load_template()
        self.models = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]

    def load_template(self) -> dict:
        """Load the base template configuration."""
        if not self.template_path.exists():
            message = f"Template file not found: {self.template_path}"
            raise FileNotFoundError(message)

        with self.template_path.open(encoding="utf-8") as f:
            return json.load(f)

    def enhance_model_data(self, model_name: str) -> pd.DataFrame | None:
        """Enhance a single model's data to meet template requirements."""
        logger.info("Enhancing data quality for %s", model_name)

        try:
            # Load original data
            original_df = self.load_original_model(model_name)
            if original_df is None:
                return None

            # Apply comprehensive transformations
            enhanced_df = original_df.copy()

            # Step 1: Clean Excel formulas and extract meaningful data
            enhanced_df = self.clean_excel_formulas(enhanced_df)

            # Step 2: Restructure columns to match template
            enhanced_df = self.restructure_columns(enhanced_df, model_name)

            # Step 3: Populate missing required columns
            enhanced_df = self.populate_missing_columns(enhanced_df, model_name)

            # Step 4: Clean and validate data
            enhanced_df = self.clean_and_validate_data(enhanced_df)

            # Step 5: Reorder columns according to template
            enhanced_df = self.reorder_columns(enhanced_df)

            logger.info(
                "Enhanced %s: %s rows, %s columns",
                model_name,
                len(enhanced_df),
                len(enhanced_df.columns),
            )

        except Exception:
            logger.exception("Error enhancing %s", model_name)

            logger.exception("Traceback: %s", traceback.format_exc())
            return None
        else:
            return enhanced_df

    def load_original_model(self, model_name: str) -> pd.DataFrame | None:
        """Load original model data from detailed table."""
        data_path = Path("data/Detailed Table.csv")

        if not data_path.exists():
            logger.error("Data file not found: %s", data_path)
            return None

        try:
            # Load and find the model's data
            df = pd.read_csv(data_path, header=None)

            # Find header row
            header_row_idx = None
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

    def clean_excel_formulas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean Excel formulas and extract meaningful data."""
        df_clean = df.copy()

        # Replace Excel formulas with appropriate values or empty strings
        for col in df_clean.columns:
            try:
                if df_clean[col].dtype == "object":
                    # Replace Excel formula references with empty strings
                    df_clean[col] = (
                        df_clean[col]
                        .astype(str)
                        .apply(
                            lambda x: (
                                ""
                                if isinstance(x, str) and x.startswith("=") and "!" in x
                                else x
                            ),
                        )
                    )

                    # Clean up empty strings and NaN values
                    df_clean[col] = df_clean[col].replace(["nan", "NaN", "None"], "")
            except Exception as e:
                logger.warning("Error processing column %s: %s", col, e, exc_info=True)
                # Keep original column if processing fails

        return df_clean

    def restructure_columns(self, df: pd.DataFrame, _model_name: str) -> pd.DataFrame:
        """Restructure columns to match template requirements."""
        df_structured = df.copy()

        # Handle duplicate column names by keeping only the first occurrence
        seen_columns = set()
        columns_to_drop = []

        for col in df_structured.columns:
            if col in seen_columns:
                columns_to_drop.append(col)
            else:
                seen_columns.add(col)

        if columns_to_drop:
            logger.info("Dropping duplicate columns: %s", columns_to_drop)
            df_structured = df_structured.drop(columns=columns_to_drop)

        logger.info("After restructure - columns: %s", list(df_structured.columns))

        # Rename columns according to mappings
        column_mappings = {
            "Test": "Test",
            "Category": "Category",
            "Sub-Category": "Sub-Category",
            "Step": "Item",  # Map Step to Item
            "Price (AUD $/unit)": "Unit Cost (AUD $/unit)",  # Alternative name
        }

        df_structured = df_structured.rename(columns=column_mappings)

        # After renaming, handle any remaining duplicates
        seen_columns = set()
        columns_to_drop = []

        for col in df_structured.columns:
            if col in seen_columns:
                columns_to_drop.append(col)
            else:
                seen_columns.add(col)

        if columns_to_drop:
            logger.info(
                "Dropping duplicate columns after renaming: %s",
                columns_to_drop,
            )
            df_structured = df_structured.drop(columns=columns_to_drop)

        return df_structured

    def populate_missing_columns(
        self,
        df: pd.DataFrame,
        _model_name: str,
    ) -> pd.DataFrame:
        """Populate missing required columns with appropriate defaults."""
        df_populated = df.copy()

        # Add missing required columns with default values
        for col in self.template["required_columns"]:
            if col not in df_populated.columns:
                if col == "Units":
                    df_populated[col] = 1.0  # Default to 1 unit
                elif col == "Total Cost (AUD)":
                    # Calculate total cost if unit cost exists
                    if "Unit Cost (AUD $/unit)" in df_populated.columns:
                        unit_cost_series = pd.to_numeric(
                            df_populated["Unit Cost (AUD $/unit)"],
                            errors="coerce",
                        ).fillna(0)
                        units_series = pd.to_numeric(
                            df_populated.get(
                                "Units",
                                pd.Series([1.0] * len(df_populated)),
                            ),
                            errors="coerce",
                        ).fillna(1)
                        df_populated[col] = unit_cost_series * units_series
                    else:
                        df_populated[col] = 0.0
                elif col in ["Item", "Notes"]:
                    df_populated[col] = ""  # Empty string for text fields
                else:
                    df_populated[col] = ""  # Default empty for other fields

        # Add optional columns if they don't exist
        for col in self.template["optional_columns"]:
            if col not in df_populated.columns:
                df_populated[col] = ""

        return df_populated

    def clean_and_validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate the data."""
        df_clean = df.copy()

        # Convert numeric columns
        numeric_columns = ["Unit Cost (AUD $/unit)", "Units", "Total Cost (AUD)"]
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(
                    0.0,
                )

        # Clean text columns
        text_columns = ["Test", "Category", "Sub-Category", "Item", "Notes"]
        for col in text_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()

        # Remove completely empty rows (except for Test column)
        non_test_cols = [col for col in df_clean.columns if col != "Test"]
        return df_clean.dropna(subset=non_test_cols, how="all")

    def reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns according to template specification."""
        df_ordered = df.copy()

        # Get the desired column order from template
        desired_order = self.template["column_order"]

        # Reorder existing columns to match template
        existing_columns = [col for col in desired_order if col in df_ordered.columns]
        new_columns = [col for col in df_ordered.columns if col not in desired_order]

        final_order = existing_columns + new_columns
        df_ordered = df_ordered[final_order]

        return df_ordered

    def save_enhanced_model(
        self,
        model_name: str,
        df: pd.DataFrame,
        output_dir: str = "data/enhanced",
    ) -> None:
        """Save the enhanced model to file."""
        if df is None or df.empty:
            logger.warning("Cannot save empty enhanced model: %s", model_name)
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_enhanced.csv"
        )
        filepath = output_path / filename

        df.to_csv(filepath, index=False)
        logger.info("Saved enhanced model to: %s", filepath)

    def enhance_all_models(self) -> dict[str, pd.DataFrame]:
        """Enhance all models and return results."""
        results = {}

        for model_name in self.models:
            try:
                enhanced_df = self.enhance_model_data(model_name)
                if enhanced_df is not None:
                    results[model_name] = enhanced_df
                    self.save_enhanced_model(model_name, enhanced_df)
                    logger.info("✅ Enhanced %s", model_name)
                else:
                    logger.error("❌ Failed to enhance %s", model_name)

            except Exception:
                logger.exception("Error enhancing %s", model_name)

        return results


def main() -> None:
    """Run the phase three enhancement workflow."""
    enhancer = DataQualityEnhancer()

    try:
        logger.info("Starting Phase 3: Data Quality Enhancement")
        logger.info("Models to enhance: %s", ", ".join(enhancer.models))
        logger.info("")

        # Enhance all models
        results = enhancer.enhance_all_models()

        # Print summary
        successful_models = len(results)
        total_rows = sum(len(df) for df in results.values())

        logger.info("")
        logger.info("Phase 3 Enhancement Summary:")
        logger.info("- Models enhanced: %s/%s", successful_models, len(enhancer.models))
        logger.info("- Total rows processed: %s", total_rows)
        logger.info(
            "- Average columns per model: %s",
            format(
                sum(len(df.columns) for df in results.values())
                / max(1, successful_models),
                ".1f",
            ),
        )

        if successful_models == len(enhancer.models):
            logger.info("🎉 All models successfully enhanced!")
        else:
            logger.info("⚠️ Some enhancements failed. Check the logs for details.")

    except Exception:
        logger.exception("Error during Phase 3 enhancement")
        raise


if __name__ == "__main__":
    main()
