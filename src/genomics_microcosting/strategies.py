import math
import re
from numbers import Number
from typing import Any, Dict, Optional, Union

from .utils import cell_to_coords, coords_to_cell
from .logging_config import get_logger
from .cost_components import (
    ArithmeticCostComponent,
    ReferenceCostComponent,
    AggregateCostComponent,
    FinancialCostComponent,
    ConditionalCostComponent,
    ComplexCostComponent,
)

logger = get_logger(__name__)


class CalculationStrategy:
    """Base class for a formula calculation strategy.

    This abstract base class defines the interface for all formula calculation strategies.
    Each strategy handles a specific type of Excel formula or operation.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        raise NotImplementedError


class LiteralStrategy(CalculationStrategy):
    """Strategy for handling numeric literals.

    This strategy handles simple numeric values in formulas, such as =3 or =1.5.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return parsed_formula["value"]


class StringLiteralStrategy(CalculationStrategy):
    """Strategy for handling string literals.

    This strategy handles string values in formulas, such as ="text".
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return parsed_formula["value"]


class ReferenceStrategy(CalculationStrategy, ReferenceCostComponent):
    """Strategy for handling cell references.

    This strategy handles references to other cells, such as =A1 or =Sheet1!A1.
    It can handle both direct value references and formula references.
    """

    # Mapping for sheet name variations found in formulas vs actual sheet names
    SHEET_NAME_MAPPING = {
        "BI - Comp Stor Costs - VCGS": "BI - Comp+Stor Costs - VCGS",
    }

    def __init__(self):
        ReferenceCostComponent.__init__(self, "Reference Strategy")

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(self, engine, parsed_formula, sheet_name, cell_ref):
        referenced_sheet = parsed_formula["sheet"]
        referenced_cell = parsed_formula["cell"]

        if referenced_sheet is None:
            referenced_sheet = sheet_name
        else:
            # Apply sheet name mapping for known variations
            referenced_sheet = self.SHEET_NAME_MAPPING.get(referenced_sheet, referenced_sheet)

        formula = engine.get_cell_formula(referenced_sheet, referenced_cell)

        if formula and isinstance(formula, str) and formula.startswith("="):
            return engine.execute_formula(formula, referenced_sheet, referenced_cell)

        return engine.get_cell_value(referenced_sheet, referenced_cell)

    def get_component_type(self):
        return "reference"

    def validate_inputs(self, parsed_formula):
        return "cell" in parsed_formula

    def get_reference_type(self):
        return "cell"

    def resolve_reference(self, engine, reference, sheet_name):
        referenced_sheet = reference.get("sheet", sheet_name)
        referenced_cell = reference["cell"]

        # Apply sheet name mapping
        referenced_sheet = self.SHEET_NAME_MAPPING.get(referenced_sheet, referenced_sheet)

        formula = engine.get_cell_formula(referenced_sheet, referenced_cell)
        if formula and isinstance(formula, str) and formula.startswith("="):
            return engine.execute_formula(formula, referenced_sheet, referenced_cell)
        return engine.get_cell_value(referenced_sheet, referenced_cell)


def _evaluate_operand(engine, operand, sheet_name, cell_ref):
    """Helper function to evaluate an operand.

    This function evaluates a single operand in a formula, which can be either
    a literal value or a cell reference.

    Args:
        engine (CalculationEngine): The calculation engine instance.
        operand (dict or str): The operand to evaluate.
        sheet_name (str): The name of the current sheet.
        cell_ref (str): The current cell reference.

    Returns:
        The evaluated value of the operand.
    """
    if isinstance(operand, dict):
        if operand.get("type") == "literal":
            return operand["value"]
        elif operand.get("type") == "reference":
            op_sheet = operand["sheet"] if operand["sheet"] else sheet_name
            op_cell = operand["cell"]
            formula = engine.get_cell_formula(op_sheet, op_cell)
            if formula and isinstance(formula, str) and formula.startswith("="):
                return engine.execute_formula(formula, op_sheet, op_cell)
            else:
                return engine.get_cell_value(op_sheet, op_cell)
    return engine.execute_formula(operand, sheet_name, cell_ref)


class AdditionStrategy(CalculationStrategy, ArithmeticCostComponent):
    """Strategy for handling addition formulas.

    This strategy handles addition operations, such as =A1+B1 or =1+2+3.
    It can handle multiple operands and will return None if any operand cannot be evaluated.
    """

    def __init__(self):
        ArithmeticCostComponent.__init__(self, "Addition Strategy")

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for idx, operand in enumerate(parsed_formula["operands"]):
            value = _evaluate_operand(engine, operand, sheet_name, f"{cell_ref}_{idx}")
            if isinstance(value, Number) and not (
                isinstance(value, float) and math.isnan(value)
            ):
                total += value
            else:
                return None
        return total

    def get_component_type(self):
        return "arithmetic"

    def validate_inputs(self, parsed_formula):
        return "operands" in parsed_formula and isinstance(parsed_formula["operands"], list)

    def get_operation_type(self):
        return "addition"

    def get_operand_count(self):
        return 0  # Variable number of operands


class MultiplicationStrategy(CalculationStrategy):
    """Strategy for handling multiplication formulas.

    This strategy handles multiplication operations, such as =A1*B1.
    It can handle multiple operands and will return None if any operand cannot be evaluated.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = 1
        for idx, operand in enumerate(parsed_formula["operands"]):
            value = _evaluate_operand(engine, operand, sheet_name, f"{cell_ref}_{idx}")
            if isinstance(value, Number):
                result *= value
            else:
                return None
        return result


class MultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for handling multiplication by a number.

    This strategy handles multiplication of a cell reference by a number,
    such as =A1*3 or =2*B1.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell_value = _evaluate_operand(
            engine,
            {
                "type": "reference",
                "sheet": parsed_formula["sheet"],
                "cell": parsed_formula["cell"],
            },
            sheet_name,
            f"{cell_ref}_0",
        )
        if isinstance(cell_value, Number):
            return cell_value * parsed_formula["number"]
        return None


class SumRangeStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with a range.

    This strategy handles SUM operations over a range of cells, such as =SUM(A1:A10).
    It will sum all numeric values in the range and ignore non-numeric values.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        start_cell = parsed_formula["start_cell"]
        end_cell = parsed_formula["end_cell"]

        start_row, start_col = cell_to_coords(start_cell)
        end_row, end_col = cell_to_coords(end_cell)

        total = 0
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = coords_to_cell(row, col)
                if cell == cell_ref:
                    continue

                formula = engine.get_cell_formula(sheet_name, cell)
                if formula:
                    value = engine.execute_formula(formula, sheet_name, cell)
                else:
                    value = engine.get_cell_value(sheet_name, cell)

                if isinstance(value, Number) and not (
                    isinstance(value, float) and math.isnan(value)
                ):
                    total += value
        return total


class SumCellsStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with individual cells.

    This strategy handles SUM operations with individual cell references,
    such as =SUM(A1,B1,C1).
    It will sum all numeric values and ignore non-numeric values.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for cell_info in parsed_formula["cells"]:
            if isinstance(cell_info, str):
                try:
                    value = float(cell_info)
                    total += value
                    continue
                except ValueError:
                    cell = cell_info
                    sheet = sheet_name
            else:
                cell = cell_info["cell"]
                sheet = cell_info.get("sheet", sheet_name)

            formula = engine.get_cell_formula(sheet, cell)
            if formula and isinstance(formula, str) and formula.startswith("="):
                value = engine.execute_formula(formula, sheet, cell)
            else:
                value = engine.get_cell_value(sheet, cell)

            if isinstance(value, Number) and not (
                isinstance(value, float) and math.isnan(value)
            ):
                total += value
        return total


class DivisionStrategy(CalculationStrategy):
    """Strategy for handling division formulas.

    This strategy handles division operations, such as =A1/B1.
    It will return None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = _evaluate_operand(
            engine, parsed_formula["operands"][0], sheet_name, f"{cell_ref}_0"
        )
        for idx, operand in enumerate(parsed_formula["operands"][1:]):
            value = _evaluate_operand(
                engine, operand, sheet_name, f"{cell_ref}_{idx + 1}"
            )
            if isinstance(value, Number) and value != 0:
                result /= value
            else:
                return None
        return result


class SimpleDivisionStrategy(CalculationStrategy):
    """Strategy for handling simple division formulas.

    This strategy handles simple division operations, such as =D27/E27.
    It performs cell1 / cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1_value = engine.get_cell_value(sheet_name, parsed_formula["cell1"])
        cell2_value = engine.get_cell_value(sheet_name, parsed_formula["cell2"])

        if isinstance(cell1_value, Number) and isinstance(cell2_value, Number) and cell2_value != 0:
            return cell1_value / cell2_value
        else:
            return None


class NumberDivisionStrategy(CalculationStrategy):
    """Strategy for handling simple number division formulas.

    This strategy handles simple number division operations, such as =1/150.
    It performs number1 / number2 operation.
    Returns None if division by zero occurs.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]

        if number2 != 0:
            return number1 / number2
        else:
            return None


class DivisionParenthesesMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling division with parentheses and multiplication formulas.

    This strategy handles formulas like =(1/E44)*Q44.
    It performs (number/cell1) * cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        number = parsed_formula["number"]
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]

        # Get value from cell1
        cell1_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": None, "cell": cell1}, 
            sheet_name, f"{cell_ref}_cell1"
        )

        # Get value from cell2
        cell2_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": None, "cell": cell2}, 
            sheet_name, f"{cell_ref}_cell2"
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, Number) or not isinstance(cell2_value, Number):
            return None

        # Check for division by zero
        if cell1_value == 0:
            return None

        # Perform (number/cell1) * cell2
        result = (number / cell1_value) * cell2_value
        return result


class NumberDivisionMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling number division and multiplication formulas.

    This strategy handles formulas like =1/F44*P44.
    It performs (number/cell1) * cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        number = parsed_formula["number"]
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]

        # Get value from cell1
        cell1_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": None, "cell": cell1}, 
            sheet_name, f"{cell_ref}_cell1"
        )

        # Get value from cell2
        cell2_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": None, "cell": cell2}, 
            sheet_name, f"{cell_ref}_cell2"
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, Number) or not isinstance(cell2_value, Number):
            return None

        # Check for division by zero
        if cell1_value == 0:
            return None

        # Perform (number/cell1) * cell2
        result = (number / cell1_value) * cell2_value
        return result


class AverageRangeStrategy(CalculationStrategy):
    """Strategy for handling AVERAGE function with range notation.

    This strategy handles formulas like =AVERAGE(L44:N44).
    It calculates the average of all cells in the specified range.
    Returns None if any cell cannot be evaluated.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        start_cell = parsed_formula["start_cell"]
        end_cell = parsed_formula["end_cell"]

        # Parse cell references to get coordinates
        start_coords = cell_to_coords(start_cell)
        end_coords = cell_to_coords(end_cell)

        if start_coords is None or end_coords is None:
            return None

        start_row, start_col = start_coords
        end_row, end_col = end_coords

        # Ensure we have valid integers
        if start_row is None or start_col is None or end_row is None or end_col is None:
            return None

        # Collect all values in the range
        values = []
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
                cell_ref_name = coords_to_cell(row, col)
                value = _evaluate_operand(
                    engine, {"type": "reference", "sheet": None, "cell": cell_ref_name},
                    sheet_name, f"{cell_ref}_{cell_ref_name}"
                )
                if isinstance(value, Number):
                    values.append(value)
                else:
                    return None  # Invalid value in range

        if not values:
            return None

        # Calculate average
        return sum(values) / len(values)


class AverageCellsStrategy(CalculationStrategy):
    """Strategy for handling AVERAGE function with individual cells.

    This strategy handles formulas like =AVERAGE(L44,N44).
    It calculates the average of the specified cells.
    Returns None if any cell cannot be evaluated.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cells = parsed_formula["cells"]
        values = []

        for i, cell in enumerate(cells):
            value = _evaluate_operand(
                engine, {"type": "reference", "sheet": None, "cell": cell},
                sheet_name, f"{cell_ref}_cell{i}"
            )
            if isinstance(value, Number):
                values.append(value)
            else:
                return None  # Invalid value

        if not values:
            return None

        # Calculate average
        return sum(values) / len(values)


class CrossSheetMultiplicationThreeStrategy(CalculationStrategy):
    """Strategy for handling cross-sheet multiplication with three operands.

    This strategy handles formulas like ='Sheet1'!F102*'Sheet1'!I102*3.
    It performs (sheet1!cell1 * sheet2!cell2) * number.
    Returns None if any operand cannot be evaluated.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        sheet1 = parsed_formula["sheet1"]
        cell1 = parsed_formula["cell1"]
        sheet2 = parsed_formula["sheet2"]
        cell2 = parsed_formula["cell2"]
        number = parsed_formula["number"]

        # Get value from sheet1!cell1
        cell1_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": sheet1, "cell": cell1},
            sheet_name, f"{cell_ref}_cell1"
        )

        # Get value from sheet2!cell2
        cell2_value = _evaluate_operand(
            engine, {"type": "reference", "sheet": sheet2, "cell": cell2},
            sheet_name, f"{cell_ref}_cell2"
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, Number) or not isinstance(cell2_value, Number):
            return None

        # Perform (cell1_value * cell2_value) * number
        result = (cell1_value * cell2_value) * number
        return result


class IfStrategy(CalculationStrategy):
    """Strategy for handling IF formulas.

    This strategy handles IF conditional statements, such as =IF(A1>0, B1, C1).
    It evaluates the condition and returns the appropriate result based on the condition.
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        condition = parsed_formula["condition"]
        match = re.match(r"(.+?)(<=|>=|<>|=|<|>)(.+)", condition)
        if match:
            left_expr, operator, right_expr = [s.strip() for s in match.groups()]

            left_val = engine.execute_formula(
                f"={left_expr}", sheet_name, f"{cell_ref}_L"
            )
            right_val = engine.execute_formula(
                f"={right_expr}", sheet_name, f"{cell_ref}_R"
            )

            try:
                if operator == "=":
                    cond_result = left_val == right_val
                elif operator == "<>":
                    cond_result = left_val != right_val
                elif operator == ">":
                    cond_result = left_val > right_val
                elif operator == "<":
                    cond_result = left_val < right_val
                elif operator == ">=":
                    cond_result = left_val >= right_val
                elif operator == "<=":
                    cond_result = left_val <= right_val
            except TypeError:
                cond_result = False
        else:
            # When the condition does not contain an explicit comparison, treat
            # it as a formula whose truthiness determines the branch.
            cond_val = engine.execute_formula(
                f"={condition}", sheet_name, f"{cell_ref}_COND"
            )
            cond_result = bool(cond_val)

        def _eval(val, suffix):
            if isinstance(val, dict):
                if val["type"] in ("literal", "string_literal"):
                    return val["value"]
                return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")
            return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")

        if cond_result:
            return _eval(parsed_formula["true_val"], "T")
        else:
            return _eval(parsed_formula["false_val"], "F")


class IfErrorStrategy(CalculationStrategy):
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        try:
            value = parsed_formula["value"]
            if isinstance(value, dict) and value.get("type") == "unknown":
                expr = value.get("formula", "").lstrip("=")
                value_result = eval(expr)
            else:
                value_result = engine.execute_formula(
                    value, sheet_name, f"{cell_ref}_VAL"
                )

            if value_result is None or (
                isinstance(value_result, float) and math.isnan(value_result)
            ):
                raise Exception("Error")
            return value_result
        except Exception:
            fallback = parsed_formula["value_if_error"].strip()
            # ``value_if_error`` may itself be a literal, reference or complex
            # formula.  Delegating to ``execute_formula`` ensures it is handled
            # consistently with other expressions.
            return engine.execute_formula(f"={fallback}", sheet_name, f"{cell_ref}_ERR")


class PmtStrategy(CalculationStrategy):
    """Strategy for handling PMT formulas."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        import numpy_financial as npf

        def _eval_token(token: str, suffix: str):
            if token is None:
                return None
            tok = token.strip()
            negative = False
            if tok.startswith("-"):
                negative = True
                tok = tok[1:].strip()

            # Check for percentage
            if tok.endswith("%"):
                try:
                    val = float(tok.rstrip("%")) / 100
                except (ValueError, TypeError):
                    val = 0
            else:
                try:
                    # Try to convert to float directly
                    val = float(tok)
                except (ValueError, TypeError):
                    # If it fails, it might be a cell reference
                    val = engine.execute_formula(
                        f"={tok}", sheet_name, f"{cell_ref}_{suffix}"
                    )

            # Ensure val is numeric
            if val is None:
                val = 0
            elif isinstance(val, str):
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = 0
            elif isinstance(val, Number) and isinstance(val, float) and math.isnan(val):
                val = 0

            if negative:
                val = -val
            return val

        rate = _eval_token(parsed_formula["rate"], "RATE")
        nper = _eval_token(parsed_formula["nper"], "NPER")
        pv = _eval_token(parsed_formula["pv"], "PV")

        if rate is None or nper is None or pv is None:
            return 0.0

        # Ensure all inputs to npf.pmt are numeric. ``numbers.Number`` also
        # covers numpy numeric types such as ``np.int64`` and ``np.float64``
        # which appear when reading values from pandas DataFrames. This allows
        # the engine to operate on values loaded from ``pandas`` DataFrames
        # without explicit type casting.
        if not all(isinstance(v, Number) for v in [rate, nper, pv]) or nper == 0:
            return 0.0

        try:
            # npf.pmt can return NaN if inputs are invalid, handle this
            result = npf.pmt(rate, nper, pv)
            return float(result) if not math.isnan(result) else 0.0
        except Exception:
            return 0.0


class VLookupStrategy(CalculationStrategy):
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        lookup_token = parsed_formula["lookup_value"].strip()
        if lookup_token.startswith('"') and lookup_token.endswith('"'):
            lookup_value = lookup_token.strip('"')
        else:
            try:
                lookup_value = float(lookup_token)
            except ValueError:
                lookup_value = engine.execute_formula(
                    f"={lookup_token}", sheet_name, f"{cell_ref}_lk"
                )

        table_array = parsed_formula["table_array"].strip()
        if "!" in table_array:
            sheet_part, range_part = table_array.split("!", 1)
            table_sheet = sheet_part.strip().strip("'")
            table_range = range_part
        else:
            table_sheet = sheet_name
            table_range = table_array

        start_cell, end_cell = [c.replace("$", "") for c in table_range.split(":")]
        start_row, start_col = cell_to_coords(start_cell)
        end_row, end_col = cell_to_coords(end_cell)

        table_data = []
        for r in range(start_row, end_row + 1):
            row_vals = []
            for c in range(start_col, end_col + 1):
                cell = coords_to_cell(r, c)
                formula = engine.get_cell_formula(table_sheet, cell)
                if formula and isinstance(formula, str) and formula.startswith("="):
                    val = engine.execute_formula(formula, table_sheet, cell)
                else:
                    val = engine.get_cell_value(table_sheet, cell)
                row_vals.append(val)
            table_data.append(row_vals)

        col_index = int(parsed_formula["col_index_num"]) - 1
        range_lookup = parsed_formula["range_lookup"].strip().upper()

        if range_lookup == "FALSE":
            for row in table_data:
                if row and row[0] == lookup_value:
                    return row[col_index] if col_index < len(row) else None
            return None
        else:
            last_match = None
            for row in table_data:
                if row and row[0] is not None:
                    if row[0] <= lookup_value:
                        last_match = row
                    else:
                        break
            if last_match:
                return last_match[col_index] if col_index < len(last_match) else None
            return None


class NumberMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling simple number multiplication: number*number"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]
        return number1 * number2


class CellDivisionByNumberStrategy(CalculationStrategy):
    """Strategy for handling cell division by number: cell/number"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell = parsed_formula["cell"]
        number = parsed_formula["number"]

        # Get the cell value
        cell_value = engine.get_cell_value(sheet_name, cell)
        if cell_value is None:
            return None

        # Perform division
        try:
            return cell_value / number
        except (ZeroDivisionError, TypeError):
            return None


class ComplexMultiplicationDivisionStrategy(CalculationStrategy):
    """Strategy for handling complex multiplication with division patterns:
    - cell*cell/number*cell
    - (number*number)/(number)
    """

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        # Check if this is the cell-based format: cell*cell/number*cell
        if "cell1" in parsed_formula:
            cell1 = parsed_formula["cell1"]
            cell2 = parsed_formula["cell2"]
            number = parsed_formula["number"]
            cell3 = parsed_formula["cell3"]

            # Get cell values
            value1 = engine.get_cell_value(sheet_name, cell1)
            value2 = engine.get_cell_value(sheet_name, cell2)
            value3 = engine.get_cell_value(sheet_name, cell3)

            if value1 is None or value2 is None or value3 is None:
                return None

            # Perform calculation: cell1 * cell2 / number * cell3
            try:
                return value1 * value2 / number * value3
            except (ZeroDivisionError, TypeError):
                return None

        # Check if this is the number-based format: (number*number)/(number)
        elif "num1" in parsed_formula:
            num1 = parsed_formula["num1"]
            num2 = parsed_formula["num2"]
            divisor = parsed_formula["divisor"]

            # Perform calculation: (num1 * num2) / divisor
            try:
                return (num1 * num2) / divisor
            except (ZeroDivisionError, TypeError):
                return None

        else:
            logger.error(f"Unknown format for complex_multiplication_division: {parsed_formula}")
            return None


class CellDivisionByNumberMultiplicationStrategy(CalculationStrategy):
    """Strategy for cell division by number, multiplied by cell: cell/number*cell"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula["cell1"]
        number = parsed_formula["number"]
        cell2 = parsed_formula["cell2"]

        value1 = engine.get_cell_value(sheet_name, cell1)
        value2 = engine.get_cell_value(sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number * cell2
        try:
            return value1 / number * value2
        except (ZeroDivisionError, TypeError):
            return None


class NumberDivisionByCellStrategy(CalculationStrategy):
    """Strategy for number divided by cell: number/cell"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        number = parsed_formula["number"]
        cell = parsed_formula["cell"]

        value = engine.get_cell_value(sheet_name, cell)

        if value is None:
            return None

        # Perform calculation: number / cell
        try:
            return number / value
        except (ZeroDivisionError, TypeError):
            return None


class CellDivisionByNumberMultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for cell division by number, multiplied by cell, multiplied by number: cell/number*cell*number"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula["cell1"]
        number1 = parsed_formula["number1"]
        cell2 = parsed_formula["cell2"]
        number2 = parsed_formula["number2"]

        value1 = engine.get_cell_value(sheet_name, cell1)
        value2 = engine.get_cell_value(sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number1 * cell2 * number2
        try:
            return value1 / number1 * value2 * number2
        except (ZeroDivisionError, TypeError):
            return None


class CellDivisionByNumberDivisionByNumberStrategy(CalculationStrategy):
    """Strategy for cell division by number, divided by number: cell/number/number"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell = parsed_formula["cell"]
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]

        value = engine.get_cell_value(sheet_name, cell)

        if value is None:
            return None

        # Perform calculation: cell / number1 / number2
        try:
            return value / number1 / number2
        except (ZeroDivisionError, TypeError):
            return None


class MultiplicationThreeValuesStrategy(CalculationStrategy):
    """Strategy for multiplication of three values: cell1*cell2*number"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        operands = parsed_formula["operands"]
        number = parsed_formula["number"]

        # Get values for the two cells
        value1 = engine.get_cell_value(sheet_name, operands[0]["cell"])
        value2 = engine.get_cell_value(sheet_name, operands[1]["cell"])

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 * cell2 * number
        try:
            return value1 * value2 * number
        except (TypeError, ValueError):
            return None


class DivisionThreeValuesStrategy(CalculationStrategy):
    """Strategy for division of three values: cell1/number/cell2"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula["cell1"]
        number = parsed_formula["number"]
        cell2 = parsed_formula["cell2"]

        # Get values for the two cells
        value1 = engine.get_cell_value(sheet_name, cell1)
        value2 = engine.get_cell_value(sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number / cell2
        try:
            return value1 / number / value2
        except (ZeroDivisionError, TypeError):
            return None


class MultiplicationWithDivisionStrategy(CalculationStrategy):
    """Strategy for handling patterns like =H58*(H57/H58)"""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]
        cell3 = parsed_formula["cell3"]

        # Get values
        value1 = engine.get_cell_value(sheet_name, cell1)
        value2 = engine.get_cell_value(sheet_name, cell2)
        value3 = engine.get_cell_value(sheet_name, cell3)

        if value3 == 0:
            return None  # Avoid division by zero

        # Perform calculation: cell1 * (cell2 / cell3)
        try:
            return value1 * (value2 / value3)
        except (ZeroDivisionError, TypeError):
            return None


class PMTStrategy(CalculationStrategy, FinancialCostComponent):
    """Strategy for handling PMT function.

    This strategy handles Excel PMT function which calculates the payment for a loan
    based on constant payments and a constant interest rate.
    PMT(rate, nper, pv, fv, type)
    """

    def __init__(self):
        FinancialCostComponent.__init__(self, "PMT Strategy")

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(self, engine, parsed_formula, sheet_name, cell_ref):
        # PMT function parameters
        rate = parsed_formula.get("rate")
        nper = parsed_formula.get("nper")
        pv = parsed_formula.get("pv")
        fv = parsed_formula.get("fv", 0)  # Future value, defaults to 0
        pmt_type = parsed_formula.get("type", 0)  # 0 = end of period, 1 = beginning

        # Evaluate parameters if they are cell references
        if isinstance(rate, dict) and rate.get("type") == "reference":
            rate = engine.get_cell_value(rate.get("sheet", sheet_name), rate["cell"])
        if isinstance(nper, dict) and nper.get("type") == "reference":
            nper = engine.get_cell_value(nper.get("sheet", sheet_name), nper["cell"])
        if isinstance(pv, dict) and pv.get("type") == "reference":
            pv = engine.get_cell_value(pv.get("sheet", sheet_name), pv["cell"])
        if isinstance(fv, dict) and fv.get("type") == "reference":
            fv = engine.get_cell_value(fv.get("sheet", sheet_name), fv["cell"])

        # Validate parameters - ensure they are numbers
        if not isinstance(rate, Number) or not isinstance(nper, Number) or not isinstance(pv, Number):
            return None

        # Ensure fv is also a number (default to 0 if not provided)
        if not isinstance(fv, Number):
            fv = 0

        # Convert to float for calculations
        rate = float(rate)  # type: ignore
        nper = float(nper)  # type: ignore
        pv = float(pv)  # type: ignore
        fv = float(fv)  # type: ignore

        if rate == 0:
            # Simple case: if rate is 0, PMT = (pv + fv) / nper
            return (pv + fv) / nper

        # Standard PMT calculation
        try:
            if pmt_type == 0:  # Payment at end of period
                pmt = (rate * (pv * (1 + rate)**nper + fv)) / ((1 + rate)**nper - 1)
            else:  # Payment at beginning of period
                pmt = (rate * (pv * (1 + rate)**nper + fv)) / ((1 + rate)**nper - 1) * (1 + rate)
            return pmt
        except (ZeroDivisionError, OverflowError, ValueError):
            return None

    def get_component_type(self):
        return "financial"

    def validate_inputs(self, parsed_formula):
        required = ["rate", "nper", "pv"]
        return all(key in parsed_formula for key in required)

    def get_financial_function(self):
        return "pmt"

    def get_required_parameters(self):
        return ["rate", "nper", "pv"]


class ParenthesesMultiplicationDivisionStrategy(CalculationStrategy):
    """Strategy for handling complex expressions like (30*52)/(4204600)."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        divisor = parsed_formula["divisor"]

        if divisor == 0:
            return None

        return (num1 * num2) / divisor


class CellMultiplicationWithDivisionStrategy(CalculationStrategy):
    """Strategy for handling expressions like (H58*(H57/H58))."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]
        cell3 = parsed_formula["cell3"]

        val1 = engine.get_cell_value(sheet_name, cell1)
        val2 = engine.get_cell_value(sheet_name, cell2)
        val3 = engine.get_cell_value(sheet_name, cell3)

        if val3 == 0:
            return None

        return val1 * (val2 / val3)


class NestedArithmeticExpressionStrategy(CalculationStrategy):
    """Strategy for handling expressions like (2*(5/8*F4))."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        num3 = parsed_formula["num3"]
        cell = parsed_formula["cell"]

        val = engine.get_cell_value(sheet_name, cell)

        if num3 == 0:
            return None

        return num1 * (num2 / num3 * val)


class DivisionMultiplicationSequenceStrategy(CalculationStrategy):
    """Strategy for handling expressions like 365/3*D58."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        cell = parsed_formula["cell"]

        if num2 == 0:
            return None

        val = engine.get_cell_value(sheet_name, cell)
        return (num1 / num2) * val
