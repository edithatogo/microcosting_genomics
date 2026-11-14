# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Summarize workbook formulas by their parsed structure."""

import logging
import sys
from collections import Counter

import pandas as pd

from genomics_microcosting.formula_parser import parse_formula

logger = logging.getLogger(__name__)


def _describe_conditional(
    formula_type: object,
    parsed_formula: dict[str, object],
) -> str:
    if formula_type == "if":
        condition = normalize_formula(parsed_formula.get("condition"))
        true_val = normalize_formula(parsed_formula.get("true_val"))
        false_val = normalize_formula(parsed_formula.get("false_val"))
        return f"if({condition}, {true_val}, {false_val})"
    if formula_type == "iferror":
        value = normalize_formula(parsed_formula.get("value"))
        return f"iferror({value}, ...)"
    return "unknown"


def normalize_formula(parsed_formula: dict[str, object] | None) -> str:
    """Describe the formula structure without its individual cell references."""
    if not parsed_formula:
        return "unknown"

    formula_type = parsed_formula.get("type")
    if formula_type in ("literal", "sum_range", "vlookup"):
        return str(formula_type)
    if formula_type == "reference":
        return f"reference({parsed_formula.get('sheet')})"
    if formula_type in ["multiplication", "addition"]:
        operands = [normalize_formula(op) for op in parsed_formula.get("operands", [])]
        return f"{formula_type}({', '.join(operands)})"
    if formula_type == "sum_cells":
        return f"sum_cells({len(parsed_formula.get('cells', []))})"
    return _describe_conditional(formula_type, parsed_formula)


def analyze_formula_patterns() -> None:
    """Report the most common formula patterns in the detailed table."""
    sys.stdout.writelines(
        (
            "Loading formulas from 'data/prepared/detailed_table_formulas.parquet'...",
            "\n",
        ),
    )
    try:
        formulas_df = pd.read_parquet("data/prepared/detailed_table_formulas.parquet")
    except Exception as e:
        logger.exception("Could not complete analyze formula patterns")
        sys.stdout.writelines((f"Error loading parquet file: {e}", "\n"))
        return

    sys.stdout.writelines(("Analyzing formula patterns...", "\n"))
    pattern_counts = Counter()
    unknown_formulas = []
    multiplication_unknowns = []

    for col in formulas_df.columns:
        for formula in formulas_df[col]:
            if isinstance(formula, str) and formula.startswith("="):
                parsed = parse_formula(formula)
                normalized = normalize_formula(parsed)
                pattern_counts[normalized] += 1

                if normalized == "unknown":
                    unknown_formulas.append(formula)
                elif normalized.startswith("multiplication(unknown"):
                    multiplication_unknowns.append(formula)

    _report_patterns(pattern_counts, unknown_formulas, multiplication_unknowns)


def _report_patterns(
    pattern_counts: Counter[str],
    unknown_formulas: list[str],
    multiplication_unknowns: list[str],
) -> None:
    sys.stdout.writelines(("\n--- Formula Pattern Analysis Report ---", "\n"))
    if not pattern_counts:
        sys.stdout.writelines(("No formula patterns found.", "\n"))
        return

    total_formulas = sum(pattern_counts.values())
    sys.stdout.writelines(
        (
            (
                f"Found {len(pattern_counts)}"
                " unique formula patterns out of "
                f"{total_formulas}"
                " total formulas.\n"
            ),
            "\n",
        ),
    )

    # Sort by count descending
    sorted_patterns = pattern_counts.most_common()

    for i, (pattern, count) in enumerate(sorted_patterns):
        percentage = (count / total_formulas) * 100
        sys.stdout.writelines((f"{i + 1}. Pattern: {pattern}", "\n"))
        sys.stdout.writelines((f"   Count: {count} ({percentage:.2f}%)", "\n"))
        sys.stdout.writelines((str("-" * 20), "\n"))

    if unknown_formulas:
        sys.stdout.writelines(("\n--- Unknown Formula Report ---", "\n"))
        sys.stdout.writelines(
            (
                (
                    f"Found {len(unknown_formulas)}"
                    " unknown formulas. Here are the first 20:"
                ),
                "\n",
            ),
        )
        for i, formula in enumerate(unknown_formulas[:20]):
            sys.stdout.writelines((f"  {i + 1}. {formula}", "\n"))
    else:
        sys.stdout.writelines(("\nNo unknown formulas found.", "\n"))

    if multiplication_unknowns:
        sys.stdout.writelines(("\n--- Multiplication with Unknowns Report ---", "\n"))
        sys.stdout.writelines(
            (
                (
                    f"Found {len(multiplication_unknowns)}"
                    " multiplication formulas with unknown parts. Here are the "
                    "first 20:"
                ),
                "\n",
            ),
        )
        for i, formula in enumerate(multiplication_unknowns[:20]):
            sys.stdout.writelines((f"  {i + 1}. {formula}", "\n"))
    else:
        sys.stdout.writelines(
            ("\nNo multiplication formulas with unknown parts found.", "\n"),
        )


if __name__ == "__main__":
    analyze_formula_patterns()
