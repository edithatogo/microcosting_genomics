#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to generate automated reports with visualizations and summary statistics."""

import logging
import sys
import traceback
from pathlib import Path

lazy import pandas as pd

from genomics_microcosting.visualization import (
    create_summary_dashboard,
    load_prepared_data,
)

logger = logging.getLogger(__name__)

CATEGORY_PREVIEW_LIMIT = 5


def generate_summary_statistics(
    data_dict: dict[str, pd.DataFrame],
    output_file: str | Path,
) -> None:
    """Generate summary statistics for all data tables.

    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_file (str or Path): Path to output file

    """
    with Path(output_file).open("w") as f:
        f.write("# Microcosting Analysis Report\n\n")
        f.write("## Summary Statistics\n\n")

        for table_name, df in data_dict.items():
            f.write(f"### {table_name}\n\n")
            f.write(f"- Number of rows: {len(df)}\n")
            f.write(f"- Number of columns: {len(df.columns)}\n\n")

            # Numeric column statistics
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                f.write("#### Numeric Columns Summary\n\n")
                f.write(df[numeric_cols].describe().to_markdown() + "\n\n")

            # Categorical column information
            categorical_cols = df.select_dtypes(include=["object"]).columns
            if len(categorical_cols) > 0:
                f.write("#### Categorical Columns\n\n")
                for col in categorical_cols[:5]:  # Limit to first 5
                    unique_count = df[col].nunique()
                    f.write(f"- **{col}**: {unique_count} unique values\n")
                if len(categorical_cols) > CATEGORY_PREVIEW_LIMIT:
                    f.write(
                        "- *... and "
                        f"{len(categorical_cols) - 5} more categorical columns*\n",
                    )
                f.write("\n")

            f.write("---\n\n")


def main() -> int:
    """Generate automated report."""
    sys.stdout.write("Generating automated report..." + "\n")

    try:
        # Load data
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        output_dir = Path(__file__).resolve().parents[1] / "reports"
        output_dir.mkdir(exist_ok=True)

        sys.stdout.write(f"Loading data from {data_dir}" + "\n")
        data_dict = load_prepared_data(data_dir)
        sys.stdout.write(f"Loaded {len(data_dict)} data tables" + "\n")

        # Generate summary statistics
        stats_file = output_dir / "summary_statistics.md"
        sys.stdout.write(f"Generating summary statistics in {stats_file}" + "\n")
        generate_summary_statistics(data_dict, stats_file)

        # Generate visualizations
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        sys.stdout.write(f"Generating visualizations in {viz_dir}" + "\n")
        figures = create_summary_dashboard(data_dir, viz_dir)
        sys.stdout.write(f"Created {len(figures)} visualizations" + "\n")

        # Generate combined report
        report_file = output_dir / "microcosting_report.md"
        sys.stdout.write(f"Generating combined report in {report_file}" + "\n")

        with Path(report_file).open("w") as f:
            f.write("# Microcosting Analysis Report\n\n")
            f.write("## Executive Summary\n\n")
            f.write(
                "This report provides an automated analysis of the "
                "microcosting data for rare disease genomics.\n\n",
            )

            f.write("## Data Overview\n\n")
            f.writelines(
                f"- **{table_name}**: {len(df)} rows, {len(df.columns)} columns\n"
                for table_name, df in data_dict.items()
            )
            f.write("\n")

            f.write("## Generated Visualizations\n\n")
            f.writelines(
                f"![{fig_file.stem}]({fig_file.name})\n\n"
                for fig_file in viz_dir.glob("*.png")
            )

            f.write("## Detailed Statistics\n\n")
            f.write(
                "See [summary_statistics.md](summary_statistics.md) for "
                "detailed statistics.\n\n",
            )

        sys.stdout.write("Report generation complete!" + "\n")
        sys.stdout.write(f"Reports saved to {output_dir}" + "\n")

    except Exception as e:
        logger.exception("Could not complete generate report")
        sys.stdout.write(f"Error generating report: {e}" + "\n")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
