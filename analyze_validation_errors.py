import re
from collections import Counter
import pandas as pd
from unimelb_phd_phase_1.formula_parser import parse_formula

def is_cross_sheet(formula_str):
    """Check if a formula string contains a sheet reference."""
    return '!' in formula_str

def get_pattern(formula_str):
    """Generate a generic pattern from a formula string."""
    # Handle absolute and relative cell references
    pattern = re.sub(r"\$?[A-Z]+\$?\d+", "CELL", formula_str)
    # Handle sheet references
    pattern = re.sub(r"'[^']+'!", "SHEET!", pattern)
    # Handle numbers
    pattern = re.sub(r"\d+\.\d+", "NUM", pattern)
    pattern = re.sub(r"\d+", "NUM", pattern)
    return pattern

def analyze_errors(validation_output_path):
    """
    Analyzes the validation output file to identify and count unsupported and discrepancy-causing formulas,
    separating them by whether they are same-sheet or cross-sheet.
    """
    unsupported_same_sheet = []
    unsupported_cross_sheet = []
    discrepancy_same_sheet = []
    discrepancy_cross_sheet = []

    with open(validation_output_path, 'r') as f:
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

    def print_top5(title, formulas):
        print(f"\n--- {title} ---")
        patterns = Counter(get_pattern(f) for f in formulas)
        if not patterns:
            print("None found.")
            return
        for pattern, count in patterns.most_common(5):
            print(f"{pattern}: {count}")

    print_top5("Top 5 Unsupported Same-Sheet Formula Patterns", unsupported_same_sheet)
    print_top5("Top 5 Unsupported Cross-Sheet Formula Patterns", unsupported_cross_sheet)
    print_top5("Top 5 Discrepancy-Causing Same-Sheet Formula Patterns", discrepancy_same_sheet)
    print_top5("Top 5 Discrepancy-Causing Cross-Sheet Formula Patterns", discrepancy_cross_sheet)


if __name__ == "__main__":
    analyze_errors("validation_output.txt")