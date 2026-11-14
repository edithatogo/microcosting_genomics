# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Comprehensive reporting module for microcosting analysis.

This module integrates all analytical components to generate comprehensive reports
for the genomics microcosting model.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
lazy from collections.abc import Callable

from .break_even_analysis import BreakEvenAnalyzer
from .budget_impact_analysis import BudgetImpactAnalyzer
from .cost_driver_analysis import CostDriverAnalyzer
from .data_manager import DataManager
from .dsa_analysis import DSAAnalyzer
from .logging_config import get_logger
from .psa_analysis import PSAAnalyzer
from .voi_analysis import VOIAnalyzer

logger = get_logger(__name__)


class ComprehensiveReporter:
    """Comprehensive reporter that integrates all analytical components."""

    def __init__(self, data_manager: DataManager) -> None:
        """Initialize the ComprehensiveReporter.

        Args:
            data_manager: DataManager instance for accessing prepared data

        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize analyzers
        self.cost_driver_analyzer = CostDriverAnalyzer(data_manager)
        self.dsa_analyzer = DSAAnalyzer(data_manager)
        self.psa_analyzer = PSAAnalyzer(data_manager)
        self.voi_analyzer = VOIAnalyzer(data_manager)
        self.budget_impact_analyzer = BudgetImpactAnalyzer(data_manager)
        self.break_even_analyzer = BreakEvenAnalyzer(data_manager)

    def generate_executive_summary(self) -> str:
        """Generate an executive summary of all analyses.

        Returns:
            Executive summary as a string

        """
        summary: list[str] = []
        summary.append("# Comprehensive Microcosting Analysis Report")
        generated_at = datetime.now(UTC).astimezone()
        summary.append(f"Generated on: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        summary.append("## Executive Summary")
        summary.append(
            "This comprehensive report integrates cost driver analysis, "
            "deterministic sensitivity analysis (DSA), "
            "probabilistic sensitivity analysis (PSA), value of information "
            "(VOI) analysis, budget impact "
            "analysis, and break-even analysis to provide a complete picture "
            "of the genomics microcosting model.",
        )
        summary.append("")
        summary.append("## Analysis Components")
        summary.append(
            (
                "1. **Cost Driver Analysis**: Identifies key cost contributors by value"
                " and proportion"
            ),
        )
        summary.append(
            (
                "2. **Deterministic Sensitivity Analysis (DSA)**: Examines impact of "
                "parameter variation"
            ),
        )
        summary.append(
            (
                "3. **Probabilistic Sensitivity Analysis (PSA)**: Quantifies "
                "uncertainty using Monte Carlo simulation"
            ),
        )
        summary.append(
            (
                "4. **Value of Information (VOI) Analysis**: Assesses economic value of"
                " reducing uncertainty"
            ),
        )
        summary.append(
            (
                "5. **Budget Impact Analysis**: Evaluates cost implications of "
                "different testing volumes and scenarios"
            ),
        )
        summary.append(
            (
                "6. **Break-even Analysis**: Determines volume thresholds for cost "
                "recovery and minimum efficient scale"
            ),
        )
        summary.append("")

        return "\n".join(summary)

    def generate_integrated_report(self, output_dir: str | None = None) -> str:
        """Generate a comprehensive integrated report combining all analyses.

        Args:
            output_dir: Optional directory to save detailed reports

        Returns:
            Integrated report as a string

        """
        try:
            report: list[str] = []

            # Add executive summary
            report.append(self.generate_executive_summary())

            sections = (
                (
                    "Cost Driver Analysis",
                    "Absolute Cost Drivers",
                    "cost driver",
                    self.cost_driver_analyzer.generate_cost_driver_report,
                ),
                (
                    "Deterministic Sensitivity Analysis (DSA)",
                    "Sensitivity Analysis Results",
                    "DSA",
                    self.dsa_analyzer.generate_dsa_report,
                ),
                (
                    "Probabilistic Sensitivity Analysis (PSA)",
                    "Simulation Details",
                    "PSA",
                    self.psa_analyzer.generate_psa_report,
                ),
                (
                    "Value of Information (VOI) Analysis",
                    "Expected Value of Perfect Information",
                    "VOI",
                    self.voi_analyzer.generate_voi_report,
                ),
                (
                    "Budget Impact Analysis",
                    "Volume Sensitivity Analysis",
                    "Budget Impact",
                    self.budget_impact_analyzer.generate_budget_impact_report,
                ),
                (
                    "Break-even Analysis",
                    "Break-even Volume Calculation",
                    "Break-even",
                    self.break_even_analyzer.generate_break_even_report,
                ),
            )
            for heading, first_subheading, name, generate in sections:
                report.append(f"## {heading}")
                report.extend(self._analysis_section(first_subheading, name, generate))
                report.append("")

            # Add methodology section
            report.append("## Methodology")
            report.append(
                "All analyses were conducted using a systematic framework that:",
            )
            report.append(
                "- Processes all input data sheets consistently using the DataManager",
            )
            report.append("- Executes Excel formula translations programmatically")
            report.append("- Maintains data integrity through validation checks")
            report.append(
                "- Supports scenario modeling through advanced analytical modules",
            )
            report.append("")

            # Add conclusions section
            report.append("## Conclusions")
            report.append(
                "This integrated analysis provides comprehensive insights into:",
            )
            report.append(
                "- Key cost drivers by value and proportion across all models",
            )
            report.append(
                "- Model robustness through deterministic sensitivity analysis",
            )
            report.append(
                (
                    "- Uncertainty quantification through probabilistic sensitivity "
                    "analysis"
                ),
            )
            report.append(
                (
                    "- Economic value of reducing uncertainty through value of "
                    "information analysis"
                ),
            )
            report.append(
                "- Budget implications of different testing volumes and scenarios",
            )
            report.append(
                "- Volume thresholds for cost recovery and minimum efficient scale",
            )
            report.append(
                "- Informed decision-making for genomics testing implementation",
            )
            report.append("")

            report_str = "\n".join(report)

            if output_dir:
                self._save_reports(Path(output_dir), report_str)

        except Exception:
            self.logger.exception("Error generating integrated report")
            raise
        else:
            return report_str

    def _analysis_section(
        self,
        first_subheading: str,
        name: str,
        generate: Callable[[], str],
    ) -> list[str]:
        try:
            lines = generate().split("\n")
        except Exception as error:
            self.logger.debug("Error generating %s analysis", name, exc_info=True)
            return [f"Error generating {name} analysis: {error}"]
        prefix = f"## {first_subheading}"
        first = next((i for i, line in enumerate(lines) if line.startswith(prefix)), 0)
        return lines[first:]

    def _save_reports(self, output_path: Path, report: str) -> None:
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "comprehensive_analysis_report.md").write_text(report)

        try:
            self.cost_driver_analyzer.generate_cost_driver_report(
                str(output_path / "cost_driver_analysis.md"),
            )
            self.break_even_analyzer.generate_break_even_report(
                output_file=str(output_path / "break_even_analysis.md"),
            )
            self.dsa_analyzer.generate_dsa_report(
                str(output_path / "dsa_analysis.md"),
            )
            self.psa_analyzer.generate_psa_report(
                output_file=str(output_path / "psa_analysis.md"),
            )
            self.voi_analyzer.generate_voi_report(
                output_file=str(output_path / "voi_analysis.md"),
            )
            self.budget_impact_analyzer.generate_budget_impact_report(
                output_file=str(output_path / "budget_impact_analysis.md"),
            )
        except Exception:
            self.logger.exception("Error saving individual reports")


def main() -> None:
    """Run a demonstration of the comprehensive reporting."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize reporter
        reporter = ComprehensiveReporter(data_manager)

        # Generate report
        report = reporter.generate_integrated_report()
        logger.info("%s", report)

    except Exception:
        logger.exception("Error in comprehensive reporting")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
