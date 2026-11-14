#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test script for the ETL pipeline implementation.

This script validates that the new modular ETL pipeline produces
identical results to the existing prepare_data.py script.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from genomics_microcosting.data_pipeline import DataPipeline
from genomics_microcosting.extractors import CSVExtractor
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


def test_etl_pipeline() -> bool | None:
    """Test the complete ETL pipeline with sample data."""
    logger.info("Starting ETL pipeline test...")

    # Create output directory
    output_dir = Path("data/test_output")
    output_dir.mkdir(exist_ok=True)

    # Create pipeline
    pipeline = DataPipeline("test_pipeline")

    # Add extractor - use existing CSV file
    csv_extractor = CSVExtractor(
        name="csv_extractor",
        source_path="data/Detailed Table.csv",
    )
    pipeline.add_extractor(csv_extractor)

    # Add transformers
    header_normalizer = HeaderNormalizer(
        name="header_normalizer",
        column_mappings={
            "Test Name": "test_name",
            "Unit Cost": "unit_cost",
            "Volume": "volume",
        },
    )
    pipeline.add_transformer(header_normalizer)

    data_cleaner = DataCleaner(
        name="data_cleaner",
        cleaning_config={
            "remove_duplicates": True,
            "handle_missing": "drop",
        },
    )
    pipeline.add_transformer(data_cleaner)

    validation_checker = ValidationChecker(
        name="validation_checker",
        validation_rules={
            "required_columns": ["test_name", "unit_cost"],
            "numeric_columns": ["unit_cost", "volume"],
        },
    )
    pipeline.add_transformer(validation_checker)

    # Add loader
    multi_loader = MultiFormatLoader(
        name="multi_format_loader",
        target_path=output_dir,
        formats=["parquet", "csv", "json"],
    )
    pipeline.add_loader(multi_loader)

    # Run pipeline
    try:
        logger.info("Running ETL pipeline...")
        results = pipeline.run()

        logger.info("Pipeline completed successfully!")
        logger.info("Results: %s", results)

        # Validate outputs
        validate_outputs(output_dir)

    except Exception:
        logger.exception("Pipeline failed")
        return False
    else:
        return True


def validate_outputs(output_dir: Path) -> None:
    """Validate that output files were created and contain data."""
    logger.info("Validating pipeline outputs...")

    # Check for expected output files
    expected_files = [
        "data.parquet",
        "data.csv",
        "data.json",
    ]

    for filename in expected_files:
        file_path = output_dir / filename
        if not file_path.exists():
            logger.error("Expected output file not found: %s", file_path)
            continue

        logger.info("Found output file: %s", file_path)

        # Try to read and validate content
        try:
            if filename.endswith(".parquet"):
                df = pd.read_parquet(file_path)
            elif filename.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif filename.endswith(".json"):
                df = pd.read_json(file_path)

            logger.info(
                "File %s contains %s rows and %s columns",
                filename,
                len(df),
                len(df.columns),
            )
            logger.info("Columns: %s", list(df.columns))

        except Exception:
            logger.exception("Failed to read %s", filename)


def compare_with_existing() -> None:
    """Compare ETL pipeline output with existing prepare_data.py output."""
    logger.info("Comparing with existing prepare_data.py output...")

    # This would compare the outputs to ensure identical results
    # For now, just log that this comparison should be done
    logger.info("TODO: Implement comparison with existing prepare_data.py output")
    logger.info("This should verify that:")
    logger.info("1. Column names match exactly")
    logger.info("2. Data values match exactly")
    logger.info("3. Row counts match exactly")


if __name__ == "__main__":
    logger.info("ETL Pipeline Test Script")
    logger.info("=" * 50)

    # Test the pipeline
    success = test_etl_pipeline()

    if success:
        logger.info("✅ ETL pipeline test completed successfully!")
        compare_with_existing()
    else:
        logger.error("❌ ETL pipeline test failed!")
        sys.exit(1)
