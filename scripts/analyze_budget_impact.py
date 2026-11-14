#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Budget Impact Analysis on the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.budget_impact_analysis import BudgetImpactAnalyzer
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Run budget impact analysis."""
    sys.stdout.write("Running Budget Impact Analysis..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = BudgetImpactAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_budget_impact_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "budget_impact_analysis.md"
        )
        analyzer.generate_budget_impact_report(output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze budget impact")
        sys.stdout.write(f"Error in budget impact analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
