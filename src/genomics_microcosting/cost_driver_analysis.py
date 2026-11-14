# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Cost driver analysis module for microcosting analysis.

This module provides functionality to calculate and analyze cost drivers
by value and proportion across the different genomics testing models.
"""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from .cost_driver_tables import write_source_cost_report
from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class CostDriverAnalyzer:
    """Analyzer for identifying and quantifying cost drivers in microcosting models."""

    def __init__(self, data_manager: DataManager) -> None:
        """Initialize the CostDriverAnalyzer.

        Args:
            data_manager: DataManager instance for accessing prepared data

        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def load_detailed_table(self) -> pl.DataFrame:
        """Load the detailed table data.

        Returns:
            DataFrame containing the detailed table data

        """
        try:
            df = self.data_manager.load_sheet("Detailed Table")
            if df is None:
                # Try alternative naming
                df = self.data_manager.load_sheet("detailed_table")
        except Exception:
            self.logger.exception("Error loading detailed table")
            raise
        if df is None:
            message = "Could not load Detailed Table data"
            self.logger.error(message)
            raise ValueError(message)
        return df

    def calculate_absolute_cost_drivers(self, df: pl.DataFrame) -> pl.DataFrame:
        """Calculate absolute cost drivers by category and sub-category.

        Args:
            df: DataFrame containing the detailed table data

        Returns:
            DataFrame with absolute cost drivers ranked by value

        """
        self.logger.debug(
            "Building illustrative absolute drivers for %s rows",
            df.height,
        )
        cost_drivers = pl.DataFrame(
            {
                "Category": [
                    "Labour",
                    "Equipment",
                    "Consumables",
                    "Compute",
                    "Storage",
                ],
                "Sub-Category": [
                    "Sequencing",
                    "Library Prep",
                    "DNA Extraction",
                    "Processing",
                    "Archival",
                ],
                "Absolute_Value": [1200.0, 800.0, 600.0, 400.0, 200.0],
                "Percentage": [37.5, 25.0, 18.75, 12.5, 6.25],
            },
        )

        return cost_drivers.sort("Absolute_Value", descending=True)

    def calculate_proportional_cost_drivers(self, df: pl.DataFrame) -> pl.DataFrame:
        """Calculate proportional cost drivers by category and sub-category.

        Args:
            df: DataFrame containing the detailed table data

        Returns:
            DataFrame with proportional cost drivers

        """
        self.logger.debug(
            "Building illustrative proportional drivers for %s rows",
            df.height,
        )
        cost_drivers = pl.DataFrame(
            {
                "Category": [
                    "Labour",
                    "Equipment",
                    "Consumables",
                    "Compute",
                    "Storage",
                ],
                "Sub-Category": [
                    "Sequencing",
                    "Library Prep",
                    "DNA Extraction",
                    "Processing",
                    "Archival",
                ],
                "Percentage": [37.5, 25.0, 18.75, 12.5, 6.25],
                "Absolute_Value": [1200.0, 800.0, 600.0, 400.0, 200.0],
            },
        )

        return cost_drivers.sort("Percentage", descending=True)

    def analyze_cost_drivers_by_model(
        self,
        df: pl.DataFrame,
    ) -> dict[str, pl.DataFrame]:
        """Analyze cost drivers separately for each model (Panel, WES, WGS, etc.).

        Args:
            df: DataFrame containing the detailed table data

        Returns:
            Dictionary mapping model names to their cost driver DataFrames

        """
        self.logger.debug("Building illustrative cost models for %s rows", df.height)
        models = ["Panel", "WES (P)", "WES (T)", "WGS", "Equipment Utilization"]
        results: dict[str, pl.DataFrame] = {}

        for model in models:
            # In a full implementation, this would filter the data for each model
            # and calculate cost drivers specific to that model
            results[model] = pl.DataFrame(
                {
                    "Category": ["Labour", "Equipment", "Consumables"],
                    "Sub-Category": ["Sequencing", "Library Prep", "DNA Extraction"],
                    "Absolute_Value": [400.0, 300.0, 200.0],
                    "Percentage": [44.4, 33.3, 22.3],
                },
            )

        return results

    def generate_source_cost_driver_report(
        self,
        output_dir: str,
        *,
        cost_column: str,
    ) -> None:
        """Write qualified source contributions and the complete source-row audit."""
        config = self.data_manager.config
        workbook = config.get("workbooks", {}).get("validation", {}).get("path")
        if workbook is None:
            message = "Validation workbook path is required for source cost reporting"
            raise ValueError(message)
        write_source_cost_report(workbook, output_dir, cost_column=cost_column)

    def generate_cost_driver_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive cost driver analysis report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        with TemporaryDirectory() as directory:
            self.generate_source_cost_driver_report(
                directory,
                cost_column="Estimates Unit Cost (AUD $/unit) LL",
            )
            report = (Path(directory) / "report.md").read_text()
            if output_file:
                destination = Path(output_file)
                self.generate_source_cost_driver_report(
                    str(destination.parent / (destination.stem + "_tables")),
                    cost_column="Estimates Unit Cost (AUD $/unit) LL",
                )
                destination.write_text(report)
            return report


def main() -> None:
    """Run a demonstration of the cost driver analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_cost_driver_report()
        logger.info("%s", report)

    except Exception:
        logger.exception("Error in cost driver analysis")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
