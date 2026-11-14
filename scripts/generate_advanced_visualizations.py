#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to generate advanced visualizations with interactive features."""

import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.advanced_visualization import (
    create_comprehensive_visualization_report,
)
from genomics_microcosting.visualization import load_prepared_data

logger = logging.getLogger(__name__)


def main() -> int:
    """Generate advanced visualizations."""
    sys.stdout.write("Generating advanced visualizations..." + "\n")

    try:
        # Load data
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        output_dir = (
            Path(__file__).resolve().parents[1] / "reports" / "advanced_visualizations"
        )
        output_dir.mkdir(exist_ok=True, parents=True)

        sys.stdout.write(f"Loading data from {data_dir}" + "\n")
        data_dict = load_prepared_data(data_dir)
        sys.stdout.write(f"Loaded {len(data_dict)} data tables" + "\n")

        if not data_dict:
            sys.stdout.write(
                "Error: No data loaded. Cannot generate visualizations." + "\n",
            )
            return 1

        # Generate comprehensive visualization report
        sys.stdout.write(f"Creating advanced visualizations in {output_dir}" + "\n")
        figures = create_comprehensive_visualization_report(data_dict, output_dir)
        sys.stdout.write(f"Created {len(figures)} advanced visualizations" + "\n")

        # List generated files
        sys.stdout.write("\nGenerated files:" + "\n")
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                sys.stdout.write(f"  - {file_path.name}" + "\n")

        sys.stdout.write("\nAdvanced visualization generation complete!" + "\n")
        sys.stdout.write(f"Visualizations saved to {output_dir}" + "\n")

    except Exception as e:
        logger.exception("Could not complete generate advanced visualizations")
        sys.stdout.write(f"Error generating advanced visualizations: {e}" + "\n")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
