#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Run probabilistic sensitivity analysis for the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.psa_analysis import PSAAnalyzer

logger = logging.getLogger(__name__)


def main() -> None:
    """Run PSA analysis."""
    sys.stdout.write("Running Probabilistic Sensitivity Analysis (PSA)..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = PSAAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_psa_report(iterations=1000)
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1] / "reports" / "psa_analysis.md"
        )
        analyzer.generate_psa_report(iterations=1000, output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete analyze psa")
        sys.stdout.write(f"Error in PSA analysis: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
