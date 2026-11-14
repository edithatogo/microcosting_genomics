#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Cost-Effectiveness Analysis on the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.cost_effectiveness_analysis import CostEffectivenessAnalyzer
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Run cost-effectiveness analysis."""
    sys.stdout.write("Running Cost-Effectiveness Analysis..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = CostEffectivenessAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_cost_effectiveness_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "cost_effectiveness_analysis.md"
        )
        analyzer.generate_cost_effectiveness_report(output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze cost effectiveness")
        sys.stdout.write(f"Error in cost-effectiveness analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
