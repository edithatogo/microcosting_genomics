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
    
    # Handle string literals
    match = re.match(r'"([^"]*)"', formula)
    if match:
        return {"type": "string_literal", "value": match.group(1)}

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
            return {
                "type": "if",
                "condition": condition.strip(),
                "true_val": parse_formula(f"={value_if_true.strip()}"),
                "false_val": parse_formula(f"={value_if_false.strip()}")
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

    # Addition
    if '+' in formula:
        parts = formula.split('+')
        if len(parts) > 1:
            return {
                "type": "addition",
                "operands": [parse_formula(f"={p}") for p in parts]
            }

    # Division of cell / number / cell
    match = re.match(r"(\$?\w+\$?\d+)/(\d+)/(\$?\w+\$?\d+)", formula)
    if match:
        cell1, number, cell2 = match.groups()
        return {
            "type": "division_three_values",
            "cell1": cell1,
            "number": int(number),
            "cell2": cell2
        }

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

    # Simple cell reference with quoted sheet name
    match = re.match(r"'([^']*)'!(\$?\w+\$?\d+)", formula)
    if match:
        sheet, cell = match.groups()
        return {"type": "reference", "sheet": sheet, "cell": cell}

    # Simple cell reference with unquoted sheet name
    match = re.match(r"([\w\s\.-]+)!(\$?\w+\$?\d+)", formula)
    if match:
        sheet, cell = match.groups()
        return {"type": "reference", "sheet": sheet.strip(), "cell": cell}

    # Simple cell reference without sheet name
    match = re.match(r"^(\$?\w+\$?\d+)$", formula)
    if match:
        cell = match.group(1)
        return {"type": "reference", "sheet": None, "cell": cell}

    return {"type": "unknown", "formula": f"={formula}"}
