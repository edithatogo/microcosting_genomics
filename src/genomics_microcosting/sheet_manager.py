# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Load workbook sheets and explicitly selected prepared tables."""

import logging
from pathlib import Path

import openpyxl
import polars as pl
lazy from openpyxl.worksheet.worksheet import Worksheet

from .config import SHEET_CONFIG_ADAPTER, SheetConfig, load_config
from .utils import cell_to_coords

logger = logging.getLogger(__name__)


class SheetManager:
    """Manages loading and accessing data from Excel sheets and Parquet files.

    This class handles loading data from Excel workbooks and prepared Parquet files,
    managing both data values and formula representations. It supports complex
    Excel features like merged cells and multi-level headers.

    Attributes:
        excel_file_path (Path): Path to the Excel file being loaded.
        prepared_data_path (Path): Directory containing prepared Parquet files.
        sheet_configs (dict): Configuration for each sheet including header information.
        sheets (dict): Dictionary of loaded data sheets as DataFrames.
        formula_sheets (dict): Dictionary of loaded formula sheets as DataFrames.

    """

    def __init__(
        self,
        excel_file_path: Path | str | None = None,
        *,
        verbose: bool = False,
        prepared_data_path: Path | str | None = None,
        sheet_configs: dict[str, SheetConfig] | None = None,
    ) -> None:
        """Initialize the SheetManager.

        Args:
            excel_file_path (Path | str | None, optional): Path to the Excel file.
                If None, load from configuration.
            verbose (bool, optional): Enable verbose logging; defaults to False.
            prepared_data_path (Path | str | None, optional): Prepared data directory.
                If None, uses default location. Defaults to None.
            sheet_configs (dict | None, optional): Sheet configuration dictionary.
                If None, uses default configuration. Defaults to None.

        """
        self.logger = logger.getChild(self.__class__.__name__)
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(levelname)s:%(name)s:%(message)s"),
            )
            self.logger.addHandler(handler)

        config = load_config()
        self.config = config
        use_prepared_tables = excel_file_path is None or prepared_data_path is not None

        if excel_file_path is None:
            workbook_key = config.get("default_workbook", "main")
            excel_file_path = (
                config.get("workbooks", {}).get(workbook_key, {}).get("path")
            )
            if excel_file_path is None:
                message = f"Workbook configuration '{workbook_key}' is missing its path"
                raise KeyError(message)

        if not Path(excel_file_path).exists():
            message = f"Selected Excel workbook does not exist: {excel_file_path}"
            raise FileNotFoundError(message)

        self.excel_file_path = Path(excel_file_path)

        if prepared_data_path is None:
            prepared_data_path = (
                Path(__file__).resolve().parents[1] / "data" / "prepared"
            )
        self.prepared_data_path = Path(prepared_data_path)
        self.use_prepared_tables = use_prepared_tables

        self.sheet_configs: dict[str, SheetConfig]
        if sheet_configs is None:
            # Load sheet configurations from the config file
            workbook_key = config.get("default_workbook", "validation")
            workbook_config = config.get("workbooks", {}).get(workbook_key, {})
            self.sheet_configs = workbook_config.get(
                "sheets",
                {
                    "Detailed Table": {
                        "header_rows": 4,
                        "data_starts_at": 5,
                        "string_columns": ["test", "category", "sub_category", "step"],
                    },
                    "Process": {"header_rows": 1, "data_starts_at": 2},
                    "DSA - Labour Prices": {"header_rows": 1, "data_starts_at": 2},
                    "DSA - Test Throughput": {"header_rows": 1, "data_starts_at": 2},
                    "Sheet1": {"header_rows": 1, "data_starts_at": 2},
                    "Sheet2": {"header_rows": 1, "data_starts_at": 2},
                    "Eq - Costs and Usage - VCGS": {
                        "header_rows": 1,
                        "data_starts_at": 2,
                    },
                },
            )
        else:
            self.sheet_configs = SHEET_CONFIG_ADAPTER.validate_python(sheet_configs)

        self.default_sheet_names = {
            "detailed_table": next(iter(self.sheet_configs.keys())),
        }
        self.sheets: dict[str, pl.DataFrame] = {}
        self.formula_sheets: dict[str, pl.DataFrame] = {}

        self._workbook = openpyxl.load_workbook(self.excel_file_path, data_only=False)
        # Unconfigured worksheets still supply cross-sheet formula references.
        for name in self._workbook.sheetnames:
            self.sheet_configs.setdefault(name, {"header_rows": 1, "data_starts_at": 2})
        self._load_all_sheets()

    def is_blank_cell(self, sheet_name: str, cell_ref: str) -> bool:
        """Identify an observed source blank without defaulting missing inputs."""
        if sheet_name not in self._workbook.sheetnames:
            return False
        row, column = cell_to_coords(cell_ref)
        if row is None or column is None:
            return False
        sheet = self._workbook[sheet_name]
        if not (0 <= row < sheet.max_row and 0 <= column < sheet.max_column):
            return False
        return sheet.cell(row + 1, column + 1).value is None

    def _load_all_sheets(self) -> None:
        """Load every configured sheet into ``self.sheets``.

        This method loads both data values and formulas for each configured sheet
        from the Excel workbook. It also loads prepared Parquet files if available.
        """
        self.logger.debug("Loading all sheets from %s", self.excel_file_path)

        workbook_values = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        try:
            for sheet_name in self.sheet_configs:
                if sheet_name not in self._workbook.sheetnames:
                    continue

                self.logger.debug("  Loading sheet: %s", sheet_name)

                sheet_obj_formulas = self._workbook[sheet_name]
                sheet_obj_values = workbook_values[sheet_name]

                raw_values, _ = self._load_raw_sheet_data(sheet_obj_values)
                _, raw_formulas = self._load_raw_sheet_data(sheet_obj_formulas)

                values_df = self._process_raw_dataframe(
                    raw_values,
                    sheet_name,
                )
                formulas_df = self._process_raw_dataframe(
                    raw_formulas,
                    sheet_name,
                )

                self.sheets[sheet_name] = values_df
                self.formula_sheets[sheet_name] = formulas_df
        finally:
            workbook_values.close()

        if self.use_prepared_tables:
            self._load_prepared_tables()

    def _load_prepared_tables(self) -> None:
        """Load pre-parsed parquet tables if available.

        This method loads prepared Parquet files that were previously generated
        from the Excel workbook. These files are used for faster loading and
        validation purposes.
        """
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
            if path.exists() and name not in self.sheets:
                self.logger.debug("Loading prepared table %s from %s", name, path)
                df = pl.read_parquet(path)
                self.sheets[name] = df
                self.formula_sheets[name] = df

    def _load_raw_sheet_data(
        self,
        sheet_obj: Worksheet,
    ) -> tuple[list[list[object]], list[list[object]]]:
        """Load the raw data from a sheet.

        This method loads raw data from an Excel sheet, handling merged cells
        by looking up the value from the top-left cell of each merged range.

        Args:
            sheet_obj: The openpyxl worksheet object to load data from.

        Returns:
            tuple: A tuple containing (data, formulas) where both are lists of lists
            representing the sheet data.

        """
        sheet_name = sheet_obj.title
        self.logger.debug("  _load_raw_sheet_data called for sheet: %s", sheet_name)

        ws = sheet_obj

        merged_lookup: dict[tuple[int, int], object] = {}
        for merged_range in ws.merged_cells.ranges:
            min_col, min_row, max_col, max_row = merged_range.bounds
            top_left_cell = ws.cell(row=min_row, column=min_col)
            val = top_left_cell.value
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    merged_lookup[(row, col)] = val

        data: list[list[object]] = []
        for row_idx, row in enumerate(ws.iter_rows(), start=1):
            row_data: list[object] = []
            for col_idx, cell in enumerate(row, start=1):
                if (row_idx, col_idx) in merged_lookup:
                    row_data.append(merged_lookup[(row_idx, col_idx)])
                else:
                    row_data.append(cell.value)
            data.append(row_data)

        return data, data

    def _create_unique_column_names(self, columns: list[str]) -> list[str]:
        """Ensure column names are unique by appending a suffix if required."""
        seen: dict[str, int] = {}
        unique_columns: list[str] = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                unique_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 1
                unique_columns.append(col)
        return unique_columns

    def _process_raw_dataframe(
        self,
        raw_data: list[list[object]],
        sheet_name: str,
    ) -> pl.DataFrame:
        """Normalize rows whose cached/formula mode was selected at workbook load."""
        config = self.sheet_configs[sheet_name]
        header_rows = config.get("header_rows", 1)
        data_starts_at = config.get("data_starts_at", header_rows + 1)

        width = max((len(row) for row in raw_data), default=0)
        names: list[str] = []
        for i in range(width):
            parts = dict.fromkeys(
                str(row[i]).strip()
                for row in raw_data[:header_rows]
                if row[i] is not None and str(row[i]).strip()
            )
            names.append(" ".join(parts) or f"unnamed_{i}")
        names = self._create_unique_column_names(names)
        rows = raw_data[data_starts_at - 1 :]
        columns: list[pl.Series] = []
        for i, name in enumerate(names):
            values = [row[i] for row in rows]
            # Excel allows formulas, numeric literals and text within one column.
            present = {type(v) for v in values if v is not None}
            if present and present <= {int, float}:
                series = pl.Series(name, values, dtype=pl.Float64)
            elif not present or present == {str}:
                series = pl.Series(name, values, dtype=pl.String)
            else:
                series = pl.Series(name, values, dtype=pl.Object)
            columns.append(series)
        return pl.DataFrame(columns)

    def get_sheet_names(self) -> list[str]:
        """Return a list of all sheet names in the workbook."""
        return list(self.sheets.keys())

    def close(self) -> None:
        """Release the underlying workbook's file resources."""
        self._workbook.close()

    def get_data(self, sheet_name: str) -> pl.DataFrame | None:
        """Return the entire DataFrame for a given sheet."""
        return self.sheets.get(sheet_name)

    def get_formulas(self, sheet_name: str) -> pl.DataFrame | None:
        """Return the entire DataFrame of formulas for a given sheet."""
        if sheet_name not in self.formula_sheets:
            sheet_obj = self._workbook[sheet_name]
            _, raw_data_formulas = self._load_raw_sheet_data(sheet_obj)
            self.formula_sheets[sheet_name] = self._process_raw_dataframe(
                raw_data_formulas,
                sheet_name,
            )
        return self.formula_sheets.get(sheet_name)

    def get_ground_truth(self, sheet_name: str | None = None) -> pl.DataFrame:
        """Return cached ground-truth values from the original workbook."""
        if sheet_name is None:
            sheet_name = self.default_sheet_names["detailed_table"]
        return self.sheets[sheet_name]
