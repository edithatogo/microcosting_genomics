from collections import Counter

import pandas as pd

from genomics_microcosting.formula_parser import parse_formula


def normalize_formula(parsed_formula):
    """
    Normalizes a parsed formula to represent its structure,
    ignoring specific cell references.
    """
    if not parsed_formula:
        return "unknown"

    formula_type = parsed_formula.get("type")
    if formula_type == "literal":
        return "literal"
    elif formula_type == "reference":
        return f"reference({parsed_formula.get('sheet')})"
    elif formula_type in ["multiplication", "addition"]:
        operands = [normalize_formula(op) for op in parsed_formula.get("operands", [])]
        return f"{formula_type}({', '.join(operands)})"
    elif formula_type == "sum_range":
        return "sum_range"
    elif formula_type == "sum_cells":
        return f"sum_cells({len(parsed_formula.get('cells', []))})"
    elif formula_type == "if":
        condition = normalize_formula(parsed_formula.get("condition"))
        true_val = normalize_formula(parsed_formula.get("true_val"))
        false_val = normalize_formula(parsed_formula.get("false_val"))
        return f"if({condition}, {true_val}, {false_val})"
    elif formula_type == "iferror":
        value = normalize_formula(parsed_formula.get("value"))
        return f"iferror({value}, ...)"
    elif formula_type == "vlookup":
        return "vlookup"
    else:
        return "unknown"


def analyze_formula_patterns():
    """
    Analyzes the formula patterns in the 'Detailed Table' and
    prints a report of the most common patterns.
    """
    print("Loading formulas from 'data/prepared/detailed_table_formulas.parquet'...")
    try:
        formulas_df = pd.read_parquet("data/prepared/detailed_table_formulas.parquet")
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        return

    print("Analyzing formula patterns...")
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

    print("\n--- Formula Pattern Analysis Report ---")
    if not pattern_counts:
        print("No formula patterns found.")
        return

    total_formulas = sum(pattern_counts.values())
    print(
        f"Found {len(pattern_counts)} unique formula patterns out of {total_formulas} total formulas.\n"
    )

    # Sort by count descending
    sorted_patterns = pattern_counts.most_common()

    for i, (pattern, count) in enumerate(sorted_patterns):
        percentage = (count / total_formulas) * 100
        print(f"{i + 1}. Pattern: {pattern}")
        print(f"   Count: {count} ({percentage:.2f}%)")
        print("-" * 20)

    if unknown_formulas:
        print("\n--- Unknown Formula Report ---")
        print(f"Found {len(unknown_formulas)} unknown formulas. Here are the first 20:")
        for i, formula in enumerate(unknown_formulas[:20]):
            print(f"  {i + 1}. {formula}")
    else:
        print("\nNo unknown formulas found.")

    if multiplication_unknowns:
        print("\n--- Multiplication with Unknowns Report ---")
        print(
            f"Found {len(multiplication_unknowns)} multiplication formulas with unknown parts. Here are the first 20:"
        )
        for i, formula in enumerate(multiplication_unknowns[:20]):
            print(f"  {i + 1}. {formula}")
    else:
        print("\nNo multiplication formulas with unknown parts found.")


if __name__ == "__main__":
    analyze_formula_patterns()
