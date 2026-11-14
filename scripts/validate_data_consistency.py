#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Data Consistency Validation on the microcosting model."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.data_consistency_validator import DataConsistencyValidator
from genomics_microcosting.data_manager import DataManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Run data consistency validation."""
    sys.stdout.write("Running Data Consistency Validation..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize validator
        validator = DataConsistencyValidator(data_manager)

        # Generate report
        report = validator.generate_validation_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "data_consistency_validation.md"
        )
        validator.generate_validation_report(output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete validate data consistency")
        sys.stdout.write(f"Error in data consistency validation: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
