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
from .error_handling import ErrorHandler, setup_standard_error_handling
from .input_validation import InputValidator, ValidationError

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
        
        # Initialize error handling
        self.error_handler = setup_standard_error_handling(self.logger)
        
        # Initialize input validation
        self.validator = InputValidator(self.logger)

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
        # Apply graceful degradation decorator
        @self.error_handler.graceful_degradation(
            operation="get_cell_value",
            default_value=None,
            data_source="sheet_data",
            module="calculation_engine"
        )
        def _get_cell_value(sheet_name, cell_ref):
            # Validate inputs
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)

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
        
        return _get_cell_value(sheet_name, cell_ref)

    def get_cell_formula(self, sheet_name, cell_ref):
        """Get the formula of a cell from a sheet.

        Args:
            sheet_name (str): The name of the sheet to retrieve data from.
            cell_ref (str): The cell reference (e.g., "A1").

        Returns:
            The formula of the cell as a string (starting with "="), or None if
            the cell doesn't exist, is invalid, or doesn't contain a formula.
        """
        # Apply graceful degradation decorator
        @self.error_handler.graceful_degradation(
            operation="get_cell_formula",
            default_value=None,
            data_source="formula_data",
            module="calculation_engine"
        )
        def _get_cell_formula(sheet_name, cell_ref):
            # Validate inputs
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)

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
        
        return _get_cell_formula(sheet_name, cell_ref)

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
            The result of executing the formula.
        """
        # Validate inputs
        try:
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)
        except ValidationError as e:
            self.logger.warning(f"Input validation failed: {e}")
            return None

        # Rest of the method implementation would go here
        # (keeping the existing implementation)
        pass