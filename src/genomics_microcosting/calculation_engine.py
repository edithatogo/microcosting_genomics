import logging


from .formula_parser import parse_formula
from .sheet_manager import SheetManager
from .strategies import (
    AdditionStrategy,
    AverageCellsStrategy,
    AverageRangeStrategy,
    CellDivisionByNumberMultiplicationByNumberStrategy,
    CellDivisionByNumberMultiplicationStrategy,
    CellDivisionByNumberStrategy,
    CellDivisionByNumberDivisionByNumberStrategy,
    CellMultiplicationWithDivisionStrategy,
    ComplexMultiplicationDivisionStrategy,
    CrossSheetMultiplicationThreeStrategy,
    DivisionMultiplicationSequenceStrategy,
    DivisionParenthesesMultiplicationStrategy,
    DivisionThreeValuesStrategy,
    DivisionStrategy,
    LiteralStrategy,
    MultiplicationByNumberStrategy,
    MultiplicationStrategy,
    MultiplicationThreeValuesStrategy,
    MultiplicationWithDivisionStrategy,
    NestedArithmeticExpressionStrategy,
    NumberDivisionByCellStrategy,
    NumberDivisionMultiplicationStrategy,
    NumberDivisionStrategy,
    NumberMultiplicationStrategy,
    ParenthesesMultiplicationDivisionStrategy,
    PMTStrategy,
    ReferenceStrategy,
    SimpleDivisionStrategy,
    StringLiteralStrategy,
    SumCellsStrategy,
    SumRangeStrategy,
)
from .utils import cell_to_coords, coords_to_cell
from .logging_config import get_logger
from .error_handling import setup_standard_error_handling
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
            "multiplication_three_values": MultiplicationThreeValuesStrategy(),
            "multiplication_by_number": MultiplicationByNumberStrategy(),
            "addition": AdditionStrategy(),
            "division": DivisionStrategy(),
            "simple_division": SimpleDivisionStrategy(),
            "division_three_values": DivisionThreeValuesStrategy(),
            "number_multiplication": NumberMultiplicationStrategy(),
            "number_division": NumberDivisionStrategy(),
            "cell_division_by_number": CellDivisionByNumberStrategy(),
            "cell_division_by_number_multiplication": CellDivisionByNumberMultiplicationStrategy(),
            "number_division_by_cell": NumberDivisionByCellStrategy(),
            "cell_division_by_number_multiplication_by_number": CellDivisionByNumberMultiplicationByNumberStrategy(),
            "cell_division_by_number_division_by_number": CellDivisionByNumberDivisionByNumberStrategy(),
            "average_range": AverageRangeStrategy(),
            "average_cells": AverageCellsStrategy(),
            "cross_sheet_multiplication_three": CrossSheetMultiplicationThreeStrategy(),
            "sum_range": SumRangeStrategy(),
            "sum_cells": SumCellsStrategy(),
            "multiplication_with_division": MultiplicationWithDivisionStrategy(),
            "pmt": PMTStrategy(),
            "number_division_multiplication": NumberDivisionMultiplicationStrategy(),
            "division_parentheses_multiplication": DivisionParenthesesMultiplicationStrategy(),
            "complex_multiplication_division": ComplexMultiplicationDivisionStrategy(),
            "parentheses_multiplication_division": ParenthesesMultiplicationDivisionStrategy(),
            "multiplication_with_nested_division": CellMultiplicationWithDivisionStrategy(),
            "complex_nested_expression": NestedArithmeticExpressionStrategy(),
            "division_multiplication_sequence": DivisionMultiplicationSequenceStrategy(),
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

    def get_cost_components_by_type(self, component_type: str):
        """Get all cost components of a specific type.

        Args:
            component_type: The type of cost component to retrieve (e.g., 'arithmetic', 'reference')

        Returns:
            List of cost component instances of the specified type
        """
        components = []
        for strategy in self.strategy_map.values():
            if hasattr(strategy, 'get_component_type') and strategy.get_component_type() == component_type:
                components.append(strategy)
        return components

    def validate_cost_component(self, formula_type: str, parsed_formula: dict) -> bool:
        """Validate a parsed formula against its cost component requirements.

        Args:
            formula_type: The type of formula
            parsed_formula: The parsed formula data

        Returns:
            True if the formula is valid for its cost component, False otherwise
        """
        if formula_type not in self.strategy_map:
            return False

        strategy = self.strategy_map[formula_type]
        if hasattr(strategy, 'validate_inputs'):
            return strategy.validate_inputs(parsed_formula)
        return True

    def get_cost_component_info(self, formula_type: str):
        """Get information about a cost component.

        Args:
            formula_type: The type of formula

        Returns:
            Dictionary with cost component information
        """
        if formula_type not in self.strategy_map:
            return None

        strategy = self.strategy_map[formula_type]
        info = {
            'name': getattr(strategy, 'name', 'Unknown'),
            'component_type': getattr(strategy, 'get_component_type', lambda: 'unknown')(),
        }

        # Add type-specific information
        if hasattr(strategy, 'get_operation_type'):
            info['operation_type'] = strategy.get_operation_type()
        if hasattr(strategy, 'get_reference_type'):
            info['reference_type'] = strategy.get_reference_type()
        if hasattr(strategy, 'get_aggregation_type'):
            info['aggregation_type'] = strategy.get_aggregation_type()
        if hasattr(strategy, 'get_financial_function'):
            info['financial_function'] = strategy.get_financial_function()
        if hasattr(strategy, 'get_required_parameters'):
            info['required_parameters'] = strategy.get_required_parameters()
        if hasattr(strategy, 'get_condition_type'):
            info['condition_type'] = strategy.get_condition_type()
        if hasattr(strategy, 'get_complexity_level'):
            info['complexity_level'] = strategy.get_complexity_level()

        return info

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

        # Parse formula if it's a string
        if isinstance(formula_or_parsed, str):
            parsed_formula = parse_formula(formula_or_parsed)
        else:
            parsed_formula = formula_or_parsed

        if parsed_formula is None:
            self.logger.warning(f"Failed to parse formula: {formula_or_parsed}")
            return None

        # Check for circular references
        cache_key = (sheet_name, cell_ref)
        if cache_key in self.call_stack:
            self.logger.warning(f"Circular reference detected: {cache_key}")
            return "#CIRCULAR_REF!"

        # Check memoization cache
        if cache_key in self.memoization_cache:
            return self.memoization_cache[cache_key]

        # Add to call stack
        self.call_stack.append(cache_key)

        try:
            # Get the appropriate strategy
            formula_type = parsed_formula.get("type")
            if formula_type not in self.strategy_map:
                self.logger.warning(f"Unknown formula type: {formula_type}")
                return None

            strategy = self.strategy_map[formula_type]

            # Execute the formula using the strategy
            result = strategy.execute(self, parsed_formula, sheet_name, cell_ref)

            # Cache the result
            self.memoization_cache[cache_key] = result

            return result

        except Exception as e:
            self.logger.error(f"Error executing formula {formula_or_parsed}: {e}")
            return None
        finally:
            # Remove from call stack
            if cache_key in self.call_stack:
                self.call_stack.remove(cache_key)

    def run_engine(self, sheet_name, fail_on_error=True):
        """Execute all formulas in a sheet and return results.

        Args:
            sheet_name (str): The name of the sheet to process.
            fail_on_error (bool): Whether to raise exceptions on errors or collect them.

        Returns:
            tuple: (results_df, errors_list) where results_df contains calculated values
                   and errors_list contains any errors encountered.
        """
        # Validate inputs
        try:
            self.validator.validate_sheet_name(sheet_name)
        except ValidationError as e:
            if fail_on_error:
                raise
            return None, [str(e)]

        # Get the data and formula sheets
        data_df = self.sheet_manager.get_data(sheet_name)
        formula_df = self.sheet_manager.get_formulas(sheet_name)

        if data_df is None:
            error_msg = f"Data sheet '{sheet_name}' not found"
            if fail_on_error:
                raise ValueError(error_msg)
            return None, [error_msg]

        if formula_df is None:
            error_msg = f"Formula sheet '{sheet_name}' not found"
            if fail_on_error:
                raise ValueError(error_msg)
            return None, [error_msg]

        # Create a copy of the data to store results
        results_df = data_df.copy()
        errors = []

        # Get configuration for this sheet
        config = self.sheet_manager.sheet_configs.get(sheet_name, {})
        data_starts_at = config.get("data_starts_at", 2)

        # Process each cell in the formula sheet
        for row_idx in range(len(formula_df)):
            for col_idx in range(len(formula_df.columns)):
                formula = formula_df.iloc[row_idx, col_idx]

                if isinstance(formula, str) and formula.startswith("="):
                    # Convert to cell reference
                    cell_ref = coords_to_cell(row_idx + data_starts_at, col_idx)

                    try:
                        # Execute the formula
                        result = self.execute_formula(formula, sheet_name, cell_ref)

                        # Store the result in the results DataFrame
                        if 0 <= row_idx < len(results_df) and 0 <= col_idx < len(results_df.columns):
                            results_df.iloc[row_idx, col_idx] = result

                    except Exception as e:
                        error_msg = f"Error in {cell_ref}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)

                        if fail_on_error:
                            raise

        return results_df, errors