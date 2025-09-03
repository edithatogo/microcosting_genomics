import logging


from .formula_parser import parse_formula
from .sheet_manager import SheetManager
from .strategies import (
    AdditionStrategy,
    DivisionStrategy,
    IfErrorStrategy,
    IfStrategy,
    LiteralStrategy,
    MultiplicationByNumberStrategy,
    MultiplicationStrategy,
    PmtStrategy,
    ReferenceStrategy,
    StringLiteralStrategy,
    SumCellsStrategy,
    SumRangeStrategy,
    UnknownStrategy,
    VLookupStrategy,
)
from .utils import cell_to_coords, coords_to_cell
from .logging_config import get_logger

logger = get_logger(__name__)


class CalculationEngine:
    """Main calculation engine for processing Excel formulas.

    This class provides the core functionality for parsing and executing Excel formulas
    with support for memoization and recursive formula execution. It uses a strategy
    pattern to handle different types of formulas and operations.

    Attributes:
        sheet_manager (SheetManager): Manager for accessing Excel sheet data.
        sheets (dict): Dictionary of loaded data sheets.
        formula_sheets (dict): Dictionary of loaded formula sheets.
        memoization_cache (dict): Cache for storing previously calculated results.
        call_stack (list): Stack for tracking formula execution to detect circular references.
        strategy_map (dict): Mapping of formula types to their corresponding strategies.
    """

    def __init__(
        self,
        sheet_manager: SheetManager,
        verbose: bool = False,
    ):
        """Initialize the CalculationEngine.

        Args:
            sheet_manager (SheetManager): The sheet manager instance for accessing data.
            verbose (bool, optional): Whether to enable verbose logging. Defaults to False.
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)

        self.sheet_manager = sheet_manager
        self.sheets = sheet_manager.sheets
        self.formula_sheets = sheet_manager.formula_sheets
        if not hasattr(self, "default_sheet_names"):
            self.default_sheet_names = {
                "detailed_table": "Detailed Table",
            }
        self.memoization_cache = {}
        self.call_stack = []
        self.strategy_map = {
            "literal": LiteralStrategy(),
            "string_literal": StringLiteralStrategy(),
            "reference": ReferenceStrategy(),
            "multiplication": MultiplicationStrategy(),
            "multiplication_by_number": MultiplicationByNumberStrategy(),
            "addition": AdditionStrategy(),
            "division": DivisionStrategy(),
            "sum_range": SumRangeStrategy(),
            "sum_cells": SumCellsStrategy(),
            "if": IfStrategy(),
            "iferror": IfErrorStrategy(),
            "vlookup": VLookupStrategy(),
            "pmt": PmtStrategy(),
            "unknown": UnknownStrategy(),
        }
        self.sheet_configs = sheet_manager.sheet_configs

        # Allow the detailed table sheet name to be overridden by configuration
        configured_name = self.default_sheet_names["detailed_table"]
        if configured_name != "Detailed Table":
            if "Detailed Table" in self.sheet_configs:
                self.sheet_configs[configured_name] = self.sheet_configs.pop(
                    "Detailed Table"
                )

    def get_cell_value(self, sheet_name, cell_ref):
        """Get the value of a cell from a sheet.

        Args:
            sheet_name (str): The name of the sheet to retrieve data from.
            cell_ref (str): The cell reference (e.g., "A1").

        Returns:
            The value of the cell, or None if the cell doesn't exist or is invalid.
        """
        try:
            row_idx, col_idx = cell_to_coords(cell_ref)
            if row_idx is None or col_idx is None:
                self.logger.debug(f"Invalid cell reference: {cell_ref}")
                return None

            df = self.sheet_manager.get_data(sheet_name)
            if df is None:
                self.logger.warning(
                    f"Sheet '{sheet_name}' not found or could not be loaded"
                )
                return None

            config = self.sheet_manager.sheet_configs.get(sheet_name)
            if not config:
                self.logger.warning(f"Configuration for sheet '{sheet_name}' not found")
                return None

            data_starts_at = config.get("data_starts_at", 2)
            df_row_idx = row_idx - (data_starts_at - 1)

            if 0 <= df_row_idx < len(df) and 0 <= col_idx < len(df.columns):
                return df.iloc[df_row_idx, col_idx]
            else:
                self.logger.debug(
                    f"Cell {cell_ref} out of bounds in sheet '{sheet_name}'"
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error getting cell value for {sheet_name}!{cell_ref}: {e}",
                exc_info=True
            )
            return None

    def get_cell_formula(self, sheet_name, cell_ref):
        """Get the formula of a cell from a sheet.

        Args:
            sheet_name (str): The name of the sheet to retrieve data from.
            cell_ref (str): The cell reference (e.g., "A1").

        Returns:
            The formula of the cell as a string (starting with "="), or None if
            the cell doesn't exist, is invalid, or doesn't contain a formula.
        """
        try:
            row_idx, col_idx = cell_to_coords(cell_ref)
            if row_idx is None or col_idx is None:
                self.logger.debug(f"Invalid cell reference: {cell_ref}")
                return None

            df = self.sheet_manager.get_formulas(sheet_name)
            if df is None:
                self.logger.warning(
                    f"Formula sheet '{sheet_name}' not found or could not be loaded"
                )
                return None

            config = self.sheet_manager.sheet_configs.get(sheet_name)
            if not config:
                self.logger.warning(f"Configuration for sheet '{sheet_name}' not found")
                return None

            data_starts_at = config.get("data_starts_at", 2)
            df_row_idx = row_idx - (data_starts_at - 1)

            if 0 <= df_row_idx < len(df) and 0 <= col_idx < len(df.columns):
                formula = df.iloc[df_row_idx, col_idx]
                if isinstance(formula, str) and formula.startswith("="):
                    return formula
                return None
            else:
                self.logger.debug(
                    f"Cell {cell_ref} out of bounds in formula sheet '{sheet_name}'"
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error getting cell formula for {sheet_name}!{cell_ref}: {e}",
                exc_info=True
            )
            return None

    def execute_formula(self, formula_or_parsed, sheet_name, cell_ref):
        """Execute a formula and return the result.

        This method handles formula execution with memoization to avoid redundant calculations
        and detects circular references to prevent infinite recursion.

        Args:
            formula_or_parsed (str or dict): Either a formula string (e.g., "=A1+B1")
                or a pre-parsed formula dictionary.
            sheet_name (str): The name of the sheet containing the formula.
            cell_ref (str): The cell reference (e.g., "A1").

        Returns:
            The result of the formula execution, or an error string if execution fails.
        """
        try:
            if (sheet_name, cell_ref) in self.call_stack:
                error_msg = f"Circular reference detected: {self.call_stack + [(sheet_name, cell_ref)]}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            self.call_stack.append((sheet_name, cell_ref))

            if (sheet_name, cell_ref) in self.memoization_cache:
                self.call_stack.pop()
                cached_result = self.memoization_cache[(sheet_name, cell_ref)]
                self.logger.debug(
                    f"Using cached result for {sheet_name}!{cell_ref}: {cached_result}"
                )
                return cached_result

            if isinstance(formula_or_parsed, dict):
                parsed_formula = formula_or_parsed
            elif isinstance(formula_or_parsed, str):
                try:
                    parsed_formula = parse_formula(formula_or_parsed)
                    self.logger.debug(
                        f"Parsed formula in {sheet_name}!{cell_ref}: {parsed_formula}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error parsing formula '{formula_or_parsed}' in {sheet_name}!{cell_ref}: {e}",
                        exc_info=True
                    )
                    self.call_stack.pop()
                    return f"PARSE_ERROR[{str(e)}]"
            else:
                self.call_stack.pop()
                return formula_or_parsed

            if parsed_formula is None:
                self.logger.debug(f"Formula parsed as None in {sheet_name}!{cell_ref}")
                self.call_stack.pop()
                return None

            strategy = self.strategy_map.get(parsed_formula["type"])

            if strategy:
                try:
                    result = strategy.execute(
                        self, parsed_formula, sheet_name, cell_ref
                    )
                    self.logger.debug(
                        f"Executed formula in {sheet_name}!{cell_ref} -> {result}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error executing strategy '{parsed_formula['type']}' in {sheet_name}!{cell_ref}: {e}",
                        exc_info=True
                    )
                    result = f"STRATEGY_ERROR[{str(e)}]"
            else:
                result = f"UNSUPPORTED[{parsed_formula['type']}]"

            self.memoization_cache[(sheet_name, cell_ref)] = result
            self.call_stack.pop()
            return result
        except Exception as e:
            self.logger.error(
                f"Unexpected error executing formula in {sheet_name}!{cell_ref}: {e}",
                exc_info=True
            )
            if self.call_stack:
                self.call_stack.pop()
            return f"EXECUTION_ERROR[{str(e)}]"

    def run_engine(self, sheet_name: str | None = None, fail_on_error: bool = True):
        """Run the calculation engine on the specified sheet.

        This method processes all formulas in the specified sheet and returns a DataFrame
        with the calculated results.

        Args:
            sheet_name (str, optional): The name of the sheet to process. If None,
                uses the default detailed table sheet.
            fail_on_error (bool, optional): Whether to raise an exception on error.
                If False, logs errors and continues. Defaults to True.

        Returns:
            tuple: A tuple containing:
                - pandas.DataFrame: DataFrame with calculated results
                - list: List of error dictionaries with details about any errors encountered
        """
        try:
            if sheet_name is None:
                sheet_name = self.sheet_manager.default_sheet_names["detailed_table"]
                self.logger.info(f"Using default sheet: {sheet_name}")
            else:
                self.logger.info(f"Processing sheet: {sheet_name}")

            formulas_df = self.sheet_manager.get_formulas(sheet_name)
            if formulas_df is None:
                self.logger.error(f"Could not load formulas for sheet '{sheet_name}'")
                return None, []

            self.logger.info(
                f"Processing {formulas_df.shape[0]} rows and {formulas_df.shape[1]} columns"
            )
            results_df = formulas_df.copy()
            errors = []

            processed_count = 0
            error_count = 0

            for r_idx in range(formulas_df.shape[0]):
                for c_idx in range(formulas_df.shape[1]):
                    formula = formulas_df.iloc[r_idx, c_idx]
                    cell_ref = coords_to_cell(
                        r_idx
                        + self.sheet_manager.sheet_configs.get(
                            sheet_name, {"data_starts_at": 1}
                        )["data_starts_at"]
                        - 1,
                        c_idx,
                    )
                    if isinstance(formula, str) and formula.startswith("="):
                        try:
                            result = self.execute_formula(formula, sheet_name, cell_ref)
                            results_df.iloc[r_idx, c_idx] = result
                            processed_count += 1

                            # Log progress every 1000 formulas
                            if processed_count % 1000 == 0:
                                self.logger.info(
                                    f"Processed {processed_count} formulas"
                                )
                        except Exception as e:
                            error_count += 1
                            error_info = {
                                "cell": cell_ref,
                                "formula": formula,
                                "error": str(e),
                                "call_stack": list(self.call_stack),  # Make a copy
                            }
                            errors.append(error_info)
                            results_df.iloc[r_idx, c_idx] = f"ERROR[{str(e)}]"
                            self.logger.error(f"Error in {sheet_name}!{cell_ref}: {e}",
                                            exc_info=True)
                            if fail_on_error:
                                self.logger.error(
                                    f"Stopping execution due to error in {sheet_name}!{cell_ref}"
                                )
                                raise
                    else:
                        value = self.get_cell_value(sheet_name, cell_ref)
                        results_df.iloc[r_idx, c_idx] = value

            self.logger.info(
                f"Engine run complete. Processed: {processed_count}, Errors: {error_count}"
            )
            return results_df, errors
        except Exception as e:
            self.logger.error(f"Error running engine for sheet '{sheet_name}': {e}",
                            exc_info=True)
            if fail_on_error:
                raise
            return None, [{"error": str(e)}]
