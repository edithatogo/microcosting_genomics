#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Value of Information (VOI) Analysis on the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.voi_analysis import VOIAnalyzer

logger = logging.getLogger(__name__)


def main() -> None:
    """Run VOI analysis."""
    sys.stdout.write("Running Value of Information (VOI) Analysis..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = VOIAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_voi_report(iterations=1000)
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1] / "reports" / "voi_analysis.md"
        )
        analyzer.generate_voi_report(iterations=1000, output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze voi")
        sys.stdout.write(f"Error in VOI analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
