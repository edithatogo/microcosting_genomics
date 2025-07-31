import openpyxl
import math
import re
from numbers import Number
from .utils import coords_to_cell, cell_to_coords
from .formula_parser import parse_formula

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
        referenced_sheet = parsed_formula['sheet']
        referenced_cell = parsed_formula['cell']

        if referenced_sheet is None:
            referenced_sheet = sheet_name
        
        formula = engine.get_cell_formula(referenced_sheet, referenced_cell)

        if formula and isinstance(formula, str) and formula.startswith('='):
            return engine.execute_formula(formula, referenced_sheet, referenced_cell)
        
        return engine.get_cell_value(referenced_sheet, referenced_cell)

class AdditionStrategy(CalculationStrategy):
    """Strategy for handling addition formulas."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for idx, operand in enumerate(parsed_formula['operands']):
            value = None
            if isinstance(operand, dict) and operand.get('type') == 'literal':
                value = operand['value']
            elif isinstance(operand, dict) and operand.get('type') == 'reference':
                op_sheet = operand['sheet'] if operand['sheet'] else sheet_name
                op_cell = operand['cell']
                formula = engine.get_cell_formula(op_sheet, op_cell)
                if formula is not None:
                    if isinstance(formula, str) and formula.startswith('='):
                        value = engine.execute_formula(formula, op_sheet, op_cell)
                    else:
                        value = engine.execute_formula(formula, op_sheet, op_cell)
                else:
                    value = engine.get_cell_value(op_sheet, op_cell)
            else:
                value = engine.execute_formula(operand, sheet_name, f"{cell_ref}_{idx}")

            if isinstance(value, Number) and not (isinstance(value, float) and math.isnan(value)):
                total += value
            else:
                return None
        return total

class MultiplicationStrategy(CalculationStrategy):
    """Strategy for handling multiplication formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = 1
        for operand in parsed_formula['operands']:
            value = None
            if 'sheet' in operand and 'cell' in operand:
                # It's a cell reference
                op_sheet = operand['sheet'] if operand['sheet'] else sheet_name
                op_cell = operand['cell']
                
                formula = engine.get_cell_formula(op_sheet, op_cell)
                if formula and isinstance(formula, str) and formula.startswith('='):
                    value = engine.execute_formula(formula, op_sheet, op_cell)
                else:
                    value = engine.get_cell_value(op_sheet, op_cell)
                
            elif 'type' in operand and operand['type'] == 'literal':
                # It's a literal value
                value = operand['value']

            if isinstance(value, Number):
                result *= value
            else:
                # If any operand is not a number, the result is invalid
                return None
        return result

class SumRangeStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with a range."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        start_cell = parsed_formula['start_cell']
        end_cell = parsed_formula['end_cell']
        
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
                
                if isinstance(value, Number) and not (isinstance(value, float) and math.isnan(value)):
                    total += value
        return total

class SumCellsStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with individual cells."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for cell_info in parsed_formula['cells']:
            if isinstance(cell_info, str):
                try:
                    value = float(cell_info)
                    total += value
                    continue
                except ValueError:
                    cell = cell_info
                    sheet = sheet_name
            else:
                cell = cell_info['cell']
                sheet = cell_info.get('sheet', sheet_name)

            formula = engine.get_cell_formula(sheet, cell)
            if formula and isinstance(formula, str) and formula.startswith('='):
                value = engine.execute_formula(formula, sheet, cell)
            else:
                value = engine.get_cell_value(sheet, cell)

            if isinstance(value, Number) and not (isinstance(value, float) and math.isnan(value)):
                total += value
        return total

class MultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for handling multiplication by a number."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell = parsed_formula['cell']
        number = parsed_formula['number']

        target_sheet = parsed_formula.get('sheet', sheet_name)

        formula = engine.get_cell_formula(target_sheet, cell)
        if formula and isinstance(formula, str) and formula.startswith('='):
            value = engine.execute_formula(formula, target_sheet, cell)
        else:
            value = engine.get_cell_value(target_sheet, cell)
            
        if isinstance(value, Number):
            return value * number
        else:
            return None

class MultiplicationThreeValuesStrategy(CalculationStrategy):
    """Strategy for handling multiplication of three values (cell*cell*number)."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        operands = parsed_formula['operands']
        number = parsed_formula['number']

        val1_cell = operands[0]['cell']
        val2_cell = operands[1]['cell']

        val1 = engine.get_cell_value(sheet_name, val1_cell)
        formula1 = engine.get_cell_formula(sheet_name, val1_cell)
        if formula1 and isinstance(formula1, str) and formula1.startswith('='):
            val1 = engine.execute_formula(formula1, sheet_name, val1_cell)
        else:
            val1 = engine.get_cell_value(sheet_name, val1_cell)

        val2 = engine.get_cell_value(sheet_name, val2_cell)
        formula2 = engine.get_cell_formula(sheet_name, val2_cell)
        if formula2 and isinstance(formula2, str) and formula2.startswith('='):
            val2 = engine.execute_formula(formula2, sheet_name, val2_cell)
        else:
            val2 = engine.get_cell_value(sheet_name, val2_cell)

        if isinstance(val1, Number) and isinstance(val2, Number):
            return val1 * val2 * number
        else:
            return None

class DivisionThreeValuesStrategy(CalculationStrategy):
    """Strategy for handling division of three values (cell/number/cell)."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell1 = parsed_formula['cell1']
        number = parsed_formula['number']
        cell2 = parsed_formula['cell2']

        val1 = engine.get_cell_value(sheet_name, cell1)
        formula1 = engine.get_cell_formula(sheet_name, cell1)
        if formula1 and isinstance(formula1, str) and formula1.startswith('='):
            val1 = engine.execute_formula(formula1, sheet_name, cell1)
        else:
            val1 = engine.get_cell_value(sheet_name, cell1)

        val2 = engine.get_cell_value(sheet_name, cell2)
        formula2 = engine.get_cell_formula(sheet_name, cell2)
        if formula2 and isinstance(formula2, str) and formula2.startswith('='):
            val2 = engine.execute_formula(formula2, sheet_name, cell2)
        else:
            val2 = engine.get_cell_value(sheet_name, val2)

        if isinstance(val1, Number) and isinstance(val2, Number) and val2 != 0 and number != 0:
            return val1 / number / val2
        else:
            return None

class IfStrategy(CalculationStrategy):
    """Strategy for handling IF formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        condition = parsed_formula['condition']
        match = re.match(r"(.+?)(<=|>=|<>|=|<|>)(.+)", condition)
        if not match:
            return None

        left_expr, operator, right_expr = [s.strip() for s in match.groups()]

        left_val = engine.execute_formula(f"={left_expr}", sheet_name, f"{cell_ref}_L")
        right_val = engine.execute_formula(f"={right_expr}", sheet_name, f"{cell_ref}_R")

        try:
            if operator == '=':
                cond_result = left_val == right_val
            elif operator == '<>':
                cond_result = left_val != right_val
            elif operator == '>':
                cond_result = left_val > right_val
            elif operator == '<':
                cond_result = left_val < right_val
            elif operator == '>=':
                cond_result = left_val >= right_val
            elif operator == '<=':
                cond_result = left_val <= right_val
            else:
                cond_result = False
        except Exception:
            cond_result = False

        def _eval(val, suffix):
            if isinstance(val, dict):
                if val['type'] in ('literal', 'string_literal'):
                    return val['value']
                return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")
            return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")

        if cond_result:
            return _eval(parsed_formula['true_val'], 'T')
        else:
            return _eval(parsed_formula['false_val'], 'F')

class IfErrorStrategy(CalculationStrategy):
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        try:
            value = parsed_formula['value']
            if isinstance(value, dict) and value.get('type') == 'unknown':
                expr = value.get('formula', '').lstrip('=')
                value_result = eval(expr)
            else:
                value_result = engine.execute_formula(value, sheet_name, f"{cell_ref}_VAL")

            if value_result is None or (isinstance(value_result, float) and math.isnan(value_result)):
                raise Exception('Error')
            return value_result
        except Exception:
            fallback = parsed_formula['value_if_error'].strip()
            return engine.execute_formula(f'={fallback}', sheet_name, f"{cell_ref}_ERR")

class PmtStrategy(CalculationStrategy):
    """Strategy for handling PMT formulas."""

    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        import numpy_financial as npf

        def _eval_token(token: str, suffix: str):
            tok = token.strip()
            negative = False
            if tok.startswith('-'):
                negative = True
                tok = tok[1:].strip()

            # Check for percentage
            if tok.endswith('%'):
                try:
                    val = float(tok.rstrip('%')) / 100
                except (ValueError, TypeError):
                    val = 0
            else:
                try:
                    # Try to convert to float directly
                    val = float(tok)
                except (ValueError, TypeError):
                    # If it fails, it might be a cell reference
                    val = engine.execute_formula(f"={tok}", sheet_name, f"{cell_ref}_{suffix}")

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

        rate = _eval_token(parsed_formula['rate'], 'RATE')
        nper = _eval_token(parsed_formula['nper'], 'NPER')
        pv = _eval_token(parsed_formula['pv'], 'PV')

        # Ensure all inputs to npf.pmt are numeric
        # Accept any numeric type, including NumPy numbers
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
        lookup_token = parsed_formula['lookup_value'].strip()
        try:
            lookup_value = float(lookup_token)
        except ValueError:
            lookup_value = engine.execute_formula(
                f"={lookup_token}", sheet_name, f"{cell_ref}_lk"
            )

        table_array = parsed_formula['table_array'].strip()
        if '!' in table_array:
            sheet_part, range_part = table_array.split('!', 1)
            table_sheet = sheet_part.strip().strip("'")
            table_range = range_part
        else:
            table_sheet = sheet_name
            table_range = table_array

        start_cell, end_cell = [c.replace('$', '') for c in table_range.split(':')]
        start_row, start_col = cell_to_coords(start_cell)
        end_row, end_col = cell_to_coords(end_cell)

        table_data = []
        for r in range(start_row, end_row + 1):
            row_vals = []
            for c in range(start_col, end_col + 1):
                cell = coords_to_cell(r, c)
                formula = engine.get_cell_formula(table_sheet, cell)
                if formula and isinstance(formula, str) and formula.startswith('='):
                    val = engine.execute_formula(formula, table_sheet, cell)
                else:
                    val = engine.get_cell_value(table_sheet, cell)
                row_vals.append(val)
            table_data.append(row_vals)

        col_index = int(parsed_formula['col_index_num']) - 1
        range_lookup = parsed_formula['range_lookup'].strip().upper()

        if range_lookup == 'FALSE':
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
