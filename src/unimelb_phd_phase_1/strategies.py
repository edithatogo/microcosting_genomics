import math
import re
from numbers import Number

from .utils import cell_to_coords, coords_to_cell


class CalculationStrategy:
    """Base class for a formula calculation strategy."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        raise NotImplementedError


class LiteralStrategy(CalculationStrategy):
    """Strategy for handling numeric literals."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return parsed_formula["value"]


class StringLiteralStrategy(CalculationStrategy):
    """Strategy for handling string literals."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return parsed_formula["value"]


class ReferenceStrategy(CalculationStrategy):
    """Strategy for handling cell references."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        referenced_sheet = parsed_formula["sheet"]
        referenced_cell = parsed_formula["cell"]

        if referenced_sheet is None:
            referenced_sheet = sheet_name

        formula = engine.get_cell_formula(referenced_sheet, referenced_cell)

        if formula and isinstance(formula, str) and formula.startswith("="):
            return engine.execute_formula(formula, referenced_sheet, referenced_cell)

        return engine.get_cell_value(referenced_sheet, referenced_cell)

def _evaluate_operand(engine, operand, sheet_name, cell_ref):
    """Helper function to evaluate an operand."""
    if isinstance(operand, dict):
        if operand.get('type') == 'literal':
            return operand['value']
        elif operand.get('type') == 'reference':
            op_sheet = operand['sheet'] if operand['sheet'] else sheet_name
            op_cell = operand['cell']
            formula = engine.get_cell_formula(op_sheet, op_cell)
            if formula and isinstance(formula, str) and formula.startswith('='):
                return engine.execute_formula(formula, op_sheet, op_cell)
            else:
                return engine.get_cell_value(op_sheet, op_cell)
    return engine.execute_formula(operand, sheet_name, cell_ref)

class AdditionStrategy(CalculationStrategy):
    """Strategy for handling addition formulas."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for idx, operand in enumerate(parsed_formula['operands']):
            value = _evaluate_operand(engine, operand, sheet_name, f"{cell_ref}_{idx}")
            if isinstance(value, Number) and not (isinstance(value, float) and math.isnan(value)):
                total += value
            else:
                return None
        return total


class MultiplicationStrategy(CalculationStrategy):
    """Strategy for handling multiplication formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = 1
        for idx, operand in enumerate(parsed_formula['operands']):
            value = _evaluate_operand(engine, operand, sheet_name, f"{cell_ref}_{idx}")
            if isinstance(value, Number):
                result *= value
            else:
                return None
        return result


class SumRangeStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with a range."""

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
    """Strategy for handling SUM formulas with individual cells."""

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
    """Strategy for handling division formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = _evaluate_operand(engine, parsed_formula['operands'][0], sheet_name, f"{cell_ref}_0")
        for idx, operand in enumerate(parsed_formula['operands'][1:]):
            value = _evaluate_operand(engine, operand, sheet_name, f"{cell_ref}_{idx+1}")
            if isinstance(value, Number) and value != 0:
                result /= value
            else:
                return None
        return result


class IfStrategy(CalculationStrategy):
    """Strategy for handling IF formulas."""

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

            # Ensure val is a number, default to 0 if it's None or NaN
            if val is None or (isinstance(val, float) and math.isnan(val)):
                val = 0
            if isinstance(val, str):
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = 0
            if negative:
                val = -val
            return val

        rate = _eval_token(parsed_formula["rate"], "RATE")
        nper = _eval_token(parsed_formula["nper"], "NPER")
        pv = _eval_token(parsed_formula["pv"], "PV")

        # Ensure all inputs to npf.pmt are numeric. ``numbers.Number`` also
        # covers numpy numeric types such as ``np.int64`` and ``np.float64``
        # which appear when reading values from pandas DataFrames. This allows
        # the engine to operate on values loaded from ``pandas`` DataFrames
        # without explicit type casting.
        if not all(isinstance(v, Number) for v in [rate, nper, pv]):
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
        if lookup_token.startswith("\"") and lookup_token.endswith("\""):
            lookup_value = lookup_token.strip("\"")
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


class UnknownStrategy(CalculationStrategy):
    """Fallback strategy for unsupported formulas."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return None
