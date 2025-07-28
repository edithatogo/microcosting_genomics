import re

def parse_formula(formula):
    """Parse a subset of Excel formulas used in the project.

    The parser recognises numeric and string literals, references, and several
    common Excel functions. Numeric literals such as ``=3`` or ``=1.5`` are
    returned as ``{"type": "literal", "value": 3}`` so that arithmetic on
    constants behaves the same as on values extracted from cells.

    Multiplication patterns that involve two cells and a trailing numeric value
    (e.g. ``=A1*B1*3``) are matched **before** simpler multiplication cases. This
    ordering prevents a formula like ``A1*B1*3`` from being prematurely
    interpreted as ``A1*B1`` followed by an unknown ``*3`` segment.

    ``IF`` expressions recursively parse both ``value_if_true`` and
    ``value_if_false``. Literal branches therefore return the same structure as
    top‑level numeric literals, e.g. ``IF(A1>0,0,B1*C1)`` yields
    ``{"type": "literal", "value": 0}`` for the true branch and a nested
    multiplication structure for the false branch.
    """
    if not isinstance(formula, str) or not formula.startswith('='):
        if isinstance(formula, (int, float)):
            return {"type": "literal", "value": formula}
        return None

    formula = formula.lstrip('=+').strip()

    # Handle numeric literals (integers or floats)
    if re.fullmatch(r"-?\d+(?:\.\d+)?", formula):
        value = float(formula)
        if value.is_integer():
            value = int(value)
        return {"type": "literal", "value": value}
    
    # Handle string literals
    match = re.match(r'"([^"]*)"', formula)
    if match:
        return {"type": "string_literal", "value": match.group(1)}

    # IFERROR
    match = re.fullmatch(r"IFERROR\((.+),(.+)\)", formula)
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
    if formula.upper().startswith('IF('):
        # More robust parsing for IF statements
        content = formula[3:-1]
        paren_level = 0
        args = []
        current_arg = ""
        for char in content:
            if char == ',' and paren_level == 0:
                args.append(current_arg)
                current_arg = ""
            else:
                if char == '(':
                    paren_level += 1
                elif char == ')':
                    paren_level -= 1
                current_arg += char
        args.append(current_arg)

        if len(args) == 3:
            condition, value_if_true, value_if_false = args
            # Recursively parse both result branches so that literals are
            # returned in the same structure as top-level numeric literals.
            return {
                "type": "if",
                "condition": condition.strip(),
                "true_val": parse_formula(f"={value_if_true.strip()}"),
                "false_val": parse_formula(f"={value_if_false.strip()}")
            }

    # VLOOKUP
    match = re.fullmatch(r"VLOOKUP\((.+),(.+),(.+),(.+)\)", formula)
    if match:
        lookup_value, table_array, col_index_num, range_lookup = match.groups()
        return {
            "type": "vlookup",
            "lookup_value": lookup_value,
            "table_array": table_array,
            "col_index_num": col_index_num,
            "range_lookup": range_lookup
        }

    # PMT
    match = re.fullmatch(r"PMT\(([^,]+),([^,]+),([^,)]+)\)", formula)
    if match:
        rate, nper, pv = [s.strip() for s in match.groups()]
        return {
            "type": "pmt",
            "rate": rate,
            "nper": nper,
            "pv": pv,
        }

    # Multiplication of three values
    # NOTE: this check is intentionally placed before the simpler
    # ``cell*cell`` pattern below so that expressions like ``A1*B1*3`` are
    # parsed as a three-value multiplication rather than ``A1*B1`` with a
    # dangling ``*3``.
    match = re.fullmatch(r"(\w+\d+)\*(\w+\d+)\*(\d+)", formula)
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
    match = re.fullmatch(r"'([^']*)'!(\$?\w+\$?\d+)\*'([^']*)'!(\$?\w+\$?\d+)", formula)
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
    match = re.fullmatch(r"(\w+\d+)\*(\w+\d+)", formula)
    if match:
        cell1, cell2 = match.groups()
        return {
            "type": "multiplication",
            "operands": [
                {"sheet": None, "cell": cell1},
                {"sheet": None, "cell": cell2},
            ]
        }

    # Multiplication with a number and optional sheet name
    match = re.fullmatch(r"'([^']*)'!(\$?\w+\$?\d+)\*(\d+)", formula)
    if match:
        sheet, cell, number = match.groups()
        return {
            "type": "multiplication_by_number",
            "sheet": sheet,
            "cell": cell,
            "number": int(number)
        }

    match = re.fullmatch(r"([\w\s\.-]+)!(\$?\w+\$?\d+)\*(\d+)", formula)
    if match:
        sheet, cell, number = match.groups()
        return {
            "type": "multiplication_by_number",
            "sheet": sheet.strip(),
            "cell": cell,
            "number": int(number)
        }

    match = re.fullmatch(r"(\$?\w+\$?\d+)\*(\d+)", formula)
    if match:
        cell, number = match.groups()
        return {
            "type": "multiplication_by_number",
            "cell": cell,
            "number": int(number)
        }

    # Addition
    if '+' in formula:
        parts = formula.split('+')
        if len(parts) > 1:
            return {
                "type": "addition",
                "operands": [parse_formula(f"={p}") for p in parts]
            }

    # Division of cell / number / cell
    match = re.fullmatch(r"(\$?\w+\$?\d+)/(\d+)/(\$?\w+\$?\d+)", formula)
    if match:
        cell1, number, cell2 = match.groups()
        return {
            "type": "division_three_values",
            "cell1": cell1,
            "number": int(number),
            "cell2": cell2
        }

    # Simple SUM
    match = re.fullmatch(r"SUM\((.+)\)", formula)
    if match:
        # This is a simplified SUM parser, it will need to be improved
        # to handle multiple arguments
        args = match.group(1).split(',')
        if len(args) == 1 and ':' in args[0]:
            start_cell, end_cell = args[0].split(':')
            return {"type": "sum_range", "start_cell": start_cell, "end_cell": end_cell}
        else:
            return {"type": "sum_cells", "cells": args}

    # Simple cell reference with quoted sheet name
    match = re.fullmatch(r"'([^']*)'!(\$?\w+\$?\d+)", formula)
    if match:
        sheet, cell = match.groups()
        return {"type": "reference", "sheet": sheet, "cell": cell}

    # Simple cell reference with unquoted sheet name
    match = re.fullmatch(r"([\w\s\.-]+)!(\$?\w+\$?\d+)", formula)
    if match:
        sheet, cell = match.groups()
        return {"type": "reference", "sheet": sheet.strip(), "cell": cell}

    # Simple cell reference without sheet name
    match = re.fullmatch(r"(\$?\w+\$?\d+)", formula)
    if match:
        cell = match.group(1)
        return {"type": "reference", "sheet": None, "cell": cell}

    return {"type": "unknown", "formula": f"={formula}"}
