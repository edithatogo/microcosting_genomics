import re
from .logging_config import get_logger

logger = get_logger(__name__)

# Mapping for sheet name variations found in formulas vs actual sheet names
SHEET_NAME_MAPPING = {
    "BI - Comp Stor Costs - VCGS": "BI - Comp+Stor Costs - VCGS",
}


def _normalize_sheet_name(sheet_name):
    """Normalize sheet name using the mapping if available."""
    return SHEET_NAME_MAPPING.get(sheet_name, sheet_name)


def _parse_arithmetic_expression(expr):
    """Parse simple arithmetic expressions like '420+4600' or '30*52'."""
    try:
        # Handle addition
        if '+' in expr:
            parts = expr.split('+')
            result = 0
            for part in parts:
                part = part.strip()
                if part:
                    result += float(part)
            return result
        
        # Handle multiplication
        if '*' in expr:
            parts = expr.split('*')
            result = 1
            for part in parts:
                part = part.strip()
                if part:
                    result *= float(part)
            return result
        
        # Handle single number
        return float(expr.strip())
    except (ValueError, TypeError):
        logger.warning(f"Could not parse arithmetic expression: {expr}")
        return None


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

    Args:
        formula (str): The formula string to parse (should start with "=").

    Returns:
        dict: A dictionary representing the parsed formula with a "type" key
        and other keys depending on the formula type, or None if the formula
        cannot be parsed.
    """
    try:
        if not isinstance(formula, str) or not formula.startswith("="):
            if isinstance(formula, (int, float)):
                return {"type": "literal", "value": formula}
            return None

        original_formula = formula
        formula = formula.lstrip("=+").strip()
        logger.debug(f"Parsing formula: {original_formula}")

        # Handle numeric literals (integers, floats, and scientific notation)
        # This pattern matches integers, floats, and scientific notation like 1E20 or 1.5E-10
        if re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", formula):
            # Handle scientific notation
            if 'e' in formula.lower():
                try:
                    value = float(formula)
                    if value.is_integer():
                        value = int(value)
                    logger.debug(f"Parsed as literal (scientific notation): {value}")
                    return {"type": "literal", "value": value}
                except ValueError:
                    pass  # Fall through to handle as regular expression
            else:
                value = float(formula)
                if value.is_integer():
                    value = int(value)
                logger.debug(f"Parsed as literal: {value}")
                return {"type": "literal", "value": value}

        # Handle string literals
        match = re.match(r'"([^"]*)"', formula)
        if match:
            value = match.group(1)
            logger.debug(f"Parsed as string literal: {value}")
            return {"type": "string_literal", "value": value}

        # IFERROR
        match = re.fullmatch(r"IFERROR\((.+),(.+)\)", formula)
        if match:
            value, value_if_error = match.groups()
            # This is a recursive call to handle nested formulas
            parsed_value = parse_formula(f"={value}")
            logger.debug(
                f"Parsed as IFERROR: value={value}, value_if_error={value_if_error}"
            )
            return {
                "type": "iferror",
                "value": parsed_value,
                "value_if_error": value_if_error,
            }

        # IF
        if formula.upper().startswith("IF("):
            # More robust parsing for IF statements
            content = formula[3:-1]
            paren_level = 0
            args = []
            current_arg = ""
            for char in content:
                if char == "," and paren_level == 0:
                    args.append(current_arg)
                    current_arg = ""
                else:
                    if char == "(":
                        paren_level += 1
                    elif char == ")":
                        paren_level -= 1
                    current_arg += char
            args.append(current_arg)

            if len(args) == 3:
                condition, value_if_true, value_if_false = args
                # Recursively parse both result branches so that literals are
                # returned in the same structure as top-level numeric literals.
                parsed_true = parse_formula(f"={value_if_true.strip()}")
                parsed_false = parse_formula(f"={value_if_false.strip()}")
                logger.debug(
                    f"Parsed as IF: condition={condition}, true_val={parsed_true}, false_val={parsed_false}"
                )
                return {
                    "type": "if",
                    "condition": condition.strip(),
                    "true_val": parsed_true,
                    "false_val": parsed_false,
                }

        # VLOOKUP
        match = re.fullmatch(r"VLOOKUP\((.+),(.+),(.+),(.+)\)", formula)
        if match:
            lookup_value, table_array, col_index_num, range_lookup = match.groups()
            logger.debug(
                f"Parsed as VLOOKUP: lookup_value={lookup_value}, table_array={table_array}, col_index_num={col_index_num}, range_lookup={range_lookup}"
            )
            return {
                "type": "vlookup",
                "lookup_value": lookup_value,
                "table_array": table_array,
                "col_index_num": col_index_num,
                "range_lookup": range_lookup,
            }

        # PMT
        match = re.fullmatch(r"PMT\(([^,]+),([^,]+),([^,)]+)\)", formula)
        if match:
            rate, nper, pv = [s.strip() for s in match.groups()]
            logger.debug(f"Parsed as PMT: rate={rate}, nper={nper}, pv={pv}")
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
        match = re.fullmatch(r"([A-Za-z]+\d+)\*([A-Za-z]+\d+)\*(\d+)", formula)
        if match:
            cell1, cell2, number = match.groups()
            logger.debug(
                f"Parsed as multiplication_three_values: cell1={cell1}, cell2={cell2}, number={number}"
            )
            return {
                "type": "multiplication_three_values",
                "operands": [
                    {"sheet": None, "cell": cell1},
                    {"sheet": None, "cell": cell2},
                ],
                "number": int(number),
            }

        # Simple multiplication with sheet names
        match = re.fullmatch(
            r"'([^']*)'!(\$?[A-Za-z]+\$?\d+)\*'([^']*)'!(\$?[A-Za-z]+\$?\d+)", formula
        )
        if match:
            sheet1, cell1, sheet2, cell2 = match.groups()
            logger.debug(
                f"Parsed as multiplication with sheets: sheet1={sheet1}, cell1={cell1}, sheet2={sheet2}, cell2={cell2}"
            )
            return {
                "type": "multiplication",
                "operands": [
                    {"type": "reference", "sheet": sheet1, "cell": cell1},
                    {"type": "reference", "sheet": sheet2, "cell": cell2},
                ],
            }

        # Simple multiplication without sheet names
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell1, cell2 = match.groups()
            logger.debug(f"Parsed as multiplication: cell1={cell1}, cell2={cell2}")
            return {
                "type": "multiplication",
                "operands": [
                    {"type": "reference", "sheet": None, "cell": cell1},
                    {"type": "reference", "sheet": None, "cell": cell2},
                ],
            }

        # Multiplication with a number and optional sheet name
        match = re.fullmatch(
            r"(?:'([^']*)'!)?(\$?[A-Za-z]+\$?\d+)\*(\d+(?:\.\d+)?)", formula
        ) or re.fullmatch(r"(\d+(?:\.\d+)?)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                sheet, cell, number = groups
                logger.debug(
                    f"Parsed as multiplication_by_number: sheet={sheet}, cell={cell}, number={number}"
                )
                return {
                    "type": "multiplication_by_number",
                    "sheet": sheet,
                    "cell": cell,
                    "number": float(number),
                }
            else:
                number, cell = groups
                logger.debug(
                    f"Parsed as multiplication_by_number: number={number}, cell={cell}"
                )
                return {
                    "type": "multiplication_by_number",
                    "sheet": None,
                    "cell": cell,
                    "number": float(number),
                }

        # Cross-sheet reference with multiplication and number: 'Sheet'!cell1*'Sheet'!cell2*number
        match = re.fullmatch(
            r"'([^']*)'!(\$?[A-Za-z]+\$?\d+)\*'([^']*)'!(\$?[A-Za-z]+\$?\d+)\*(\d+)", formula
        )
        if match:
            sheet1, cell1, sheet2, cell2, number = match.groups()
            normalized_sheet1 = _normalize_sheet_name(sheet1)
            normalized_sheet2 = _normalize_sheet_name(sheet2)
            logger.debug(
                f"Parsed as cross_sheet_multiplication_three: sheet1={sheet1} -> {normalized_sheet1}, cell1={cell1}, sheet2={sheet2} -> {normalized_sheet2}, cell2={cell2}, number={number}"
            )
            return {
                "type": "cross_sheet_multiplication_three",
                "sheet1": normalized_sheet1,
                "cell1": cell1,
                "sheet2": normalized_sheet2,
                "cell2": cell2,
                "number": int(number),
            }

        # Cross-sheet reference patterns must come BEFORE simpler cell reference patterns
        # to prevent partial matching of cross-sheet references

        # Cross-sheet reference: 'Sheet'!cell
        match = re.fullmatch(r"'([^']*)'!(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            sheet, cell = match.groups()
            normalized_sheet = _normalize_sheet_name(sheet)
            logger.debug(f"Parsed as cross_sheet_reference: sheet={sheet} -> {normalized_sheet}, cell={cell}")
            return {
                "type": "reference",
                "sheet": normalized_sheet,
                "cell": cell,
            }

        # Simple cell reference with quoted sheet name (including external workbook references)
        match = re.fullmatch(r"'(?:\[\d+\])?([^']*)'!(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            sheet, cell = match.groups()
            normalized_sheet = _normalize_sheet_name(sheet)
            logger.debug(
                f"Parsed as reference with quoted sheet: sheet={sheet} -> {normalized_sheet}, cell={cell}"
            )
            return {"type": "reference", "sheet": normalized_sheet, "cell": cell}

        # Simple cell reference with unquoted sheet name (including external workbook references)
        match = re.fullmatch(r"(?:\[[^\]]+\])?([\w\s\.-]+)!(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            sheet, cell = match.groups()
            logger.debug(
                f"Parsed as reference with unquoted sheet: sheet={sheet}, cell={cell}"
            )
            return {"type": "reference", "sheet": sheet.strip(), "cell": cell}

        # Complex expression: (number*number)/(expression) like (30*52)/(420+4600)
        match = re.fullmatch(r"\((\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)\)/\(([^)]+)\)", formula)
        if match:
            num1, num2, divisor_expr = match.groups()
            logger.debug(
                f"Parsed as complex_multiplication_division: num1={num1}, num2={num2}, divisor_expr={divisor_expr}"
            )

            # Parse the divisor expression using the arithmetic expression parser
            divisor_value = _parse_arithmetic_expression(divisor_expr)
            if divisor_value is None:
                logger.warning(f"Could not parse divisor expression: {divisor_expr}")
                return None

            return {
                "type": "complex_multiplication_division",
                "num1": float(num1),
                "num2": float(num2),
                "divisor": divisor_value,
            }

        # Addition
        if "+" in formula:
            parts = formula.split("+")
            if len(parts) > 1:
                operands = [parse_formula(f"={p}") for p in parts]
                logger.debug(f"Parsed as addition: {len(operands)} operands")
                return {
                    "type": "addition",
                    "operands": operands,
                }

        # Division of cell / number / cell
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\d+)/(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell1, number, cell2 = match.groups()
            logger.debug(
                f"Parsed as division_three_values: cell1={cell1}, number={number}, cell2={cell2}"
            )
            return {
                "type": "division_three_values",
                "cell1": cell1,
                "number": int(number),
                "cell2": cell2,
            }

        # Division with parentheses and multiplication: (number/cell)*cell
        match = re.fullmatch(r"\((\d+)/(\$?[A-Za-z]+\$?\d+)\)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            number, cell1, cell2 = match.groups()
            logger.debug(
                f"Parsed as division_parentheses_multiplication: number={number}, cell1={cell1}, cell2={cell2}"
            )
            return {
                "type": "division_parentheses_multiplication",
                "number": int(number),
                "cell1": cell1,
                "cell2": cell2,
            }

        # Number divided by cell times cell: number/cell*cell
        match = re.fullmatch(r"(\d+)/(\$?[A-Za-z]+\$?\d+)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            number, cell1, cell2 = match.groups()
            logger.debug(
                f"Parsed as number_division_multiplication: number={number}, cell1={cell1}, cell2={cell2}"
            )
            return {
                "type": "number_division_multiplication",
                "number": int(number),
                "cell1": cell1,
                "cell2": cell2,
            }

        # AVERAGE function
        match = re.fullmatch(r"AVERAGE\((.+)\)", formula)
        if match:
            args = match.group(1)
            # Handle range notation like L44:N44
            if ":" in args:
                start_cell, end_cell = args.split(":")
                logger.debug(
                    f"Parsed as average_range: start_cell={start_cell}, end_cell={end_cell}"
                )
                return {
                    "type": "average_range",
                    "start_cell": start_cell.strip(),
                    "end_cell": end_cell.strip(),
                }
            else:
                # Handle comma-separated cells
                cells = [cell.strip() for cell in args.split(",")]
                logger.debug(f"Parsed as average_cells: cells={cells}")
                return {
                    "type": "average_cells",
                    "cells": cells,
                }

        # Simple cell reference (must come AFTER cross-sheet patterns)
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell = match.group(1)
            logger.debug(f"Parsed as reference: cell={cell}")
            return {
                "type": "reference",
                "sheet": None,
                "cell": cell,
            }

        # Multiplication with division: cell*(cell/cell)
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)\*\((\$?[A-Za-z]+\$?\d+)/(\$?[A-Za-z]+\$?\d+)\)", formula)
        if match:
            cell1, cell2, cell3 = match.groups()
            logger.debug(
                f"Parsed as multiplication_with_division: cell1={cell1}, cell2={cell2}, cell3={cell3}"
            )
            return {
                "type": "multiplication_with_division",
                "cell1": cell1,
                "cell2": cell2,
                "cell3": cell3,
            }

        # Simple number multiplication: number*number
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)", formula)
        if match:
            number1, number2 = match.groups()
            logger.debug(
                f"Parsed as number_multiplication: number1={number1}, number2={number2}"
            )
            return {
                "type": "number_multiplication",
                "number1": float(number1),
                "number2": float(number2),
            }

        # Simple division: cell/cell
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell1, cell2 = match.groups()
            logger.debug(
                f"Parsed as simple_division: cell1={cell1}, cell2={cell2}"
            )
            return {
                "type": "simple_division",
                "cell1": cell1,
                "cell2": cell2,
            }

        # Cell division by number: cell/number
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\d+(?:\.\d+)?)", formula)
        if match:
            cell, number = match.groups()
            logger.debug(
                f"Parsed as cell_division_by_number: cell={cell}, number={number}"
            )
            return {
                "type": "cell_division_by_number",
                "cell": cell,
                "number": float(number),
            }

        # Complex multiplication with division: cell*cell/number*cell
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)\*(\$?[A-Za-z]+\$?\d+)/(\d+(?:\.\d+)?)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell1, cell2, number, cell3 = match.groups()
            logger.debug(
                f"Parsed as complex_multiplication_division: cell1={cell1}, cell2={cell2}, number={number}, cell3={cell3}"
            )
            return {
                "type": "complex_multiplication_division",
                "cell1": cell1,
                "cell2": cell2,
                "number": float(number),
                "cell3": cell3,
            }



        # Cell division by number, multiplied by cell: cell/number*cell
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\d+(?:\.\d+)?)\*(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell1, number, cell2 = match.groups()
            logger.debug(
                f"Parsed as cell_division_by_number_multiplication: cell1={cell1}, number={number}, cell2={cell2}"
            )
            return {
                "type": "cell_division_by_number_multiplication",
                "cell1": cell1,
                "number": float(number),
                "cell2": cell2,
            }

        # Number divided by cell: number/cell
        match = re.fullmatch(r"(\d+(?:\.\d+)?)/(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            number, cell = match.groups()
            logger.debug(
                f"Parsed as number_division_by_cell: number={number}, cell={cell}"
            )
            return {
                "type": "number_division_by_cell",
                "number": float(number),
                "cell": cell,
            }

        # Cell division by number, multiplied by cell, multiplied by number: cell/number*cell*number
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\d+(?:\.\d+)?)\*(\$?[A-Za-z]+\$?\d+)\*(\d+(?:\.\d+)?)", formula)
        if match:
            cell1, number1, cell2, number2 = match.groups()
            logger.debug(
                f"Parsed as cell_division_by_number_multiplication_by_number: cell1={cell1}, number1={number1}, cell2={cell2}, number2={number2}"
            )
            return {
                "type": "cell_division_by_number_multiplication_by_number",
                "cell1": cell1,
                "number1": float(number1),
                "cell2": cell2,
                "number2": float(number2),
            }

        # Cell division by number, divided by number: cell/number/number
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)/(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", formula)
        if match:
            cell, number1, number2 = match.groups()
            logger.debug(
                f"Parsed as cell_division_by_number_division_by_number: cell={cell}, number1={number1}, number2={number2}"
            )
            return {
                "type": "cell_division_by_number_division_by_number",
                "cell": cell,
                "number1": float(number1),
                "number2": float(number2),
            }

        # Simple number division: number/number
        match = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", formula)
        if match:
            number1, number2 = match.groups()
            logger.debug(
                f"Parsed as number_division: number1={number1}, number2={number2}"
            )
            return {
                "type": "number_division",
                "number1": float(number1),
                "number2": float(number2),
            }

        # Simple cell reference (must come AFTER cross-sheet patterns)
        match = re.fullmatch(r"(\$?[A-Za-z]+\$?\d+)", formula)
        if match:
            cell = match.group(1)
            logger.debug(f"Parsed as simple cell reference: {cell}")
            return {"type": "reference", "cell": cell}

        # Complex expression: (cell*(cell/cell)) like (H58*(H57/H58))
        match = re.fullmatch(r"\(([A-Za-z]+\d+)\*\(([A-Za-z]+\d+)/([A-Za-z]+\d+)\)\)", formula)
        if match:
            cell1, cell2, cell3 = match.groups()
            logger.debug(
                f"Parsed as multiplication_with_nested_division: cell1={cell1}, cell2={cell2}, cell3={cell3}"
            )
            return {
                "type": "multiplication_with_nested_division",
                "cell1": cell1,
                "cell2": cell2,
                "cell3": cell3,
            }

        # Complex expression: (number*(number/cell)) like (2*(5/8*F4))
        match = re.fullmatch(r"\((\d+(?:\.\d+)?)\*\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\*([A-Za-z]+\d+)\)\)", formula)
        if match:
            num1, num2, num3, cell = match.groups()
            logger.debug(
                f"Parsed as complex_nested_expression: num1={num1}, num2={num2}, num3={num3}, cell={cell}"
            )
            return {
                "type": "complex_nested_expression",
                "num1": float(num1),
                "num2": float(num2),
                "num3": float(num3),
                "cell": cell,
            }

        # Number division followed by multiplication: number/number*cell like 365/3*D58
        match = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\*([A-Za-z]+\d+)", formula)
        if match:
            num1, num2, cell = match.groups()
            logger.debug(
                f"Parsed as division_multiplication_sequence: num1={num1}, num2={num2}, cell={cell}"
            )
            return {
                "type": "division_multiplication_sequence",
                "num1": float(num1),
                "num2": float(num2),
                "cell": cell,
            }

        # SUM function with range: SUM(A1:A10)
        match = re.fullmatch(r"SUM\((\$?[A-Za-z]+\$?\d+):(\$?[A-Za-z]+\$?\d+)\)", formula)
        if match:
            start_cell, end_cell = match.groups()
            logger.debug(
                f"Parsed as sum_range: start_cell={start_cell}, end_cell={end_cell}"
            )
            return {
                "type": "sum_range",
                "start_cell": start_cell,
                "end_cell": end_cell,
            }

        # SUM function with multiple cells: SUM(A1,B1,C1)
        match = re.fullmatch(r"SUM\(([^)]+)\)", formula)
        if match:
            args_str = match.group(1)
            # Split by comma and clean up whitespace
            cells = [cell.strip() for cell in args_str.split(',')]
            logger.debug(f"Parsed as sum_cells: cells={cells}")
            return {
                "type": "sum_cells",
                "cells": cells,
            }

        logger.warning(f"Unknown formula type: {original_formula}")
    except Exception as e:
        logger.error(f"Error parsing formula '{formula}': {e}")
        return {"type": "parse_error", "formula": formula, "error": str(e)}
