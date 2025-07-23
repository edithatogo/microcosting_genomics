import re

def parse_formula(formula):
    """
    Parses a simple Excel formula.
    """
    if not isinstance(formula, str) or not formula.startswith('='):
        if isinstance(formula, (int, float)):
            return {"type": "literal", "value": formula}
        return None

    formula = formula.lstrip('=+').strip()

    # Handle numeric literals
    if formula.isnumeric():
        return {"type": "literal", "value": float(formula)}
    
    # IFERROR
    match = re.match(r"IFERROR\((.+),(.+)\)", formula)
    if match:
        value, value_if_error = match.groups()
        # This is a recursive call to handle nested formulas
        parsed_value = parse_formula(f"={value}")
        return {
            "type": "iferror",
            "value": parsed_value,
            "value_if_error": value_if_error
        }

    # IF
    match = re.match(r"IF\((.+),(.+),(.+)\)", formula)
    if match:
        condition, value_if_true, value_if_false = match.groups()
        return {
            "type": "if",
            "condition": condition,
            "value_if_true": parse_formula(f"={value_if_true}"),
            "value_if_false": parse_formula(f"={value_if_false}")
        }

    # VLOOKUP
    match = re.match(r"VLOOKUP\((.+),(.+),(.+),(.+)\)", formula)
    if match:
        lookup_value, table_array, col_index_num, range_lookup = match.groups()
        return {
            "type": "vlookup",
            "lookup_value": lookup_value,
            "table_array": table_array,
            "col_index_num": col_index_num,
            "range_lookup": range_lookup
        }

    # Multiplication of three values
    match = re.match(r"(\w+\d+)\*(\w+\d+)\*(\d+)", formula)
    if match:
        cell1, cell2, number = match.groups()
        return {
            "type": "multiplication_three_values",
            "operands": [
                {"sheet": None, "cell": cell1},
                {"sheet": None, "cell": cell2},
            ],
            "number": int(number)
        }

    # Simple multiplication with sheet names
    match = re.match(r"'([^']*)'!(\$?\w+\$?\d+)\*'([^']*)'!(\$?\w+\$?\d+)", formula)
    if match:
        sheet1, cell1, sheet2, cell2 = match.groups()
        return {
            "type": "multiplication",
            "operands": [
                {"sheet": sheet1, "cell": cell1},
                {"sheet": sheet2, "cell": cell2},
            ]
        }

    # Simple multiplication without sheet names
    match = re.match(r"(\w+\d+)\*(\w+\d+)", formula)
    if match:
        cell1, cell2 = match.groups()
        return {
            "type": "multiplication",
            "operands": [
                {"sheet": None, "cell": cell1},
                {"sheet": None, "cell": cell2},
            ]
        }

    # Multiplication with a number
    match = re.match(r"(\w+\d+)\*(\d+)", formula)
    if match:
        cell, number = match.groups()
        return {
            "type": "multiplication_by_number",
            "cell": cell,
            "number": int(number)
        }

    # Simple cell reference with sheet name
    match = re.match(r"'([^']*)'!(\$?\w+\$?\d+)", formula)
    if match:
        sheet, cell = match.groups()
        return {"type": "reference", "sheet": sheet, "cell": cell}

    # Simple cell reference without sheet name
    match = re.match(r"(\w+\d+)", formula)
    if match:
        cell = match.group(1)
        return {"type": "reference", "sheet": None, "cell": cell}

    # Simple SUM
    match = re.match(r"SUM\((.+)\)", formula)
    if match:
        # This is a simplified SUM parser, it will need to be improved
        # to handle multiple arguments
        args = match.group(1).split(',')
        if len(args) == 1 and ':' in args[0]:
            start_cell, end_cell = args[0].split(':')
            return {"type": "sum_range", "start_cell": start_cell, "end_cell": end_cell}
        else:
            return {"type": "sum_cells", "cells": args}


    return {"type": "unknown", "formula": f"={formula}"}