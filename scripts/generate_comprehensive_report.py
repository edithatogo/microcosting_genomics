#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to generate a comprehensive report integrating all microcosting analyses."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.comprehensive_reporting import ComprehensiveReporter
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Generate comprehensive report."""
    sys.stdout.write("Generating comprehensive microcosting analysis report..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize reporter
        reporter = ComprehensiveReporter(data_manager)

        # Generate integrated report
        report = reporter.generate_integrated_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_dir = (
            Path(__file__).resolve().parents[1] / "reports" / "comprehensive_analysis"
        )
        reporter.generate_integrated_report(output_dir=str(output_dir))
        sys.stdout.write(f"Comprehensive report saved to {output_dir}" + "\n")

    except Exception as e:
        logger.exception("Could not complete generate comprehensive report")
        sys.stdout.write(f"Error in comprehensive reporting: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
