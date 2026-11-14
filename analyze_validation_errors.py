# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Summarize cross-sheet references in validation errors."""

import re
import sys
from collections import Counter
from pathlib import Path


def is_cross_sheet(formula_str: str) -> bool:
    """Check if a formula string contains a sheet reference."""
    return "!" in formula_str


def get_pattern(formula_str: str) -> str:
    """Generate a generic pattern from a formula string."""
    # Handle absolute and relative cell references
    pattern = re.sub(r"\$?[A-Z]+\$?\d+", "CELL", formula_str)
    # Handle sheet references
    pattern = re.sub(r"'[^']+'!", "SHEET!", pattern)
    # Handle numbers
    pattern = re.sub(r"\d+\.\d+", "NUM", pattern)
    return re.sub(r"\d+", "NUM", pattern)


def analyze_errors(validation_output_path: str | Path) -> None:
    """Count unsupported and discrepant formulas by sheet-reference scope."""
    unsupported_same_sheet = []
    unsupported_cross_sheet = []
    discrepancy_same_sheet = []
    discrepancy_cross_sheet = []

    with Path(validation_output_path).open() as f:
        for line in f:
            match = re.search(r"'formula': \"=(.*?)\"", line)
            if not match:
                continue

            formula_str = match.group(1)

            if "'calculated_value': 'UNSUPPORTED[unknown]'" in line:
                if is_cross_sheet(formula_str):
                    unsupported_cross_sheet.append(formula_str)
                else:
                    unsupported_same_sheet.append(formula_str)
            elif "Discrepancies found:" not in line:
                if is_cross_sheet(formula_str):
                    discrepancy_cross_sheet.append(formula_str)
                else:
                    discrepancy_same_sheet.append(formula_str)

    def print_top5(title: str, formulas: list[str]) -> None:
        sys.stdout.writelines((f"\n--- {title} ---", "\n"))
        patterns = Counter(get_pattern(f) for f in formulas)
        if not patterns:
            sys.stdout.writelines(("None found.", "\n"))
            return
        for pattern, count in patterns.most_common(5):
            sys.stdout.writelines((f"{pattern}: {count}", "\n"))

    print_top5("Top 5 Unsupported Same-Sheet Formula Patterns", unsupported_same_sheet)
    print_top5(
        "Top 5 Unsupported Cross-Sheet Formula Patterns",
        unsupported_cross_sheet,
    )
    print_top5(
        "Top 5 Discrepancy-Causing Same-Sheet Formula Patterns",
        discrepancy_same_sheet,
    )
    print_top5(
        "Top 5 Discrepancy-Causing Cross-Sheet Formula Patterns",
        discrepancy_cross_sheet,
    )


if __name__ == "__main__":
    analyze_errors("validation_output.txt")
