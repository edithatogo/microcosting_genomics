# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Example cost analysis plugin."""

from typing import Any

import polars as pl

from genomics_microcosting.plugin_system import AnalysisPlugin


class CostAnalysisPlugin(AnalysisPlugin):
    """Plugin for cost analysis functionality."""

    def __init__(self) -> None:
        """Register the example cost analysis plugin."""
        super().__init__(
            name="cost_analysis",
            version="1.0.0",
            description="Cost analysis plugin for microcosting data",
        )

    def analyze(self, data: object) -> dict[str, Any]:
        """Perform cost analysis on microcosting data.

        Args:
            data (pl.DataFrame): Microcosting data

        Returns:
            Dict[str, Any]: Analysis results

        Raises:
            ValueError: If data is not a Polars DataFrame.

        """
        if isinstance(data, pl.DataFrame):
            return self._analyze_frame(data)
        message = "Data must be a Polars DataFrame"
        raise ValueError(message)

    def _analyze_frame(self, data: pl.DataFrame) -> dict[str, Any]:
        results: dict[str, Any] = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "numeric_columns": len(data.select(pl.selectors.numeric()).columns),
            "memory_usage_mb": data.estimated_size() / 1024 / 1024,
        }

        # If there are numeric columns, calculate basic statistics
        numeric_data = data.select(pl.selectors.numeric()).with_columns(
            pl.selectors.float().fill_nan(None),
        )
        if numeric_data.width > 0 and numeric_data.height > 0:
            results["cost_statistics"] = {
                "mean_cost": numeric_data.mean().row(0, named=True),
                "median_cost": numeric_data.median().row(0, named=True),
                "std_cost": numeric_data.std().row(0, named=True),
            }

        return results
