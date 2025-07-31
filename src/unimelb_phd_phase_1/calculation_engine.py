import logging
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

from .config import load_config
from .formula_parser import parse_formula
from .strategies import (AdditionStrategy, DivisionThreeValuesStrategy,
                         IfErrorStrategy, IfStrategy, LiteralStrategy,
                         MultiplicationByNumberStrategy,
                         MultiplicationStrategy, PmtStrategy,
                         ReferenceStrategy, SumCellsStrategy, SumRangeStrategy,
                         VLookupStrategy)
from .utils import cell_to_coords, coords_to_cell

# The data tables contain thousands of columns which trigger Pandas warnings
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculationEngine:
    def __init__(
        self,
        excel_file_path: Path | str | None = None,
        verbose: bool = False,
        prepared_data_path: Path | str | None = None,
    ):
        """Create a new engine instance and load all configured sheets.

        Parameters
        ----------
        excel_file_path:
            Path to the Excel workbook.  If ``None`` the default workbook from
            the configuration is used.
        verbose:
            When ``True`` debug level logging is enabled.
        prepared_data_path:
            Directory containing prepared parquet tables.  These tables will
            overwrite any matching worksheets when :meth:`_load_all_sheets`
            completes.
        """
        self.logger = logger.getChild(self.__class__.__name__)
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(levelname)s:%(name)s:%(message)s")
            )
            self.logger.addHandler(handler)

        config = load_config()
        self.config = config

        if excel_file_path is None:
            workbook_key = config.get("default_workbook", "main")
            try:
                excel_file_path = config["workbooks"][workbook_key]["path"]
            except KeyError as e:
                raise KeyError(
                    f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}"
                ) from e

        # Fallback to the validation workbook if the configured file is missing
        if not Path(excel_file_path).exists():
            alt_path = config.get("workbooks", {}).get("validation", {}).get("path")
            if alt_path and Path(alt_path).exists():
                self.logger.warning(
                    "Excel file %s not found, falling back to %s",
                    excel_file_path,
                    alt_path,
                )
                excel_file_path = alt_path

        self.excel_file_path = Path(excel_file_path)

        if prepared_data_path is None:
            prepared_data_path = (
                Path(__file__).resolve().parents[1] / "data" / "prepared"
            )
        self.prepared_data_path = Path(prepared_data_path)

        workbook_config = config.get("workbooks", {}).get(
            config.get("default_workbook", "main"), {}
        )
        sheet_names = workbook_config.get("sheets", {})

        self.default_sheet_names = {
            "detailed_table": sheet_names.get("detailed_table", "Detailed Table")
        }
        self.sheets = {}
        self.formula_sheets = {}  # This will be populated on demand
        self.memoization_cache = {}
        self.call_stack = []
        self.strategy_map = {
            "literal": LiteralStrategy(),
            "reference": ReferenceStrategy(),
            "multiplication": MultiplicationStrategy(),
            "addition": AdditionStrategy(),
            "sum_range": SumRangeStrategy(),
            "sum_cells": SumCellsStrategy(),
            "multiplication_by_number": MultiplicationByNumberStrategy(),
            "division_three_values": DivisionThreeValuesStrategy(),
            "if": IfStrategy(),
            "iferror": IfErrorStrategy(),
            "vlookup": VLookupStrategy(),
            "pmt": PmtStrategy(),
            # More strategies will be added here
        }
        self.sheet_configs = {
            # The first four rows in the "Detailed Table" sheet form a complex
            # multi-level header.  Row five begins the actual data.  The
            # configuration below reflects that structure so that the loader
            # correctly builds a ``MultiIndex`` for the columns.
            "Detailed Table": {
                "header_rows": 4,
                "data_starts_at": 5,
                "string_columns": ["Test", "Category", "Sub-Category", "Step"],
            },
            "2. Labor Prices": {"header_rows": 1, "data_starts_at": 2},
            "3. Estimates": {"header_rows": 1, "data_starts_at": 2},
            "4. DSA - Equipment Throughput": {"header_rows": 1, "data_starts_at": 2},
            "5. DSA - Overheads": {"header_rows": 1, "data_starts_at": 2},
            "6. DSA - Consumable Discounts": {"header_rows": 1, "data_starts_at": 2},
            "7. DSA - Labor Prices": {"header_rows": 1, "data_starts_at": 2},
            "8. PSA": {"header_rows": 1, "data_starts_at": 2},
            "Process": {"header_rows": 1, "data_starts_at": 2},
            "Sheet1": {"header_rows": 1, "data_starts_at": 2},
            "Sheet2": {"header_rows": 1, "data_starts_at": 2},
            "Summary Table": {"header_rows": 1, "data_starts_at": 2},
            "At a Glance": {"header_rows": 1, "data_starts_at": 2},
            "Labour - Usage - VCGS": {"header_rows": 1, "data_starts_at": 2},
            "Cons -  Costs and Util - VCGS": {"header_rows": 1, "data_starts_at": 2},
            "Eq - Costs and Usage - VCGS": {"header_rows": 1, "data_starts_at": 2},
            "Labour - Costs - VCGS": {"header_rows": 1, "data_starts_at": 2},
        }

        # Allow the detailed table sheet name to be overridden by configuration
        configured_name = self.default_sheet_names["detailed_table"]
        if configured_name != "Detailed Table":
            if "Detailed Table" in self.sheet_configs:
                self.sheet_configs[configured_name] = self.sheet_configs.pop(
                    "Detailed Table"
                )

        # Load workbook once with data_only=False to access formulas and merged cells
        self._workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)

        # Populate ``self.sheets`` and ``self.formula_sheets``
        self._load_all_sheets()

    def _load_all_sheets(self):
        """Load every configured sheet into ``self.sheets``.

        This reads each worksheet twice via :meth:`_load_raw_sheet_data`, once
        to capture the numeric values and again to retain formulas. The
        resulting DataFrames are stored in ``self.sheets`` and
        ``self.formula_sheets``.  Prepared parquet tables are loaded last to
        override any matching sheets.
        """
        self.logger.debug("Loading all sheets from %s", self.excel_file_path)

        workbook_values = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        try:
            for sheet_name in self._workbook.sheetnames:
                if sheet_name not in self.sheet_configs:
                    continue

                self.logger.debug("  Loading sheet: %s", sheet_name)

                sheet_obj_formulas = self._workbook[sheet_name]
                sheet_obj_values = workbook_values[sheet_name]

                raw_values, _ = self._load_raw_sheet_data(sheet_obj_values)
                _, raw_formulas = self._load_raw_sheet_data(sheet_obj_formulas)

                values_df = self._process_raw_dataframe(
                    raw_values, sheet_obj_values, sheet_name, data_only=True
                )
                formulas_df = self._process_raw_dataframe(
                    raw_formulas, sheet_obj_formulas, sheet_name, data_only=False
                )

                self.sheets[sheet_name] = values_df
                self.formula_sheets[sheet_name] = formulas_df
        finally:
            workbook_values.close()

        # Replace with any available prepared parquet tables
        self._load_prepared_tables()

    def _load_prepared_tables(self):
        """Load pre-parsed parquet tables if available."""
        if not self.prepared_data_path.exists():
            return

        mapping = {
            "2. Labor Prices": self.prepared_data_path / "2._labor_prices.parquet",
            "3. Estimates": self.prepared_data_path / "3._estimates.parquet",
            "4. DSA - Equipment Throughput": self.prepared_data_path / "4._dsa_equipment_throughput.parquet",
            "5. DSA - Overheads": self.prepared_data_path / "5._dsa_overheads.parquet",
            "6. DSA - Consumable Discounts": self.prepared_data_path / "6._dsa_consumable_discounts.parquet",
            "7. DSA - Labor Prices": self.prepared_data_path / "7._dsa_labour_prices.parquet",
            "Summary Table": self.prepared_data_path / "summary_table.parquet",
            "Process": self.prepared_data_path / "process.parquet",
            "At a Glance": self.prepared_data_path / "at_a_glance.parquet",
            "PSA": self.prepared_data_path / "psa.parquet",
            "Eq - Costs and Usage - VCGS": self.prepared_data_path / "equipment_costs.parquet",
            "Cons -  Costs and Util - VCGS": self.prepared_data_path / "consumable_costs.parquet",
            "Labour - Costs - VCGS": self.prepared_data_path / "labour_costs.parquet",
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
        self.logger.debug("  _load_raw_sheet_data called for sheet: %s", sheet_name)

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
        config = self.sheet_configs[sheet_name]
        header_rows = config.get("header_rows", 1)

        df = pd.DataFrame(raw_data)

        if header_rows > 1:
            header = df.iloc[0:header_rows]
            if not header.empty:
                header = header.T.ffill().T
                df.columns = pd.MultiIndex.from_frame(header.T)
            df = df.iloc[header_rows:]
        elif header_rows == 1:
            df.columns = df.iloc[0]
            df = df.iloc[1:]

        df.reset_index(drop=True, inplace=True)

        if data_only:
            string_columns = config.get("string_columns", [])

            def is_string_col(col):
                if isinstance(df.columns, pd.MultiIndex):
                    col_names = list(col) if isinstance(col, tuple) else [col]
                    return any(c in string_columns for c in col_names)
                return col in string_columns

            for col in df.columns:
                if not is_string_col(col):
                    df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_cell_value(self, sheet_name, cell_ref):
        row_idx, col_idx = cell_to_coords(cell_ref)
        if row_idx is None or col_idx is None:
            return None
        if sheet_name not in self.sheets:
            return None

        df = self.sheets[sheet_name]
        config = self.sheet_configs.get(sheet_name)
        if not config:
            return None

        data_starts_at = config.get("data_starts_at", 2)
        df_row_idx = row_idx - data_starts_at

        if 0 <= df_row_idx < len(df):
            return df.iloc[df_row_idx, col_idx]
        return None

    def get_cell_formula(self, sheet_name, cell_ref):
        row_idx, col_idx = cell_to_coords(cell_ref)
        if row_idx is None or col_idx is None:
            return None
        if sheet_name not in self.formula_sheets:
            return None
        df = self.formula_sheets[sheet_name]
        config = self.sheet_configs.get(sheet_name)
        if not config:
            return None

        data_starts_at = config.get("data_starts_at", 2)
        df_row_idx = row_idx - data_starts_at

        if 0 <= df_row_idx < len(df):
            return df.iloc[df_row_idx, col_idx]
        return None

    def execute_formula(self, formula_or_parsed, sheet_name, cell_ref):
        if (sheet_name, cell_ref) in self.call_stack:
            raise Exception(
                f"Circular reference detected: {self.call_stack + [(sheet_name, cell_ref)]}"
            )
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

        strategy = self.strategy_map.get(parsed_formula["type"])

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
            self.formula_sheets[sheet_name] = self._process_raw_dataframe(
                raw_data_formulas, sheet_obj, sheet_name, data_only=False
            )
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
                cell_ref = coords_to_cell(
                    r_idx
                    + self.sheet_configs.get(sheet_name, {"data_starts_at": 1})[
                        "data_starts_at"
                    ]
                    - 1,
                    c_idx,
                )
                if isinstance(formula, str) and formula.startswith("="):
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
[end of file]
