# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Log prepared and calculated table structure for local diagnostics."""

import logging

import polars as pl

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Inspect native table schemas and the detailed unit-cost output."""
    # Load the ground truth data
    ground_truth_path = "data/prepared/ground_truth.parquet"
    ground_truth_df = pl.read_parquet(ground_truth_path)

    logger.info("Ground truth shape: %s", ground_truth_df.shape)
    logger.info("Ground truth columns: %s", ground_truth_df.columns)

    # Initialize the CalculationEngine
    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)

    # Run the engine to get the calculated results
    results_df, errors = engine.run_engine("Detailed Table")

    if results_df is None:
        logger.error("Error: Engine returned None results")
        logger.info("Errors: %s", errors)
        return

    logger.info("Results shape: %s", results_df.shape)
    logger.info("Results columns (first 10): %s", results_df.columns[:10])

    # Find the unit cost column
    unit_cost_col = None
    for col in results_df.columns:
        if "Unit Cost (AUD $/unit)" in col:
            unit_cost_col = col
            break

    logger.info("Unit cost column: %s", unit_cost_col)
    if unit_cost_col:
        logger.info("Unit cost data type: %s", type(results_df[unit_cost_col]))
        logger.info("Unit cost shape: %s", results_df[unit_cost_col].shape)
        logger.info("First 5 values: %s", results_df[unit_cost_col].head())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
