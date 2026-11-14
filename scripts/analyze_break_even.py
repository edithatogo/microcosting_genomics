#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Break-even Analysis on the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.break_even_analysis import BreakEvenAnalyzer
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Run break-even analysis."""
    sys.stdout.write("Running Break-even Analysis..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = BreakEvenAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_break_even_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1] / "reports" / "break_even_analysis.md"
        )
        analyzer.generate_break_even_report(output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze break even")
        sys.stdout.write(f"Error in break-even analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
