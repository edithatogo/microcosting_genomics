import logging
import pandas as pd
from pathlib import Path

import openpyxl
import pandas as pd
import re
import logging
import warnings

logger = logging.getLogger(__name__)

from .config import load_config
from .formula_parser import parse_formula
from .strategies import (
    LiteralStrategy,
    ReferenceStrategy,
    MultiplicationStrategy,
    SumRangeStrategy,
    SumCellsStrategy,
    MultiplicationByNumberStrategy,
    MultiplicationThreeValuesStrategy,
    DivisionThreeValuesStrategy,
    AdditionStrategy,
    IfStrategy,
    IfErrorStrategy,
    VLookupStrategy,
    PmtStrategy,
)
from .utils import cell_to_coords, coords_to_cell

logger = logging.getLogger(__name__)

class CalculationEngine:
    def __init__(
        self,
        excel_file_path: Path | str | None = None,
        verbose: bool = False,
        prepared_data_path: Path | str | None = None,
    ):
        self.logger = logger.getChild(self.__class__.__name__)
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            self.logger.addHandler(handler)

        config = load_config()
        self.config = config
        if excel_file_path is None:
            workbook_key = config.get("default_workbook", "main")
            excel_file_path = config["workbooks"][workbook_key]["path"]
        self.excel_file_path = Path(excel_file_path)
        if prepared_data_path is None:
            prepared_data_path = Path(__file__).resolve().parents[2] / "data" / "prepared"
        self.prepared_data_path = Path(prepared_data_path)
        sheet_names = config.get("workbooks", {}).get(config.get("default_workbook", "main"), {}).get("sheets", {})
        self.default_sheet_names = {
            "detailed_table": sheet_names.get("detailed_table", "Detailed Table")
        }
        self.sheets = {}
        self.formula_sheets = {} # This will be populated on demand
        self.memoization_cache = {}
        self.call_stack = []
        self.strategy_map = {
            'literal': LiteralStrategy(),
            'reference': ReferenceStrategy(),
            'multiplication': MultiplicationStrategy(),
            'addition': AdditionStrategy(),
            'sum_range': SumRangeStrategy(),
            'sum_cells': SumCellsStrategy(),
            'multiplication_by_number': MultiplicationByNumberStrategy(),
            'division_three_values': DivisionThreeValuesStrategy(),
            'if': IfStrategy(),
            'iferror': IfErrorStrategy(),
            'vlookup': VLookupStrategy(),
            'pmt': PmtStrategy(),
            # More strategies will be added here
        }
        self.sheet_configs = {
            'Detailed Table': {'header_rows': 4, 'data_starts_at': 5, 'string_columns': ['Test', 'Category', 'Sub-Category', 'Step']},
            '2. Labor Prices': {'header_rows': 1, 'data_starts_at': 2},
            '3. Estimates': {'header_rows': 1, 'data_starts_at': 2},
            '4. DSA - Equipment Throughput': {'header_rows': 1, 'data_starts_at': 2},
            '5. DSA - Overheads': {'header_rows': 1, 'data_starts_at': 2},
            '6. DSA - Consumable Discounts': {'header_rows': 1, 'data_starts_at': 2},
            '7. DSA - Labor Prices': {'header_rows': 1, 'data_starts_at': 2},
            '8. PSA': {'header_rows': 1, 'data_starts_at': 2},
            'Process': {'header_rows': 1, 'data_starts_at': 2},
            'Sheet1': {'header_rows': 1, 'data_starts_at': 2},
            'Summary Table': {'header_rows': 1, 'data_starts_at': 2},
            'At a Glance': {'header_rows': 1, 'data_starts_at': 2},
            'Labour - Usage - VCGS': {'header_rows': 1, 'data_starts_at': 2},
            'Cons -  Costs and Util - VCGS': {'header_rows': 1, 'data_starts_at': 2},
            'Eq - Costs and Usage - VCGS': {'header_rows': 1, 'data_starts_at': 2},
            'Labour - Costs - VCGS': {'header_rows': 1, 'data_starts_at': 2},
        }

        # Allow the detailed table sheet name to be overridden by configuration
        configured_name = self.default_sheet_names["detailed_table"]
        if configured_name != "Detailed Table":
            self.sheet_configs[configured_name] = self.sheet_configs.pop("Detailed Table")

        # Load workbook once with data_only=False to access formulas and merged cells
        self._workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)

        self._load_all_sheets()
        self._load_prepared_tables()

    def _load_all_sheets(self):
        """Loads all sheets from the Excel file into the engine."""
        print(f"Loading sheets from: {self.excel_file_path}")
        print(f"Workbook sheet names: {self._workbook.sheetnames}")

        for sheet_name in self._workbook.sheetnames:
            print(f"Processing sheet: {sheet_name}")
            if sheet_name in self.sheet_configs:
                print(f"  Config found for {sheet_name}: {self.sheet_configs[sheet_name]}")
                sheet_obj = self._workbook[sheet_name]
                
                # Load raw data (values and formulas) using openpyxl
                all_data_values, all_data_formulas = self._load_raw_sheet_data(sheet_obj)

                # Process raw dataframes (handle headers, fill merged cells, coerce types)
                self.sheets[sheet_name] = self._process_raw_dataframe(all_data_values, sheet_obj, sheet_name, data_only=True)
                self.formula_sheets[sheet_name] = self._process_raw_dataframe(all_data_formulas, sheet_obj, sheet_name, data_only=False)
            else:
                print(f"  No config found for {sheet_name}, skipping.")

    def _load_prepared_tables(self):
        """Load pre-parsed parquet tables if available."""
        if not self.prepared_data_path.exists():
            return

        mapping = {
            "2. Labor Prices": self.prepared_data_path / "2._labor_prices.parquet",
            "3. Estimates": self.prepared_data_path / "3._estimates.parquet",
        }

        for name, path in mapping.items():
            if path.exists():
                self.logger.debug("Loading prepared table %s from %s", name, path)
                df = pd.read_parquet(path)
                self.sheets[name] = df
                self.formula_sheets[name] = df

    def _load_raw_sheet_data(self, sheet_obj):
        """
        Loads the raw data from a sheet.
        It handles merged cells by looking up the value from the top-left cell.
        """
        sheet_name = sheet_obj.title
        print(f"  _load_raw_sheet_data called for sheet: {sheet_name}")

        ws = sheet_obj

        # Pre-process merged cells for fast lookup
        merged_lookup = {}
        for merged_range in ws.merged_cells.ranges:
            min_row, min_col, max_row, max_col = merged_range.bounds
            top_left_cell = ws.cell(row=min_row, column=min_col)
            val = top_left_cell.value
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    merged_lookup[(row, col)] = val
        
        # Extract data using the lookup for merged cells
        data = []
        for row_idx, row in enumerate(ws.iter_rows(), start=1):
            row_data = []
            for col_idx, cell in enumerate(row, start=1):
                if (row_idx, col_idx) in merged_lookup:
                    row_data.append(merged_lookup[(row_idx, col_idx)])
                else:
                    row_data.append(cell.value)
            data.append(row_data)

        # Since we only have one workbook view (data_only=False),
        # we return the same data for both values and formulas.
        return data, data

    def _process_raw_dataframe(self, raw_data, sheet_obj, sheet_name, data_only):
        print(f"  _process_raw_dataframe called for sheet: {sheet_name}, data_only: {data_only}")

        self.logger.debug("  _process_raw_dataframe called for sheet: %s, data_only: %s", sheet_name, data_only)
        config = self.sheet_configs[sheet_name]
        header_rows = config['header_rows']
        data_starts_at = config['data_starts_at']

        df = pd.DataFrame(raw_data)
        self.logger.debug("    Sheet: %s, df.shape: %s", sheet_name, df.shape)

        if header_rows > 0:
            header_df = df.iloc[:header_rows].copy()
            self.logger.debug("    Sheet: %s, header_df.shape: %s", sheet_name, header_df.shape)
            header_df = header_df.ffill(axis=0)
            
            if sheet_name == self.default_sheet_names["detailed_table"]:
                self.logger.debug("--- DEBUG: Detailed Table Header ---")
                self.logger.debug("%s", header_df.to_string())
                self.logger.debug("------------------------------------")

            data_df = df.iloc[data_starts_at - 1:].copy()
            self.logger.debug(f"    Sheet: {sheet_name}, data_df.shape: {data_df.shape}")
            self.logger.debug(f"    Sheet: {sheet_name}, header_df.shape[1]: {header_df.shape[1]}")
            level_names = [f"level_{i}" for i in range(header_rows)]
            data_df.columns = pd.MultiIndex.from_arrays(
                header_df.values,
                names=level_names,
            )
            self.logger.debug("    Sheet: %s, data_df.shape: %s", sheet_name, data_df.shape)
            self.logger.debug("    Sheet: %s, header_df.shape[1]: %s", sheet_name, header_df.shape[1])
            data_df.columns = pd.MultiIndex.from_arrays(header_df.values)

            if sheet_name == self.default_sheet_names["detailed_table"]:
                self.logger.debug("--- DEBUG: Detailed Table Columns ---")
                self.logger.debug("%s", data_df.columns)
                self.logger.debug("-------------------------------------")
                self.logger.debug("--- DEBUG: Detailed Table Data (Before Coercion) ---")
                self.logger.debug("%s", data_df.head().to_string())
                self.logger.debug("----------------------------------------------------")
        else:
            data_df = df.iloc[data_starts_at - 1:].copy()
        
        data_df.reset_index(drop=True, inplace=True)

        if data_only:
            string_columns = config.get('string_columns', [])
            # Coerce all columns to numeric where possible, but don't fill NaNs
            for col_name, series in data_df.items():
                # col_name can be a tuple if there's a multi-index
                col_name_str = col_name[0] if isinstance(col_name, tuple) else col_name
                if col_name_str not in string_columns:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
                        data_df[col_name] = pd.to_numeric(series, errors="coerce")
            
            if sheet_name == self.default_sheet_names["detailed_table"]:
                self.logger.debug("--- DEBUG: Detailed Table Data (After Coercion) ---")
                self.logger.debug("%s", data_df.head().to_string())
                self.logger.debug("---------------------------------------------------")
        return data_df

    def get_cell_value(self, sheet_name, cell_ref):
        self.logger.debug("get_cell_value called for sheet: %s, cell: %s", sheet_name, cell_ref)
        row_idx, col_idx = cell_to_coords(cell_ref) # These are 0-indexed
        if row_idx is None or col_idx is None:
            self.logger.debug("Invalid cell_ref: %s", cell_ref)
            return None

        if sheet_name not in self.sheets:
            self.logger.debug("Sheet '%s' not found in self.sheets.", sheet_name)
            return None

        config = self.sheet_configs.get(sheet_name, {'header_rows': 0, 'data_starts_at': 1})
        data_starts_at = config['data_starts_at']
        
        # Adjust row_idx for DataFrame indexing (data_starts_at is 1-indexed Excel row)
        df_row_idx = row_idx - (data_starts_at - 1)
        
       
        self.logger.debug(
            "Excel row_idx=%s, col_idx=%s -> DataFrame df_row_idx=%s",
            row_idx,
            col_idx,
            df_row_idx,
        )

        if df_row_idx < 0 or df_row_idx >= len(self.sheets[sheet_name]):
            self.logger.debug("df_row_idx %s is out of bounds for sheet %s.", df_row_idx, sheet_name)
            return None # Or handle as an error

        value = self.sheets[sheet_name].iloc[df_row_idx, col_idx]
        self.logger.debug("Retrieved value: %s", value)
        return value

    def get_cell_formula(self, sheet_name, cell_ref):
        self.logger.debug("get_cell_formula called for sheet: %s, cell: %s", sheet_name, cell_ref)
        row_idx, col_idx = cell_to_coords(cell_ref) # These are 0-indexed
        if row_idx is None or col_idx is None:
            self.logger.debug("Invalid cell_ref: %s", cell_ref)
            return None

        if sheet_name not in self.formula_sheets:
            self.logger.debug("Sheet '%s' not found in self.formula_sheets.", sheet_name)
            return None
        
        config = self.sheet_configs.get(sheet_name, {'header_rows': 0, 'data_starts_at': 1})
        data_starts_at = config['data_starts_at']

        # Adjust row_idx for DataFrame indexing (data_starts_at is 1-indexed Excel row)
        df_row_idx = row_idx - (data_starts_at - 1)
        
        self.logger.debug(
            "Excel row_idx=%s, col_idx=%s -> DataFrame df_row_idx=%s",
            row_idx,
            col_idx,
            df_row_idx,
        )

        if df_row_idx < 0 or df_row_idx >= len(self.formula_sheets[sheet_name]):
            self.logger.debug("df_row_idx %s is out of bounds for sheet %s.", df_row_idx, sheet_name)
            return None # Or handle as an error

        formula = self.formula_sheets[sheet_name].iloc[df_row_idx, col_idx]
        self.logger.debug("Retrieved formula: %s", formula)
        return formula

    def execute_formula(self, formula_or_parsed, sheet_name, cell_ref):
        if (sheet_name, cell_ref) in self.call_stack:
            raise Exception(f"Circular reference detected: {self.call_stack + [(sheet_name, cell_ref)]}")
        self.call_stack.append((sheet_name, cell_ref))

        if (sheet_name, cell_ref) in self.memoization_cache:
            self.call_stack.pop()
            return self.memoization_cache[(sheet_name, cell_ref)]

        if isinstance(formula_or_parsed, dict):
            parsed_formula = formula_or_parsed
        elif isinstance(formula_or_parsed, str):
            parsed_formula = parse_formula(formula_or_parsed)
        else:
            # It's a literal value, not a formula string
            self.call_stack.pop()
            return formula_or_parsed

        if parsed_formula is None:
            self.call_stack.pop()
            return None

        strategy = self.strategy_map.get(parsed_formula['type'])

        if strategy:
            result = strategy.execute(self, parsed_formula, sheet_name, cell_ref)
        else:
            result = f"UNSUPPORTED[{parsed_formula['type']}]"

        self.memoization_cache[(sheet_name, cell_ref)] = result
        self.call_stack.pop()
        return result


    def get_sheet_names(self):
        """Returns a list of all sheet names in the workbook."""
        return list(self.sheets.keys())

    def get_data(self, sheet_name):
        """Returns the entire DataFrame for a given sheet."""
        return self.sheets.get(sheet_name)

    def get_formulas(self, sheet_name):
        """Returns the entire DataFrame of formulas for a given sheet."""
        if sheet_name not in self.formula_sheets:
            sheet_obj = self._workbook[sheet_name]
            # _load_raw_sheet_data returns (all_data_values, all_data_formulas)
            _, raw_data_formulas = self._load_raw_sheet_data(sheet_obj)
            self.formula_sheets[sheet_name] = self._process_raw_dataframe(raw_data_formulas, sheet_obj, sheet_name, data_only=False)
        return self.formula_sheets.get(sheet_name)

    def get_ground_truth(self, sheet_name: str | None = None):
        """
        Returns a DataFrame with the ground truth values from the original Excel file.
        """
        if sheet_name is None:
            sheet_name = self.default_sheet_names["detailed_table"]
        return self.sheets[sheet_name]

    def run_engine(self, sheet_name: str | None = None, fail_on_error: bool = True):
        """
        Runs the calculation engine on the specified sheet and returns a DataFrame with the results.
        If fail_on_error is False, it will log errors and continue.
        """
        if sheet_name is None:
            sheet_name = self.default_sheet_names["detailed_table"]
        formulas_df = self.get_formulas(sheet_name)
        if formulas_df is None:
            return None, []

        results_df = formulas_df.copy()
        errors = []
        for r_idx in range(formulas_df.shape[0]):
            for c_idx in range(formulas_df.shape[1]):
                formula = formulas_df.iloc[r_idx, c_idx]
                cell_ref = coords_to_cell(r_idx + self.sheet_configs.get(sheet_name, {'data_starts_at': 1})['data_starts_at'] - 1, c_idx)
                if isinstance(formula, str) and formula.startswith('='):
                    try:
                        result = self.execute_formula(formula, sheet_name, cell_ref)
                        results_df.iloc[r_idx, c_idx] = result
                    except Exception as e:
                        error_info = {
                            "cell": cell_ref,
                            "formula": formula,
                            "error": str(e),
                            "call_stack": self.call_stack,
                        }
                        errors.append(error_info)
                        results_df.iloc[r_idx, c_idx] = f"ERROR[{str(e)}]"
                        if fail_on_error:
                            raise
                else:
                    # For non-formula cells, we can just take the value from the original sheet
                    value = self.get_cell_value(sheet_name, cell_ref)
                    results_df.iloc[r_idx, c_idx] = value
        return results_df, errors

