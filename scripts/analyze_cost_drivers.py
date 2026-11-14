#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to analyze cost drivers in the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Run cost driver analysis."""
    sys.stdout.write("Running cost driver analysis..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_cost_driver_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1] / "reports" / "cost_driver_analysis.md"
        )
        analyzer.generate_cost_driver_report(str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze cost drivers")
        sys.stdout.write(f"Error in cost driver analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
