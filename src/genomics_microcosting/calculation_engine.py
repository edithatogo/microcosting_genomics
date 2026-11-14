# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Evaluate workbook cost formulas through validated calculation strategies."""

import logging

import polars as pl
from pydantic import ValidationError as FormulaValidationError

from .component_contracts import (
    AggregationMetadata,
    ComplexityMetadata,
    ComponentMetadata,
    ConditionMetadata,
    FinancialMetadata,
    InputValidation,
    OperationMetadata,
    ReferenceMetadata,
    RequiredParameters,
)
from .error_handling import setup_standard_error_handling
from .formula_contracts import validate_formula_record
from .formula_parser import parse_formula
from .input_validation import InputValidator, ValidationError
from .logging_config import get_logger
from .strategies import (
    AdditionStrategy,
    AverageCellsStrategy,
    AverageRangeStrategy,
    CalculationStrategy,
    CellDivisionByNumberDivisionByNumberStrategy,
    CellDivisionByNumberMultiplicationByNumberStrategy,
    CellDivisionByNumberMultiplicationStrategy,
    CellDivisionByNumberStrategy,
    CellMultiplicationWithDivisionStrategy,
    ComplexMultiplicationDivisionStrategy,
    CrossSheetMultiplicationThreeStrategy,
    DivisionMultiplicationSequenceStrategy,
    DivisionParenthesesMultiplicationStrategy,
    DivisionStrategy,
    DivisionThreeValuesStrategy,
    IfErrorStrategy,
    IfStrategy,
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
    VLookupStrategy,
)
from .utils import cell_to_coords, coords_to_cell
lazy from .sheet_manager import SheetManager

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
        call_stack (list): Formula execution stack for detecting circular references.
        strategy_map (dict): Mapping of formula types to their corresponding strategies.

    """

    def __init__(
        self,
        sheet_manager: SheetManager,
        *,
        verbose: bool = False,
    ) -> None:
        """Initialize the CalculationEngine.

        Args:
            sheet_manager (SheetManager): The sheet manager instance for accessing data.
            verbose (bool, optional): Enable verbose logging. Defaults to False.

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
        self.memoization_cache: dict[tuple[str, str], object] = {}
        self.call_stack: list[tuple[str, str]] = []
        self.strategy_map: dict[str, CalculationStrategy] = {
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
            "cell_division_by_number_multiplication": (
                CellDivisionByNumberMultiplicationStrategy()
            ),
            "number_division_by_cell": NumberDivisionByCellStrategy(),
            "cell_division_by_number_multiplication_by_number": (
                CellDivisionByNumberMultiplicationByNumberStrategy()
            ),
            "cell_division_by_number_division_by_number": (
                CellDivisionByNumberDivisionByNumberStrategy()
            ),
            "average_range": AverageRangeStrategy(),
            "average_cells": AverageCellsStrategy(),
            "cross_sheet_multiplication_three": CrossSheetMultiplicationThreeStrategy(),
            "sum_range": SumRangeStrategy(),
            "sum_cells": SumCellsStrategy(),
            "multiplication_with_division": MultiplicationWithDivisionStrategy(),
            "pmt": PMTStrategy(),
            "number_division_multiplication": NumberDivisionMultiplicationStrategy(),
            "division_parentheses_multiplication": (
                DivisionParenthesesMultiplicationStrategy()
            ),
            "complex_multiplication_division": ComplexMultiplicationDivisionStrategy(),
            "parentheses_multiplication_division": (
                ParenthesesMultiplicationDivisionStrategy()
            ),
            "multiplication_with_nested_division": (
                CellMultiplicationWithDivisionStrategy()
            ),
            "complex_nested_expression": NestedArithmeticExpressionStrategy(),
            "division_multiplication_sequence": (
                DivisionMultiplicationSequenceStrategy()
            ),
            "if": IfStrategy(),
            "iferror": IfErrorStrategy(),
            "vlookup": VLookupStrategy(),
        }
        self.sheet_configs = sheet_manager.sheet_configs

        # Initialize error handling
        self.error_handler = setup_standard_error_handling(self.logger)

        # Initialize input validation
        self.validator = InputValidator(self.logger)

        # Allow the detailed table sheet name to be overridden by configuration
        configured_name = self.default_sheet_names["detailed_table"]
        if (configured_name != "Detailed Table") and (
            "Detailed Table" in self.sheet_configs
        ):
            self.sheet_configs[configured_name] = self.sheet_configs.pop(
                "Detailed Table",
            )

    def get_cost_components_by_type(
        self,
        component_type: str,
    ) -> list[ComponentMetadata]:
        """Get all cost components of a specific type.

        Args:
            component_type: Cost component type, such as arithmetic or reference.

        Returns:
            List of cost component instances of the specified type

        """
        components: list[ComponentMetadata] = []
        components.extend(
            strategy
            for strategy in self.strategy_map.values()
            if isinstance(strategy, ComponentMetadata)
            and strategy.get_component_type() == component_type
        )
        return components

    def validate_cost_component(
        self,
        formula_type: str,
        parsed_formula: dict[str, object],
    ) -> bool:
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
        if isinstance(strategy, InputValidation):
            return strategy.validate_inputs(parsed_formula)
        return True

    def get_cost_component_info(self, formula_type: str) -> dict[str, object] | None:
        """Get information about a cost component.

        Args:
            formula_type: The type of formula

        Returns:
            Dictionary with cost component information

        """
        if formula_type not in self.strategy_map:
            return None

        strategy = self.strategy_map[formula_type]
        info: dict[str, object] = {
            "name": getattr(strategy, "name", "Unknown"),
            "component_type": (
                strategy.get_component_type()
                if isinstance(strategy, ComponentMetadata)
                else "unknown"
            ),
        }
        if isinstance(strategy, OperationMetadata):
            info["operation_type"] = strategy.get_operation_type()
        if isinstance(strategy, ReferenceMetadata):
            info["reference_type"] = strategy.get_reference_type()
        if isinstance(strategy, AggregationMetadata):
            info["aggregation_type"] = strategy.get_aggregation_type()
        if isinstance(strategy, FinancialMetadata):
            info["financial_function"] = strategy.get_financial_function()
        if isinstance(strategy, RequiredParameters):
            info["required_parameters"] = strategy.get_required_parameters()
        if isinstance(strategy, ConditionMetadata):
            info["condition_type"] = strategy.get_condition_type()
        if isinstance(strategy, ComplexityMetadata):
            info["complexity_level"] = strategy.get_complexity_level()

        return info

    def get_cell_value(self, sheet_name: str, cell_ref: str) -> object:
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
            module="calculation_engine",
        )
        def _get_cell_value(sheet_name: str, cell_ref: str) -> object:
            # Validate inputs
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)

            row_idx, col_idx = cell_to_coords(cell_ref)
            if row_idx is None or col_idx is None:
                self.logger.debug("Invalid cell reference: %s", cell_ref)
                return None

            df = self.sheet_manager.get_data(sheet_name)
            if df is None:
                self.logger.warning(
                    "Sheet '%s' not found or could not be loaded",
                    sheet_name,
                )
                return None

            config = self.sheet_manager.sheet_configs.get(sheet_name)
            if not config:
                self.logger.warning(
                    "Configuration for sheet '%s' not found",
                    sheet_name,
                )
                return None

            data_starts_at = config.get("data_starts_at", 2)
            df_row_idx = row_idx - (data_starts_at - 1)

            if 0 <= df_row_idx < len(df) and 0 <= col_idx < len(df.columns):
                return df.item(df_row_idx, col_idx)
            self.logger.debug(
                "Cell %s out of bounds in sheet '%s'",
                cell_ref,
                sheet_name,
            )
            return None

        return _get_cell_value(sheet_name, cell_ref)

    def get_cell_formula(self, sheet_name: str, cell_ref: str) -> str | None:
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
            module="calculation_engine",
        )
        def _get_cell_formula(sheet_name: str, cell_ref: str) -> str | None:
            # Validate inputs
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)

            row_idx, col_idx = cell_to_coords(cell_ref)
            if row_idx is None or col_idx is None:
                self.logger.debug("Invalid cell reference: %s", cell_ref)
                return None

            df = self.sheet_manager.get_formulas(sheet_name)
            if df is None:
                self.logger.warning(
                    "Formula sheet '%s' not found or could not be loaded",
                    sheet_name,
                )
                return None

            config = self.sheet_manager.sheet_configs.get(sheet_name)
            if not config:
                self.logger.warning(
                    "Configuration for sheet '%s' not found",
                    sheet_name,
                )
                return None

            data_starts_at = config.get("data_starts_at", 2)
            df_row_idx = row_idx - (data_starts_at - 1)

            if 0 <= df_row_idx < len(df) and 0 <= col_idx < len(df.columns):
                formula = df.item(df_row_idx, col_idx)
                if isinstance(formula, str) and formula.startswith("="):
                    return formula
                return None
            self.logger.debug(
                "Cell %s out of bounds in formula sheet '%s'",
                cell_ref,
                sheet_name,
            )
            return None

        return _get_cell_formula(sheet_name, cell_ref)

    def execute_formula(
        self,
        formula_or_parsed: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Execute a formula and return the result.

        Memoize formula execution and detect circular references.

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
            self.logger.warning("Input validation failed: %s", e)
            return None

        # Validate both parser output and direct parsed records at the boundary.
        try:
            if isinstance(formula_or_parsed, str):
                parsed_formula = parse_formula(formula_or_parsed)
            else:
                parsed_formula = validate_formula_record(formula_or_parsed)
        except FormulaValidationError as error:
            self.logger.warning("Invalid parsed formula: %s", error)
            return None

        if parsed_formula is None:
            self.logger.warning("Failed to parse formula: %s", formula_or_parsed)
            return None

        # Check for circular references
        cache_key = (sheet_name, cell_ref)
        if cache_key in self.call_stack:
            self.logger.warning("Circular reference detected: %s", cache_key)
            return "#CIRCULAR_REF!"

        # Check memoization cache
        if cache_key in self.memoization_cache:
            return self.memoization_cache[cache_key]

        return self._execute_uncached(parsed_formula, formula_or_parsed, cache_key)

    def _execute_uncached(
        self,
        parsed_formula: dict[str, object],
        source: object,
        cache_key: tuple[str, str],
    ) -> object:
        sheet_name, cell_ref = cache_key
        self.call_stack.append(cache_key)

        try:
            # Get the appropriate strategy
            formula_type = parsed_formula.get("type")
            if (
                not isinstance(formula_type, str)
                or formula_type not in self.strategy_map
            ):
                self.logger.warning("Unknown formula type: %s", formula_type)
                return None

            strategy = self.strategy_map[formula_type]

            # Execute the formula using the strategy
            result = strategy.execute(self, parsed_formula, sheet_name, cell_ref)

            # Cache the result
            self.memoization_cache[cache_key] = result

        except Exception:
            self.logger.exception(
                "Error executing formula %s",
                source,
            )
            return None
        else:
            return result
        finally:
            # Remove from call stack
            if cache_key in self.call_stack:
                self.call_stack.remove(cache_key)

    def run_engine(
        self,
        sheet_name: str,
        *,
        fail_on_error: bool = True,
    ) -> tuple[pl.DataFrame | None, list[str]]:
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

        config = self.sheet_manager.sheet_configs.get(sheet_name, {})
        return self._evaluate_sheet(
            sheet_name,
            data_df,
            formula_df,
            config.get("data_starts_at", 2),
            fail_on_error=fail_on_error,
        )

    def _evaluate_sheet(
        self,
        sheet_name: str,
        data_df: pl.DataFrame,
        formula_df: pl.DataFrame,
        data_starts_at: int,
        *,
        fail_on_error: bool,
    ) -> tuple[pl.DataFrame, list[str]]:
        # Create a copy of the data to store results
        result_columns = [column.to_list() for column in data_df]
        errors: list[str] = []

        # Process each cell in the formula sheet
        for col_idx, column in enumerate(formula_df):
            for row_idx, formula in enumerate(column.to_list()):
                if isinstance(formula, str) and formula.startswith("="):
                    # Convert to cell reference
                    cell_ref = coords_to_cell(row_idx + data_starts_at - 1, col_idx)

                    try:
                        # Execute the formula
                        result = self.execute_formula(formula, sheet_name, cell_ref)

                        # Store the result in the results DataFrame
                        result_columns[col_idx][row_idx] = result

                    except Exception as e:
                        error_msg = f"Error in {cell_ref}: {e!s}"
                        self.logger.exception(error_msg)
                        errors.append(error_msg)

                        if fail_on_error:
                            raise

        return pl.DataFrame(
            [
                pl.Series(name, values, dtype=pl.Object)
                for name, values in zip(data_df.columns, result_columns, strict=True)
            ],
        ), errors
