import pandas as pd
import openpyxl
from unimelb_phd_phase_1.formula_parser import parse_formula

def cell_to_coords(cell):
    """
    Converts an Excel cell reference (e.g., 'A1') to zero-based row and column indices.
    """
    if not isinstance(cell, str):
        return None, None

    col_str = ''.join(filter(str.isalpha, cell))
    row_str = ''.join(filter(str.isdigit, cell))

    if not col_str or not row_str:
        return None, None

    col = 0
    for char in col_str:
        col = col * 26 + (ord(char.upper()) - ord('A')) + 1
    col -= 1
    
    row = int(row_str) - 1
    
    return row, col

class CalculationEngine:
    def __init__(self, excel_file_path):
        self.excel_file_path = excel_file_path
        self.workbook = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        self.formula_workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)
        self.sheets = {}
        self.formula_sheets = {}

        for sheet_name in self.workbook.sheetnames:
            self.sheets[sheet_name] = self._load_sheet(self.workbook[sheet_name])
            self.formula_sheets[sheet_name] = self._load_sheet(self.formula_workbook[sheet_name])

    def _load_sheet(self, sheet):
        data = sheet.values
        # First three rows are headers, with the third being a separator line
        header1 = [h if h is not None else '' for h in next(data)]
        header2 = [h if h is not None else '' for h in next(data)]
        next(data) # skip separator line
        
        # Combine headers
        header = [f"{h1}_{h2}" if h1 else h2 for h1, h2 in zip(header1, header2)]
        
        df = pd.DataFrame(data, columns=header)
        return df

    def get_cell_value(self, sheet_name, cell):
        row, col = cell_to_coords(cell)
        print(f"get_cell_value: sheet={sheet_name}, cell={cell}, row={row}, col={col}")
        if row is None or col is None:
            return None
        # Adjust row for headers, openpyxl is 1-based, pandas is 0-based
        row -= 3 # 3 header rows
        print(f"get_cell_value: adjusted row={row}")
        if row < 0:
            return None
        
        value = self.sheets[sheet_name].iloc[row, col]
        print(f"get_cell_value: returning {value}")
        return value

    def get_cell_formula(self, sheet_name, cell):
        row, col = cell_to_coords(cell)
        if row is None or col is None:
            return None
        # Adjust row for headers, openpyxl is 1-based, pandas is 0-based
        row -= 3 # 3 header rows
        if row < 0:
            return None
        return self.formula_sheets[sheet_name].iloc[row, col]

    def execute_formula(self, formula):
        parsed_formula = parse_formula(formula)

        if parsed_formula is None:
            return None

        if parsed_formula['type'] == 'literal':
            return parsed_formula['value']

        if parsed_formula['type'] == 'reference':
            sheet = parsed_formula['sheet']
            cell = parsed_formula['cell']
            # This is a simplification, as the sheet might not be the same as the
            # sheet the formula is on.
            # I will need to handle this later.
            if sheet is None:
                # This is a temporary solution. I need to know which sheet the formula belongs to.
                # For now, I will assume the first sheet.
                sheet = self.workbook.sheetnames[0]
            return self.get_cell_value(sheet, cell)

        # I will add more logic here to handle the other formula types.

        return None
