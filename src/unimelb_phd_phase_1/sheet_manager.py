"""This module contains the SheetManager class."""

import logging
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

from .config import load_config

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetManager:
    """Manages loading and accessing data from Excel sheets and Parquet files."""

    def __init__(
        self,
        excel_file_path: Path | str | None = None,
        verbose: bool = False,
        prepared_data_path: Path | str | None = None,
        sheet_configs: dict | None = None,
    ):
        """Create a new SheetManager instance."""
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

        if sheet_configs is None:
            self.sheet_configs = {
                "Detailed Table": {
                    "header_rows": 4,
                    "data_starts_at": 5,
                    "string_columns": ["Test", "Category", "Sub-Category", "Step"],
                },
                "Process": {"header_rows": 1, "data_starts_at": 2},
                "DSA - Labour Prices": {"header_rows": 1, "data_starts_at": 2},
                "DSA - Test Throughput": {"header_rows": 1, "data_starts_at": 2},
                "Sheet1": {"header_rows": 1, "data_starts_at": 2},
                "Sheet2": {"header_rows": 1, "data_starts_at": 2},
                "Eq - Costs and Usage - VCGS": {"header_rows": 1, "data_starts_at": 2},
            }
        else:
            self.sheet_configs = sheet_configs

        self.default_sheet_names = {
            "detailed_table": next(iter(self.sheet_configs.keys()))
        }
        self.sheets = {}
        self.formula_sheets = {}

        self._workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)
        self._load_all_sheets()

    def _load_all_sheets(self):
        """Load every configured sheet into ``self.sheets``."""
        self.logger.debug("Loading all sheets from %s", self.excel_file_path)

        workbook_values = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        try:
            for sheet_name, sheet_config in self.sheet_configs.items():
                if sheet_name not in self._workbook.sheetnames:
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

        self._load_prepared_tables()

    def _load_prepared_tables(self):
        """Load pre-parsed parquet tables if available."""
        if not self.prepared_data_path.exists():
            return

        mapping = {
            "2. Labor Prices": self.prepared_data_path / "2._labor_prices.parquet",
            "3. Estimates": self.prepared_data_path / "3._estimates.parquet",
            "4. DSA - Equipment Throughput": self.prepared_data_path
            / "4._dsa_equipment_throughput.parquet",
            "5. DSA - Overheads": self.prepared_data_path / "5._dsa_overheads.parquet",
            "6. DSA - Consumable Discounts": self.prepared_data_path
            / "6._dsa_consumable_discounts.parquet",
            "7. DSA - Labor Prices": self.prepared_data_path
            / "7._dsa_labour_prices.parquet",
            "Summary Table": self.prepared_data_path / "summary_table.parquet",
            "Process": self.prepared_data_path / "process.parquet",
            "At a Glance": self.prepared_data_path / "at_a_glance.parquet",
            "PSA": self.prepared_data_path / "psa.parquet",
            "Eq - Costs and Usage - VCGS": self.prepared_data_path
            / "equipment_costs.parquet",
            "Cons -  Costs and Util - VCGS": self.prepared_data_path
            / "consumable_costs.parquet",
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

        merged_lookup = {}
        for merged_range in ws.merged_cells.ranges:
            min_row, min_col, max_row, max_col = merged_range.bounds
            top_left_cell = ws.cell(row=min_row, column=min_col)
            val = top_left_cell.value
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    merged_lookup[(row, col)] = val

        data = []
        for row_idx, row in enumerate(ws.iter_rows(), start=1):
            row_data = []
            for col_idx, cell in enumerate(row, start=1):
                if (row_idx, col_idx) in merged_lookup:
                    row_data.append(merged_lookup[(row_idx, col_idx)])
                else:
                    row_data.append(cell.value)
            data.append(row_data)

        return data, data

    def _process_raw_dataframe(self, raw_data, sheet_obj, sheet_name, data_only):
        config = self.sheet_configs[sheet_name]
        header_rows = config.get("header_rows", 1)
        data_starts_at = config.get("data_starts_at", header_rows + 1)

        df = pd.DataFrame(raw_data)

        if header_rows > 0:
            header_df = df.iloc[:header_rows].ffill(axis=0)
            if header_rows > 1:
                columns = pd.MultiIndex.from_frame(header_df.T)
            else:
                columns = pd.MultiIndex.from_arrays([header_df.iloc[0].tolist()])
        else:
            columns = df.columns

        df = df.iloc[data_starts_at - 1 :].reset_index(drop=True)
        df.columns = columns

        df.reset_index(drop=True, inplace=True)

        if data_only:
            string_columns = config.get("string_columns", [])

            def is_string_col(col):
                if isinstance(df.columns, pd.MultiIndex):
                    col_names = list(col) if isinstance(col, tuple) else [col]
                    return any(c in string_columns for c in col_names)
                return col in string_columns

            df = df.apply(
                lambda series: (
                    pd.to_numeric(series, errors="coerce")
                    if not is_string_col(series.name)
                    else series
                )
            )

        return df

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
