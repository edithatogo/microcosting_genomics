#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to perform Monte Carlo Simulation Optimization."""

import logging
import sys
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.monte_carlo_optimizer import MonteCarloOptimizer

logger = logging.getLogger(__name__)


def main() -> None:
    """Run Monte Carlo optimization."""
    sys.stdout.write("Running Monte Carlo Simulation Optimization..." + "\n")

    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize optimizer
        optimizer = MonteCarloOptimizer(data_manager)

        # Generate report
        report = optimizer.generate_optimization_report()
        sys.stdout.write(str(report) + "\n")

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "monte_carlo_optimization.md"
        )
        optimizer.generate_optimization_report(output_file=str(output_file))
        sys.stdout.write(f"Report saved to {output_file}" + "\n")

    except Exception as e:
        logger.exception("Could not complete optimize monte carlo")
        sys.stdout.write(f"Error in Monte Carlo optimization: {e}" + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
