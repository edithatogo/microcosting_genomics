import openpyxl
import math
from .utils import coords_to_cell, cell_to_coords

class CalculationStrategy:
    """Base class for a formula calculation strategy."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        raise NotImplementedError

class LiteralStrategy(CalculationStrategy):
    """Strategy for handling literal values."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        return parsed_formula['value']

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

            if isinstance(value, (int, float)):
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
                
                if isinstance(value, (int, float)) and not math.isnan(value):
                    total += value
        return total

class SumCellsStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with individual cells."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for cell_info in parsed_formula['cells']:
            cell = cell_info['cell']
            # Assuming 'sheet' key might be missing, default to current sheet
            sheet = cell_info.get('sheet', sheet_name) 
            
            formula = engine.get_cell_formula(sheet, cell)
            if formula and isinstance(formula, str) and formula.startswith('='):
                value = engine.execute_formula(formula, sheet, cell)
            else:
                value = engine.get_cell_value(sheet, cell)
            
            if isinstance(value, (int, float)) and not math.isnan(value):
                total += value
        return total

class MultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for handling multiplication by a number."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        cell = parsed_formula['cell']
        number = parsed_formula['number']
        
        formula = engine.get_cell_formula(sheet_name, cell)
        if formula and isinstance(formula, str) and formula.startswith('='):
            value = engine.execute_formula(formula, sheet_name, cell)
        else:
            value = engine.get_cell_value(sheet_name, cell)
            
        if isinstance(value, (int, float)):
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

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
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
            val2 = engine.execute_formula(formula2, sheet_name, val2_cell)
        else:
            val2 = engine.get_cell_value(sheet_name, cell2)

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)) and val2 != 0 and number != 0:
            return val1 / number / val2
        else:
            return None

class IfStrategy(CalculationStrategy):
    """Strategy for handling IF formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        # This is a placeholder implementation.
        # A real implementation would need to evaluate the condition.
        return "IF_NOT_IMPLEMENTED"

class IfErrorStrategy(CalculationStrategy):
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        # To be implemented
        return "IFERROR_NOT_IMPLEMENTED"

class VLookupStrategy(CalculationStrategy):
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        # To be implemented
        return "VLOOKUP_NOT_IMPLEMENTED"
