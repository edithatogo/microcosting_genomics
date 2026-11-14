#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Prepare cleaned datasets from the microcosting workbooks using the new ETL pipeline.

This script replaces the original prepare_data.py with a modular ETL pipeline
that provides the same functionality while being more maintainable and extensible.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from genomics_microcosting.config import load_config
from genomics_microcosting.data_pipeline import DataPipeline
from genomics_microcosting.extractors import ExcelExtractor
from genomics_microcosting.loaders import MultiFormatLoader
from genomics_microcosting.transformers import (
    DataCleaner,
    HeaderNormalizer,
    ValidationChecker,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GenomicsDataCleaner(DataCleaner):
    """Custom data cleaner for genomics microcosting data with domain-specific logic."""

    def __init__(
        self,
        name: str,
        cleaning_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the table cleaner with its preparation rules."""
        if cleaning_config is None:
            cleaning_config = {
                "remove_duplicates": True,
                "handle_missing": "coerce",  # Convert invalid values to NaN
                "normalize_text": True,
                "string_columns": [
                    "test",
                    "category",
                    "sub_category",
                    "step",
                    "source",
                ],
            }
        super().__init__(name, cleaning_config)

    def transform(
        self,
        data: pd.DataFrame | dict[str, pd.DataFrame],
    ) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Apply genomics-specific data cleaning."""
        # First apply the parent class cleaning
        cleaned_data = super().transform(data)

        # Apply additional genomics-specific cleaning
        if isinstance(cleaned_data, dict):
            # Handle multiple sheets
            result = {}
            for sheet_name, df in cleaned_data.items():
                result[sheet_name] = self._apply_genomics_cleaning(df)
            return result
        # Handle single DataFrame
        return self._apply_genomics_cleaning(cleaned_data)

    def _apply_genomics_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply genomics-specific data cleaning to a single DataFrame."""
        # Apply type conversion with better error handling for genomics data
        for col in df.columns:
            # Preserve string columns as specified in config
            if col.lower() in self.cleaning_config.get("string_columns", []):
                # Keep as string if it contains non-numeric data
                try:
                    if df[col].notna().any():
                        sample_values = df[col].dropna().head(10)
                        if any(
                            isinstance(val, str) or pd.isna(val)
                            for val in sample_values.to_numpy()
                        ):
                            continue  # Keep as object/string
                except TypeError, ValueError:
                    logger.debug(
                        "Retained column values after a conversion error",
                        exc_info=True,
                    )

            # Apply numeric conversion for other columns
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except TypeError, ValueError:
                # If conversion fails, keep original values
                logger.debug(
                    "Retained column values after a conversion error",
                    exc_info=True,
                )

        return df


def create_prepare_data_pipeline(workbook_key: str = "validation") -> DataPipeline:
    """Create a configured ETL pipeline for preparing genomics data."""
    logger.info("Creating ETL pipeline for workbook: %s", workbook_key)

    # Load configuration
    config = load_config()

    if workbook_key not in config["workbooks"]:
        message = f"Workbook '{workbook_key}' not found in configuration"
        raise KeyError(message)

    workbook_config = config["workbooks"][workbook_key]
    source_file = Path(workbook_config["path"])
    sheet_configs = workbook_config["sheets"]

    # Create pipeline
    pipeline = DataPipeline(f"prepare_data_{workbook_key}")

    # Add extractor for Excel file
    excel_extractor = ExcelExtractor(
        name="excel_extractor",
        source_path=source_file,
        sheet_configs=sheet_configs,
        workbook_key=workbook_key,
    )
    pipeline.add_extractor(excel_extractor)

    # Add transformers
    header_normalizer = HeaderNormalizer(
        name="header_normalizer",
        column_mappings={
            # Add any specific column mappings if needed
        },
    )
    pipeline.add_transformer(header_normalizer)

    # Custom data cleaner for genomics data
    data_cleaner = GenomicsDataCleaner(
        name="genomics_data_cleaner",
    )
    pipeline.add_transformer(data_cleaner)

    # Add validation
    validation_checker = ValidationChecker(
        name="validation_checker",
        validation_rules={
            "required_columns": [],  # Add required columns if any
            "numeric_columns": [],  # Add numeric columns for validation
        },
    )
    pipeline.add_transformer(validation_checker)

    # Add loader for multiple formats
    output_dir = Path("data/prepared")
    multi_loader = MultiFormatLoader(
        name="multi_format_loader",
        target_path=output_dir,
        formats=["parquet", "csv"],
    )
    pipeline.add_loader(multi_loader)

    return pipeline


def main() -> None:
    """Create cleaned Parquet and CSV datasets using the ETL pipeline."""
    logger.info("Starting data preparation with ETL pipeline...")

    config = load_config()
    workbook_key = config.get("default_workbook", "validation")

    try:
        # Create and run the ETL pipeline
        pipeline = create_prepare_data_pipeline(workbook_key)
        results = pipeline.run()

        logger.info("Data preparation completed successfully!")
        logger.info("Pipeline results: %s", results)

        # Log summary of processed sheets
        if isinstance(results, dict):
            for sheet_name, df in results.items():
                logger.info(
                    "Processed sheet '%s': %s rows, %s columns",
                    sheet_name,
                    len(df),
                    len(df.columns),
                )

    except Exception:
        logger.exception("Data preparation failed")
        raise


def compare_with_original() -> None:
    """Compare the ETL pipeline output with the original prepare_data.py output."""
    logger.info("Comparing ETL pipeline output with original prepare_data.py...")

    # This function would compare the outputs to ensure identical results
    # For now, just log that this comparison should be done
    logger.info(
        "TODO: Implement detailed comparison with original prepare_data.py output",
    )
    logger.info("This should verify that:")
    logger.info("1. All sheets are processed identically")
    logger.info("2. Column names match exactly")
    logger.info("3. Data values match exactly")
    logger.info("4. Row counts match exactly")
    logger.info("5. Data types are preserved correctly")


if __name__ == "__main__":
    main()
    compare_with_original()
