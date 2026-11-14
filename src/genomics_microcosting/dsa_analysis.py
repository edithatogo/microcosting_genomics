# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Deterministic Sensitivity Analysis (DSA) module for microcosting analysis.

This module provides functionality to perform deterministic sensitivity analysis
by systematically varying key parameters and observing the impact on cost outcomes.
"""

import logging
from pathlib import Path
from typing import Protocol, TypedDict, Unpack, cast
lazy from collections.abc import Iterable, Sequence

import polars as pl
lazy from matplotlib.figure import Figure
lazy from matplotlib.patches import Rectangle

from .data_manager import DataManager
from .logging_config import get_logger
from .sensitivity_evidence import markdown_table, scenario_costs

try:
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError, AttributeError:
    plt = None

HAS_MATPLOTLIB = plt is not None
logger = get_logger(__name__)


class _LabelStyle(TypedDict):
    ha: str
    va: str
    fontsize: int


class _TornadoAxes(Protocol):
    def barh(
        self,
        y: Sequence[int],
        width: Sequence[float],
        *,
        color: str,
    ) -> Iterable[Rectangle]: ...

    def set_yticks(self, ticks: Sequence[int], *, labels: Sequence[str]) -> object: ...
    def set_xlabel(self, label: str) -> object: ...
    def set_title(self, label: str) -> object: ...
    def grid(self, *, visible: bool, alpha: float) -> None: ...

    def text(
        self,
        x: float,
        y: float,
        s: str,
        **style: Unpack[_LabelStyle],
    ) -> object: ...


class TornadoPlotter(Protocol):
    """Describe the Matplotlib subplot interface used by tornado charts."""

    def subplots(
        self,
        *,
        figsize: tuple[float, float],
    ) -> tuple[Figure, _TornadoAxes]:
        """Create a figure and its axes."""
        ...


class SensitivityResult(TypedDict):
    """Observed low/base/high outcome and percentage changes for one parameter."""

    parameter: str
    baseline: float
    low_value: float
    high_value: float
    low_change_pct: float
    high_change_pct: float
    low_impact: float
    high_impact: float
    max_impact: float


class DSAAnalyzer:
    """Analyzer for performing Deterministic Sensitivity Analysis."""

    def __init__(self, data_manager: DataManager) -> None:
        """Initialize the DSAAnalyzer.

        Args:
            data_manager: DataManager instance for accessing prepared data

        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def load_dsa_parameters(self) -> dict[str, pl.DataFrame]:
        """Load DSA parameters from prepared sheets.

        Returns:
            Dictionary of DSA parameter sheets

        """
        workbook = self.data_manager.config.get("workbooks", {}).get("validation", {})
        configured_path = workbook.get("path")
        if configured_path is None:
            message = "Validation workbook path is missing from configuration"
            raise KeyError(message)
        path = self.data_manager.data_dir / Path(configured_path).name
        return {"workbook": scenario_costs(path)}

    def perform_one_way_sensitivity(
        self,
        baseline_value: float,
        low_value: float,
        high_value: float,
        parameter_name: str,
    ) -> SensitivityResult:
        """Perform one-way sensitivity analysis for a single parameter.

        Args:
            baseline_value: Baseline value for the parameter
            low_value: Low value for sensitivity analysis
            high_value: High value for sensitivity analysis
            parameter_name: Name of the parameter being analyzed

        Returns:
            Dictionary with sensitivity results

        """
        # Calculate percentage changes
        low_change = ((low_value - baseline_value) / baseline_value) * 100
        high_change = ((high_value - baseline_value) / baseline_value) * 100

        # Calculate impact on outcomes (simplified)
        # In a real implementation, this would run the full model with modified
        # parameters
        low_impact = abs(low_change)  # Simplified impact measure
        high_impact = abs(high_change)  # Simplified impact measure
        max_impact = max(low_impact, high_impact)

        return {
            "parameter": parameter_name,
            "baseline": baseline_value,
            "low_value": low_value,
            "high_value": high_value,
            "low_change_pct": low_change,
            "high_change_pct": high_change,
            "low_impact": low_impact,
            "high_impact": high_impact,
            "max_impact": max_impact,
        }

    def generate_tornado_chart(
        self,
        sensitivity_results: list[SensitivityResult],
        title: str = "DSA Tornado Chart",
    ) -> Figure | None:
        """Generate a tornado chart for sensitivity analysis results.

        Args:
            sensitivity_results: List of sensitivity analysis results
            title: Title for the chart

        Returns:
            Matplotlib figure with tornado chart or None if matplotlib unavailable

        """
        if plt is None:
            logger.warning("Matplotlib not available, skipping chart generation")
            return None

        # Sort by impact
        sorted_results = sorted(sensitivity_results, key=lambda x: x["max_impact"])

        parameters = [result["parameter"] for result in sorted_results]
        impacts = [result["max_impact"] for result in sorted_results]

        fig, ax = cast("TornadoPlotter", plt).subplots(
            figsize=(10, max(6, len(parameters) * 0.5)),
        )
        y_pos = range(len(parameters))
        bars = ax.barh(y_pos, impacts, color="skyblue")
        ax.set_yticks(y_pos, labels=parameters)
        ax.set_xlabel("Impact on Cost Outcomes (%)")
        ax.set_title(title)
        ax.grid(visible=True, alpha=0.3)

        # Add value labels
        for bar, impact in zip(bars, impacts, strict=True):
            ax.text(
                bar.get_width() + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{impact:.1f}%",
                ha="left",
                va="center",
                fontsize=8,
            )

        fig.tight_layout()
        return fig

    def analyze_dsa_parameters(
        self,
        dsa_parameters: dict[str, pl.DataFrame],
    ) -> list[SensitivityResult]:
        """Analyze DSA parameters and calculate sensitivity.

        Args:
            dsa_parameters: Dictionary of DSA parameter sheets

        Returns:
            List of sensitivity analysis results

        """
        results: list[SensitivityResult] = []
        for sheet_name, source in dsa_parameters.items():
            table = source
            if {"Parameter", "Baseline", "Low", "High"}.issubset(table.columns):
                table = (
                    table.unpivot(
                        on=["Low", "Baseline", "High"],
                        index=["Parameter"],
                        variable_name="scenario",
                        value_name="cost",
                    )
                    .join(
                        table.select("Parameter", "Baseline"),
                        on="Parameter",
                        validate="m:1",
                    )
                    .rename(
                        {"Parameter": "parameter", "Baseline": "baseline"},
                    )
                    .with_columns(pl.lit(sheet_name).alias("assay"))
                )
            for key, group in table.group_by(
                ["parameter", "assay"],
                maintain_order=True,
            ):
                baseline = group["baseline"][0]
                low = group["cost"].min()
                high = group["cost"].max()
                if (
                    not isinstance(baseline, (float, int))
                    or not isinstance(low, (float, int))
                    or not isinstance(high, (float, int))
                ):
                    message = "Sensitivity bounds and baseline must be numeric"
                    raise TypeError(message)
                results.append(
                    self.perform_one_way_sensitivity(
                        baseline,
                        low,
                        high,
                        " / ".join(map(str, key)),
                    ),
                )
        return results

    def generate_dsa_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive DSA analysis report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        try:
            # Load DSA parameters
            dsa_parameters = self.load_dsa_parameters()

            # Analyze parameters
            sensitivity_results = self.analyze_dsa_parameters(dsa_parameters)

            # Generate report
            report: list[str] = []
            report.append("# Deterministic Sensitivity Analysis (DSA) Report\n")
            report.append("## Executive Summary\n")
            report.append(
                "This report presents the results of deterministic "
                "sensitivity analysis, "
                "which examines the impact of varying key parameters "
                "on cost outcomes.\n",
            )

            report.append("## Sensitivity Analysis Results\n")
            report.append("One-way sensitivity analysis results:\n")

            # Create results table
            results_df = pl.DataFrame(sensitivity_results)
            if results_df.height:
                report.append(
                    markdown_table(results_df.sort("max_impact", descending=True)),
                )
            else:
                report.append("No sensitivity analysis results available.")

            report.append("\n## Key Findings\n")
            report.append(
                "- Parameters are ranked by their maximum impact on cost outcomes\n",
            )
            report.append(
                (
                    "- Higher impact parameters should be "
                    "prioritized for data quality improvements\n"
                ),
            )
            report.append(
                (
                    "- Tornado chart visualization highlights "
                    "the most influential parameters\n"
                ),
            )

            report_str = "\n".join(report)

            if output_file:
                with Path(output_file).open("w") as f:
                    f.write(report_str)

        except Exception:
            self.logger.exception("Error generating DSA report")
            raise
        else:
            return report_str


def main() -> None:
    """Run a demonstration of the DSA analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = DSAAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_dsa_report()
        logger.info("%s", report)

    except Exception:
        logger.exception("Error in DSA analysis")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
