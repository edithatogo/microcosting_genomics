#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to create visualizations of cost data."""

import logging
import sys

from genomics_microcosting.visualization import create_summary_dashboard

logger = logging.getLogger(__name__)


def main() -> int:
    """Create visualizations."""
    sys.stdout.write("Creating cost visualization dashboard..." + "\n")

    try:
        # Create dashboard
        figures = create_summary_dashboard()
        sys.stdout.write(f"Created {len(figures)} visualizations" + "\n")
        sys.stdout.write("Dashboard creation complete!" + "\n")

    except Exception as e:
        logger.exception("Could not complete visualize costs")
        sys.stdout.write(f"Error creating visualizations: {e}" + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
