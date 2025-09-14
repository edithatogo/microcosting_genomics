"""This module contains the SheetManager class."""

import logging
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

from .config import load_config
from .type_specifications import get_type_spec, apply_type_conversions, validate_dataframe_types

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetManager:
    """Manages loading and accessing data from Excel sheets and Parquet files.

    This class handles loading data from Excel workbooks and prepared Parquet files,
    managing both data values and formula representations. It supports complex
    Excel features like merged cells and multi-level headers.

    Attributes:
        excel_file_path (Path): Path to the Excel file being loaded.
        prepared_data_path (Path): Path to the directory containing prepared Parquet files.
        sheet_configs (dict): Configuration for each sheet including header information.
        sheets (dict): Dictionary of loaded data sheets as DataFrames.
        formula_sheets (dict): Dictionary of loaded formula sheets as DataFrames.
    """

    def __init__(
        self,
        excel_file_path: Path | str | None = None,
        verbose: bool = False,
        prepared_data_path: Path | str | None = None,
        sheet_configs: dict | None = None,
    ):
        """Initialize the SheetManager.

        Args:
            excel_file_path (Path | str | None, optional): Path to the Excel file.
                If None, loads from configuration. Defaults to None.
            verbose (bool, optional): Whether to enable verbose logging. Defaults to False.
            prepared_data_path (Path | str | None, optional): Path to prepared data directory.
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
            # Load sheet configurations from the config file
            workbook_key = config.get("default_workbook", "validation")
            workbook_config = config.get("workbooks", {}).get(workbook_key, {})
            self.sheet_configs = workbook_config.get("sheets", {
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
                "Eq - Costs and Usage - VCGS": {"header_rows": 1, "data_starts_at": 2},
            })
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
        """Load every configured sheet into ``self.sheets``.

        This method loads both data values and formulas for each configured sheet
        from the Excel workbook. It also loads prepared Parquet files if available.
        """
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
            if path.exists():
                self.logger.debug("Loading prepared table %s from %s", name, path)
                df = pd.read_parquet(path)
                self.sheets[name] = df
                self.formula_sheets[name] = df

    def _load_raw_sheet_data(self, sheet_obj):
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

    def _create_unique_column_names(self, columns: list[str]) -> list[str]:
        """Ensure column names are unique by appending a suffix if required."""
        seen: dict[str, int] = {}
        unique_columns = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                unique_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 1
                unique_columns.append(col)
        return unique_columns

    def _process_raw_dataframe(self, raw_data, sheet_obj, sheet_name, data_only):
        config = self.sheet_configs[sheet_name]
        header_rows = config.get("header_rows", 1)
        data_starts_at = config.get("data_starts_at", header_rows + 1)

        df = pd.DataFrame(raw_data)

        if header_rows > 0:
            # Enhanced header processing with better multi-level header handling
            header_df = df.iloc[:header_rows].copy()
            header_df = header_df.ffill(axis=0)

            columns: list[str] = []
            for i in range(header_df.shape[1]):
                parts = []
                for row_idx in range(header_rows):
                    val = header_df.iloc[row_idx, i]
                    if pd.notna(val) and str(val).strip() not in ['None', 'nan', '']:
                        parts.append(str(val).strip())

                # Remove duplicates while preserving order
                seen = set()
                unique_parts = []
                for part in parts:
                    if part not in seen:
                        unique_parts.append(part)
                        seen.add(part)

                name = " ".join(unique_parts).replace("nan", "").strip()
                name = " ".join(name.split())  # Normalize whitespace

                if not name:
                    name = f"unnamed_{i}"
                columns.append(name)

            # Ensure column names are unique
            columns = self._create_unique_column_names(columns)
        else:
            columns = [f"col_{i}" for i in range(len(df.columns))]

        df = df.iloc[data_starts_at - 1 :].reset_index(drop=True)
        df.columns = columns

        df.reset_index(drop=True, inplace=True)

        if data_only:
            # Apply type specifications for data validation and conversion
            type_specs = {}
            column_mapping = config.get("column_mapping", {})

            # Build type specifications for mapped columns
            for _, standard_col in column_mapping.items():
                type_spec = get_type_spec(standard_col)
                if type_spec:
                    type_specs[standard_col] = type_spec

            # Apply type conversions if we have specifications
            if type_specs:
                try:
                    df = apply_type_conversions(df, type_specs)
                    # Validate types and log any issues
                    validation_errors = validate_dataframe_types(df, type_specs)
                    if validation_errors:
                        for error in validation_errors:
                            self.logger.warning("Type validation error in %s: %s", sheet_name, error)
                except Exception as e:
                    self.logger.error("Error applying type conversions for %s: %s", sheet_name, e)
                    # Fall back to basic numeric conversion for backward compatibility
                    string_columns = config.get("string_columns", [])

                    def is_string_col(col):
                        return col in string_columns

                    df = df.apply(
                        lambda series: (
                            pd.to_numeric(series, errors="coerce")
                            if not is_string_col(series.name)
                            else series
                        )
                    )
            else:
                # Fall back to legacy type conversion if no type specs available
                string_columns = config.get("string_columns", [])

                def is_string_col(col):
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
