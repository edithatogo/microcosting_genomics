#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Run deterministic sensitivity analysis for the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.dsa_analysis import DSAAnalyzer

logger = logging.getLogger(__name__)


def main() -> None:
    """Run DSA analysis."""
    sys.stdout.write("Running Deterministic Sensitivity Analysis (DSA)..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = DSAAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_dsa_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1] / "reports" / "dsa_analysis.md"
        )
        analyzer.generate_dsa_report(str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze dsa")
        sys.stdout.write(f"Error in DSA analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
