import pandas as pd
import os
import openpyxl
from unimelb_phd_phase_1.formula_parser import parse_formula
from unimelb_phd_phase_1.strategies import (
    LiteralStrategy,
    ReferenceStrategy,
    MultiplicationStrategy,
    SumRangeStrategy,
    SumCellsStrategy,
)

def create_unique_column_names(columns):
    """
    Given a list of column names, ensures each name is unique by appending a suffix if needed.
    """
    seen = {}
    unique_columns = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            unique_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            unique_columns.append(col)
    return unique_columns

class CalculationEngine:
    def cell_to_coords(self, cell):
        """
        Converts an Excel cell reference (e.g., 'A1', '$A1', 'A$1', '$A$1') to zero-based row and column indices.
        """
        if not isinstance(cell, str):
            return None, None

        cell = cell.replace('$', '')
        col_str = ''.join(filter(str.isalpha, cell))
        row_str = ''.join(filter(str.isdigit, cell))

        if not col_str or not row_str:
            return None, None

        col = 0
        for char in col_str:
            col = col * 26 + (ord(char.upper()) - ord('A') + 1)
        col -= 1
        
        row = int(row_str) - 1
        
        return row, col

    def __init__(self, excel_file_path='data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm'):
        self.excel_file_path = excel_file_path
        self.sheets = {}
        self.formula_sheets = {} # This will be populated on demand
        self.memoization_cache = {}
        self.call_stack = []
        self.strategy_map = {
            'literal': LiteralStrategy(),
            'reference': ReferenceStrategy(),
            'multiplication': MultiplicationStrategy(),
            'sum_range': SumRangeStrategy(),
            'sum_cells': SumCellsStrategy(),
            # More strategies will be added here
        }

        self._load_all_sheets()

    def _load_all_sheets(self):
        """Loads all sheets from the Excel file into the engine."""
        workbook = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            
            # Read the header rows separately to construct column names
            header_df = pd.DataFrame(sheet.values)
            
            if sheet_name == 'Detailed Table':
                h1 = header_df.iloc[0].ffill()
                h2 = header_df.iloc[1].fillna('')
                h3 = header_df.iloc[2].fillna('')
                
                new_columns = []
                for i in range(header_df.shape[1]):
                    full_header = f"{h1[i]} {h2[i]} {h3[i]}".replace('nan', '').strip()
                    full_header = ' '.join(full_header.split())
                    if not full_header:
                        full_header = f"unnamed_{i}"
                    new_columns.append(full_header)
                
                unique_columns = create_unique_column_names(new_columns)
                
                data_df = pd.DataFrame(list(sheet.values)[3:], columns=unique_columns)
            else:
                # For other sheets, assume the first row is the header
                columns = create_unique_column_names(list(sheet.values)[0])
                data_df = pd.DataFrame(list(sheet.values)[1:], columns=columns)

            # Coerce all columns to numeric where possible
            for col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')

            self.sheets[sheet_name] = data_df

    def get_cell_value(self, sheet_name, cell):
        row, col = self.cell_to_coords(cell)
        if row is None or col is None:
            return None
        return self.sheets[sheet_name].iat[row, col]

    def get_cell_formula(self, sheet_name, cell):
        # Formula sheets are loaded on demand to save memory
        if sheet_name not in self.formula_sheets:
            workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)
            sheet = workbook[sheet_name]
            
            # Use the same cleaned headers as the data sheet
            columns = self.sheets[sheet_name].columns
            
            # Read the formula sheet, skipping the header rows
            if sheet_name == 'Detailed Table':
                df = pd.DataFrame(list(sheet.values)[3:], columns=columns)
            else:
                df = pd.DataFrame(list(sheet.values)[1:], columns=columns)
            
            self.formula_sheets[sheet_name] = df

        row, col = self.cell_to_coords(cell)
        if row is None or col is None:
            return None
        
        # Adjust for the header rows that were skipped
        if sheet_name == 'Detailed Table':
            return self.formula_sheets[sheet_name].iat[row - 3, col]
        else:
            return self.formula_sheets[sheet_name].iat[row - 1, col]

    def execute_formula(self, formula, sheet_name, cell_ref):
        """
        Executes a given formula in the context of a sheet and cell.
        """
        # First, check for circular references
        if (sheet_name, cell_ref) in self.call_stack:
            raise Exception(f"Circular reference detected: {self.call_stack + [(sheet_name, cell_ref)]}")
        self.call_stack.append((sheet_name, cell_ref))

        # First, check the cache
        if (sheet_name, cell_ref) in self.memoization_cache:
            self.call_stack.pop()
            return self.memoization_cache[(sheet_name, cell_ref)]

        parsed_formula = parse_formula(formula)

        if parsed_formula is None:
            self.call_stack.pop()
            return None # Or handle as an error

        strategy = self.strategy_map.get(parsed_formula['type'])

        if strategy:
            result = strategy.execute(self, parsed_formula, sheet_name, cell_ref)
        else:
            result = f"UNSUPPORTED[{parsed_formula['type']}]"

        # Store the result in the cache before returning
        self.memoization_cache[(sheet_name, cell_ref)] = result
        self.call_stack.pop()
        return result