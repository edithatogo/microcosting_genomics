import openpyxl

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
        target_sheet = parsed_formula['sheet'] if parsed_formula['sheet'] is not None else sheet_name
        target_cell = parsed_formula['cell']
        
        # This is a recursive call to the engine to resolve the value of the referenced cell.
        # This will handle cases where the referenced cell also contains a formula.
        formula = engine.get_cell_formula(target_sheet, target_cell)
        if isinstance(formula, str) and formula.startswith('='):
            return engine.execute_formula(formula, target_sheet, target_cell)
        else:
            # If the referenced cell is not a formula, it's a direct value.
            return formula # The value from the data_only=False sheet is the direct value

class MultiplicationStrategy(CalculationStrategy):
    """Strategy for handling multiplication."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        result = 1
        for operand in parsed_formula['operands']:
            # Resolve the value of each operand recursively
            if operand['sheet'] is None:
                # This is a simple cell reference like 'E5'
                op_formula = engine.get_cell_formula(sheet_name, operand['cell'])
                if isinstance(op_formula, str) and op_formula.startswith('='):
                    op_value = engine.execute_formula(op_formula, sheet_name, operand['cell'])
                else:
                    op_value = op_formula
            else:
                # This is a reference with a sheet name like "'Sheet1'!E5"
                op_formula = engine.get_cell_formula(operand['sheet'], operand['cell'])
                if isinstance(op_formula, str) and op_formula.startswith('='):
                    op_value = engine.execute_formula(op_formula, operand['sheet'], operand['cell'])
                else:
                    op_value = op_formula
            
            if op_value is None or not isinstance(op_value, (int, float)):
                return None # Or handle as an error
            result *= op_value
        return result

class SumRangeStrategy(CalculationStrategy):
    """Strategy for handling SUM(A1:B2) formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        start_cell = parsed_formula['start_cell']
        end_cell = parsed_formula['end_cell']
        
        start_row, start_col = engine.cell_to_coords(start_cell)
        end_row, end_col = engine.cell_to_coords(end_cell)
        
        total = 0
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                cell = f"{openpyxl.utils.get_column_letter(c + 1)}{r + 1}"
                formula = engine.get_cell_formula(sheet_name, cell)
                if isinstance(formula, str) and formula.startswith('='):
                    value = engine.execute_formula(formula, sheet_name, cell)
                else:
                    value = formula
                
                if value is not None and isinstance(value, (int, float)):
                    total += value
        return total

class SumCellsStrategy(CalculationStrategy):
    """Strategy for handling SUM(A1,B2) formulas."""
    def execute(self, engine, parsed_formula, sheet_name, cell_ref):
        total = 0
        for cell in parsed_formula['cells']:
            formula = engine.get_cell_formula(sheet_name, cell)
            if isinstance(formula, str) and formula.startswith('='):
                value = engine.execute_formula(formula, sheet_name, cell)
            else:
                value = formula
            
            if value is not None and isinstance(value, (int, float)):
                total += value
        return total
