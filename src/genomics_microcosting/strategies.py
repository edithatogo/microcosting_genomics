# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Evaluate the supported workbook formula strategies."""

import math
import re
from typing import TYPE_CHECKING, ClassVar

import numpy_financial as npf

if TYPE_CHECKING:
    from .calculation_engine import CalculationEngine

from . import strategy_contracts as contracts
from .cost_components import (
    ArithmeticCostComponent,
    FinancialCostComponent,
    ReferenceCostComponent,
)
from .formula_contracts import (
    FORMULA_RECORD,
    NUMERIC_LITERAL,
    REFERENCE_TARGET,
    STRING_LITERAL,
)
from .logging_config import get_logger
from .utils import cell_to_coords, coords_to_cell

logger = get_logger(__name__)


class CalculationStrategy:
    """Base class for a formula calculation strategy.

    This abstract base class defines the interface for all formula calculation
    strategies.
    Each strategy handles a specific type of Excel formula or operation.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: dict[str, object],
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        raise NotImplementedError


class LiteralStrategy(CalculationStrategy):
    """Strategy for handling numeric literals.

    This strategy handles simple numeric values in formulas, such as =3 or =1.5.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del engine, sheet_name, cell_ref
        return NUMERIC_LITERAL.validate_python(parsed_formula)["value"]


class StringLiteralStrategy(CalculationStrategy):
    """Strategy for handling string literals.

    This strategy handles string values in formulas, such as ="text".
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del engine, sheet_name, cell_ref
        return STRING_LITERAL.validate_python(parsed_formula)["value"]


class ReferenceStrategy(CalculationStrategy, ReferenceCostComponent):
    """Resolve validated cell references with consistent local-sheet defaults."""

    SHEET_NAME_MAPPING: ClassVar[dict[str, str]] = {
        "BI - Comp Stor Costs - VCGS": "BI - Comp+Stor Costs - VCGS",
    }

    def __init__(self) -> None:
        """Initialize the reference cost component."""
        ReferenceCostComponent.__init__(self, "Reference Strategy")

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the reference in the current worksheet context."""
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Resolve the same reference contract used by the component API."""
        del cell_ref
        return self.resolve_reference(engine, parsed_formula, sheet_name)

    def get_component_type(self) -> str:
        """Return the reference component category."""
        return "reference"

    def validate_inputs(self, parsed_formula: dict[str, object]) -> bool:
        """Report whether the legacy required cell field is present."""
        return "cell" in parsed_formula

    def get_reference_type(self) -> str:
        """Return the cell reference category."""
        return "cell"

    def resolve_reference(
        self,
        engine: CalculationEngine,
        reference: object,
        sheet_name: str,
    ) -> object:
        """Resolve absent/null qualifiers locally and preserve explicit sheets."""
        target = REFERENCE_TARGET.validate_python(reference)
        qualifier = target.get("sheet")
        referenced_sheet = sheet_name if qualifier is None else qualifier
        referenced_sheet = self.SHEET_NAME_MAPPING.get(
            referenced_sheet,
            referenced_sheet,
        )
        referenced_cell = target["cell"]
        formula = engine.get_cell_formula(referenced_sheet, referenced_cell)
        if formula and formula.startswith("="):
            return engine.execute_formula(formula, referenced_sheet, referenced_cell)
        value = engine.get_cell_value(referenced_sheet, referenced_cell)
        if value is None and engine.sheet_manager.is_blank_cell(
            referenced_sheet,
            referenced_cell,
        ):
            return 0
        return value


def _evaluate_operand(
    engine: CalculationEngine,
    operand: object,
    sheet_name: str,
    cell_ref: str,
    *,
    blank_as_zero: bool = False,
) -> object:
    """Evaluate a literal, reference or nested formula operand.

    This function evaluates a single operand in a formula, which can be either
    a literal value or a cell reference.

    Args:
        engine (CalculationEngine): The calculation engine instance.
        operand (dict or str): The operand to evaluate.
        sheet_name (str): The name of the current sheet.
        cell_ref (str): The current cell reference.
        blank_as_zero (bool): Treat an absent reference value as zero.

    Returns:
        The evaluated value of the operand.

    """
    if isinstance(operand, dict):
        operand = FORMULA_RECORD.validate_python(operand)
        if operand.get("type") == "literal":
            return operand["value"]
        if operand.get("type") == "reference":
            target = REFERENCE_TARGET.validate_python(operand)
            op_sheet = target.get("sheet") or sheet_name
            op_cell = target["cell"]
            formula = engine.get_cell_formula(op_sheet, op_cell)
            if formula and formula.startswith("="):
                return engine.execute_formula(formula, op_sheet, op_cell)
            value = engine.get_cell_value(op_sheet, op_cell)
            if (
                value is None
                and blank_as_zero
                and engine.sheet_manager.is_blank_cell(op_sheet, op_cell)
            ):
                return 0
            return value
    return engine.execute_formula(operand, sheet_name, cell_ref)


class AdditionStrategy(CalculationStrategy, ArithmeticCostComponent):
    """Strategy for handling addition formulas.

    This strategy handles addition operations, such as =A1+B1 or =1+2+3.
    It can handle multiple operands and will return None if any operand cannot be
    evaluated.
    """

    def __init__(self) -> None:
        """Initialize the cost component identity."""
        ArithmeticCostComponent.__init__(self, "Addition Strategy")

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Calculate the component value from validated operands."""
        parsed_formula = contracts.ADDITION_ARGUMENTS.validate_python(parsed_formula)
        total: int | float = 0
        for idx, operand in enumerate(parsed_formula["operands"]):
            value = _evaluate_operand(
                engine,
                operand,
                sheet_name,
                f"{cell_ref}_{idx}",
                blank_as_zero=True,
            )
            if isinstance(value, int | float) and not (
                isinstance(value, float) and math.isnan(value)
            ):
                total += value
            else:
                return None
        return total

    def get_component_type(self) -> str:
        """Return the component category."""
        return "arithmetic"

    def validate_inputs(self, parsed_formula: dict[str, object]) -> bool:
        """Check that required expression fields are present."""
        return "operands" in parsed_formula and isinstance(
            parsed_formula["operands"],
            list,
        )

    def get_operation_type(self) -> str:
        """Return the supported component contract."""
        return "addition"

    def get_operand_count(self) -> int:
        """Return the supported component contract."""
        return 0  # Variable number of operands


class MultiplicationStrategy(CalculationStrategy):
    """Strategy for handling multiplication formulas.

    This strategy handles multiplication operations, such as =A1*B1.
    It can handle multiple operands and will return None if any operand cannot be
    evaluated.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.ADDITION_ARGUMENTS.validate_python(parsed_formula)
        result: int | float = 1
        for idx, operand in enumerate(parsed_formula["operands"]):
            value = _evaluate_operand(
                engine,
                operand,
                sheet_name,
                f"{cell_ref}_{idx}",
                blank_as_zero=True,
            )
            if isinstance(value, int | float):
                result *= value
            else:
                return None
        return result


class MultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for handling multiplication by a number.

    This strategy handles multiplication of a cell reference by a number,
    such as =A1*3 or =2*B1.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.MULTIPLICATION_BY_NUMBER_ARGUMENTS.validate_python(
            parsed_formula,
        )
        cell_value = _evaluate_operand(
            engine,
            {
                "type": "reference",
                "sheet": parsed_formula["sheet"],
                "cell": parsed_formula["cell"],
            },
            sheet_name,
            f"{cell_ref}_0",
            blank_as_zero=True,
        )
        if isinstance(cell_value, int | float):
            return cell_value * parsed_formula["number"]
        return None


class SumRangeStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with a range.

    This strategy handles SUM operations over a range of cells, such as =SUM(A1:A10).
    It will sum all numeric values in the range and ignore non-numeric values.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.SUM_RANGE_ARGUMENTS.validate_python(parsed_formula)
        start_cell = parsed_formula["start_cell"]
        end_cell = parsed_formula["end_cell"]

        start_row, start_col = cell_to_coords(start_cell)
        end_row, end_col = cell_to_coords(end_cell)
        if start_row is None or start_col is None or end_row is None or end_col is None:
            return None

        total: int | float = 0
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = coords_to_cell(row, col)
                if cell == cell_ref:
                    continue

                formula = engine.get_cell_formula(sheet_name, cell)
                if formula:
                    value = engine.execute_formula(formula, sheet_name, cell)
                    if value is None:
                        return None
                else:
                    value = engine.get_cell_value(sheet_name, cell)

                if isinstance(value, int | float) and not (
                    isinstance(value, float) and math.isnan(value)
                ):
                    total += value
        return total


class SumCellsStrategy(CalculationStrategy):
    """Strategy for handling SUM formulas with individual cells.

    This strategy handles SUM operations with individual cell references,
    such as =SUM(A1,B1,C1).
    It will sum all numeric values and ignore non-numeric values.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.SUM_CELLS_ARGUMENTS.validate_python(parsed_formula)
        total: int | float = 0
        for cell_info in parsed_formula["cells"]:
            if isinstance(cell_info, str):
                try:
                    value = float(cell_info)
                    total += value
                    continue
                except ValueError:
                    if "!" in cell_info:
                        qualifier, cell = cell_info.rsplit("!", 1)
                        sheet = qualifier.strip("'").replace("''", "'")
                    else:
                        cell = cell_info
                        sheet = sheet_name
            else:
                cell = cell_info["cell"]
                sheet = cell_info.get("sheet") or sheet_name

            if ":" in cell:
                first, last = cell.split(":")
                range_value = SumRangeStrategy().execute(
                    engine,
                    {"start_cell": first, "end_cell": last},
                    sheet,
                    cell_ref,
                )
                if not isinstance(range_value, int | float):
                    return None
                total += range_value
                continue

            formula = engine.get_cell_formula(sheet, cell)
            if formula and formula.startswith("="):
                value = engine.execute_formula(formula, sheet, cell)
                if value is None:
                    return None
            else:
                value = engine.get_cell_value(sheet, cell)

            if isinstance(value, int | float) and not (
                isinstance(value, float) and math.isnan(value)
            ):
                total += value
        return total


class DivisionStrategy(CalculationStrategy):
    """Strategy for handling division formulas.

    This strategy handles division operations, such as =A1/B1.
    It will return None if any operand cannot be evaluated or if division by zero
    occurs.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.ADDITION_ARGUMENTS.validate_python(parsed_formula)
        result = _evaluate_operand(
            engine,
            parsed_formula["operands"][0],
            sheet_name,
            f"{cell_ref}_0",
            blank_as_zero=True,
        )
        if not isinstance(result, int | float):
            return None
        for idx, operand in enumerate(parsed_formula["operands"][1:]):
            value = _evaluate_operand(
                engine,
                operand,
                sheet_name,
                f"{cell_ref}_{idx + 1}",
                blank_as_zero=True,
            )
            if isinstance(value, int | float) and value != 0:
                result /= value
            else:
                return None
        return result


def _resolve_formula_or_cached_cell(
    engine: CalculationEngine,
    sheet_name: str,
    cell: str,
) -> int | float | None:
    """Resolve numeric arithmetic operands without using stale formula caches."""
    formula = engine.get_cell_formula(sheet_name, cell)
    value = (
        engine.execute_formula(formula, sheet_name, cell)
        if formula and formula.startswith("=")
        else engine.get_cell_value(sheet_name, cell)
    )
    return value if isinstance(value, int | float) else None


class SimpleDivisionStrategy(CalculationStrategy):
    """Strategy for handling simple division formulas.

    This strategy handles simple division operations, such as =D27/E27.
    It performs cell1 / cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = contracts.SIMPLE_DIVISION_ARGUMENTS.validate_python(
            parsed_formula,
        )
        cell1_value = _resolve_formula_or_cached_cell(
            engine,
            sheet_name,
            parsed_formula["cell1"],
        )
        cell2_value = _resolve_formula_or_cached_cell(
            engine,
            sheet_name,
            parsed_formula["cell2"],
        )

        if (
            isinstance(cell1_value, int | float)
            and isinstance(cell2_value, int | float)
            and cell2_value != 0
        ):
            return cell1_value / cell2_value
        return None


class NumberDivisionStrategy(CalculationStrategy):
    """Strategy for handling simple number division formulas.

    This strategy handles simple number division operations, such as =1/150.
    It performs number1 / number2 operation.
    Returns None if division by zero occurs.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del engine, sheet_name, cell_ref
        parsed_formula = contracts.NUMBER_DIVISION_ARGUMENTS.validate_python(
            parsed_formula,
        )
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]

        if number2 != 0:
            return number1 / number2
        return None


class DivisionParenthesesMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling division with parentheses and multiplication formulas.

    This strategy handles formulas like =(1/E44)*Q44.
    It performs (number/cell1) * cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = (
            contracts.DIVISION_PARENTHESES_MULTIPLICATION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        number = parsed_formula["number"]
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]

        # Get value from cell1
        cell1_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": None, "cell": cell1},
            sheet_name,
            f"{cell_ref}_cell1",
        )

        # Get value from cell2
        cell2_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": None, "cell": cell2},
            sheet_name,
            f"{cell_ref}_cell2",
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, int | float) or not isinstance(
            cell2_value,
            int | float,
        ):
            return None

        # Check for division by zero
        if cell1_value == 0:
            return None

        return (number / cell1_value) * cell2_value


class NumberDivisionMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling number division and multiplication formulas.

    This strategy handles formulas like =1/F44*P44.
    It performs (number/cell1) * cell2 operation.
    Returns None if any operand cannot be evaluated or if division by zero occurs.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = (
            contracts.DIVISION_PARENTHESES_MULTIPLICATION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        number = parsed_formula["number"]
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]

        # Get value from cell1
        cell1_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": None, "cell": cell1},
            sheet_name,
            f"{cell_ref}_cell1",
        )

        # Get value from cell2
        cell2_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": None, "cell": cell2},
            sheet_name,
            f"{cell_ref}_cell2",
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, int | float) or not isinstance(
            cell2_value,
            int | float,
        ):
            return None

        # Check for division by zero
        if cell1_value == 0:
            return None

        return (number / cell1_value) * cell2_value


class AverageRangeStrategy(CalculationStrategy):
    """Strategy for handling AVERAGE function with range notation.

    This strategy handles formulas like =AVERAGE(L44:N44).
    It calculates the average of all cells in the specified range.
    Returns None if any cell cannot be evaluated.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.SUM_RANGE_ARGUMENTS.validate_python(parsed_formula)
        start_cell = parsed_formula["start_cell"]
        end_cell = parsed_formula["end_cell"]

        # Parse cell references to get coordinates
        start_coords = cell_to_coords(start_cell)
        end_coords = cell_to_coords(end_cell)

        start_row, start_col = start_coords
        end_row, end_col = end_coords

        # Ensure we have valid integers
        if start_row is None or start_col is None or end_row is None or end_col is None:
            return None

        # Collect all values in the range
        values: list[int | float] = []
        for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
            for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
                cell_ref_name = coords_to_cell(row, col)
                value = _evaluate_operand(
                    engine,
                    {"type": "reference", "sheet": None, "cell": cell_ref_name},
                    sheet_name,
                    f"{cell_ref}_{cell_ref_name}",
                )
                if isinstance(value, int | float):
                    values.append(value)
                else:
                    return None  # Invalid value in range

        if not values:
            return None

        # Calculate average
        return sum(values) / len(values)


class AverageCellsStrategy(CalculationStrategy):
    """Strategy for handling AVERAGE function with individual cells.

    This strategy handles formulas like =AVERAGE(L44,N44).
    It calculates the average of the specified cells.
    Returns None if any cell cannot be evaluated.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.AVERAGE_CELLS_ARGUMENTS.validate_python(
            parsed_formula,
        )
        cells = parsed_formula["cells"]
        values: list[int | float] = []

        for i, cell in enumerate(cells):
            value = _evaluate_operand(
                engine,
                {"type": "reference", "sheet": None, "cell": cell},
                sheet_name,
                f"{cell_ref}_cell{i}",
            )
            if isinstance(value, int | float):
                values.append(value)
            else:
                return None  # Invalid value

        if not values:
            return None

        # Calculate average
        return sum(values) / len(values)


class CrossSheetMultiplicationThreeStrategy(CalculationStrategy):
    """Strategy for handling cross-sheet multiplication with three operands.

    This strategy handles formulas like ='Sheet1'!F102*'Sheet1'!I102*3.
    It performs (sheet1!cell1 * sheet2!cell2) * number.
    Returns None if any operand cannot be evaluated.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = (
            contracts.CROSS_SHEET_MULTIPLICATION_THREE_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        sheet1 = parsed_formula["sheet1"]
        cell1 = parsed_formula["cell1"]
        sheet2 = parsed_formula["sheet2"]
        cell2 = parsed_formula["cell2"]
        number = parsed_formula["number"]

        # Get value from sheet1!cell1
        cell1_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": sheet1, "cell": cell1},
            sheet_name,
            f"{cell_ref}_cell1",
        )

        # Get value from sheet2!cell2
        cell2_value = _evaluate_operand(
            engine,
            {"type": "reference", "sheet": sheet2, "cell": cell2},
            sheet_name,
            f"{cell_ref}_cell2",
        )

        # Check for valid numeric values
        if not isinstance(cell1_value, int | float) or not isinstance(
            cell2_value,
            int | float,
        ):
            return None

        return (cell1_value * cell2_value) * number


def _compare_scalars[T: (str, int | float)](left: T, right: T, operator: str) -> bool:
    """Compare values after narrowing both operands to a shared scalar domain."""
    if operator == ">":
        return left > right
    if operator == "<":
        return left < right
    if operator == ">=":
        return left >= right
    return left <= right


def _ordered_condition(left: object, right: object, operator: str) -> bool:
    """Compare numeric or text operands without mixing scalar domains."""
    if isinstance(left, int | float) and isinstance(right, int | float):
        return _compare_scalars(float(left), float(right), operator)
    if isinstance(left, str) and isinstance(right, str):
        return _compare_scalars(left, right, operator)
    return False


class IfStrategy(CalculationStrategy):
    """Strategy for handling IF formulas.

    This strategy handles IF conditional statements, such as =IF(A1>0, B1, C1).
    It evaluates the condition and returns the appropriate result based on the
    condition.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.IF_ARGUMENTS.validate_python(parsed_formula)
        condition = parsed_formula["condition"]
        match = re.match(r"(.+?)(<=|>=|<>|=|<|>)(.+)", condition)
        if match:
            left_expr, operator, right_expr = [s.strip() for s in match.groups()]

            left_val = engine.execute_formula(
                f"={left_expr}",
                sheet_name,
                f"{cell_ref}_L",
            )
            right_val = engine.execute_formula(
                f"={right_expr}",
                sheet_name,
                f"{cell_ref}_R",
            )

            cond_result = False
            if operator == "=":
                cond_result = left_val == right_val
            elif operator == "<>":
                cond_result = left_val != right_val
            elif (
                isinstance(left_val, int | float) and isinstance(right_val, int | float)
            ) or (isinstance(left_val, str) and isinstance(right_val, str)):
                cond_result = _ordered_condition(left_val, right_val, operator)
        else:
            # When the condition does not contain an explicit comparison, treat
            # it as a formula whose truthiness determines the branch.
            cond_val = engine.execute_formula(
                f"={condition}",
                sheet_name,
                f"{cell_ref}_COND",
            )
            cond_result = bool(cond_val)

        def _eval(val: object, suffix: str) -> object:
            if isinstance(val, dict):
                val = FORMULA_RECORD.validate_python(val)
                if val["type"] in ("literal", "string_literal"):
                    return val["value"]
                return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")
            return engine.execute_formula(val, sheet_name, f"{cell_ref}_{suffix}")

        if cond_result:
            return _eval(parsed_formula["true_val"], "T")
        return _eval(parsed_formula["false_val"], "F")


class IfErrorStrategy(CalculationStrategy):
    """Evaluate IfError workbook expressions."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.IF_ERROR_ARGUMENTS.validate_python(parsed_formula)
        value = parsed_formula["value"]
        if isinstance(value, dict):
            record = FORMULA_RECORD.validate_python(value)
            value = record
            if record.get("type") == "unknown":
                formula = record.get("formula", "")
                value = formula.lstrip("=") if isinstance(formula, str) else None
        try:
            value_result = engine.execute_formula(value, sheet_name, f"{cell_ref}_VAL")
        except ArithmeticError, ValueError, TypeError, KeyError:
            value_result = None
        if value_result is not None and not (
            isinstance(value_result, float) and math.isnan(value_result)
        ):
            return value_result
        fallback = parsed_formula["value_if_error"].strip()
        return engine.execute_formula(f"={fallback}", sheet_name, f"{cell_ref}_ERR")


def _pmt_token(
    engine: CalculationEngine,
    token: str,
    sheet_name: str,
    cell_ref: str,
    suffix: str,
) -> float:
    """Resolve a legacy PMT token with its original zero coercion semantics."""
    tok = token.strip()
    negative = False
    if tok.startswith("-"):
        negative = True
        tok = tok[1:].strip()

    # Check for percentage
    if tok.endswith("%"):
        try:
            val = float(tok.rstrip("%")) / 100
        except ValueError, TypeError:
            val = 0
    else:
        try:
            # Try to convert to float directly
            val = float(tok)
        except ValueError, TypeError:
            # If it fails, it might be a cell reference
            val = engine.execute_formula(
                f"={tok}",
                sheet_name,
                f"{cell_ref}_{suffix}",
            )

    number = _numeric_or_zero(val)
    return -number if negative else number


def _numeric_or_zero(value: object) -> float:
    """Preserve legacy PMT coercion for blank, text and NaN inputs."""
    if not isinstance(value, int | float | str):
        return 0.0
    try:
        number = float(value)
    except ValueError:
        return 0.0
    return 0.0 if math.isnan(number) else number


class PmtStrategy(CalculationStrategy):
    """Strategy for handling PMT formulas."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.PMT_ARGUMENTS.validate_python(parsed_formula)

        rate = _pmt_token(engine, parsed_formula["rate"], sheet_name, cell_ref, "RATE")
        nper = _pmt_token(engine, parsed_formula["nper"], sheet_name, cell_ref, "NPER")
        pv = _pmt_token(engine, parsed_formula["pv"], sheet_name, cell_ref, "PV")

        if nper == 0:
            return 0.0

        try:
            # npf.pmt can return NaN if inputs are invalid, handle this
            result = float(npf.pmt(rate, nper, pv))
            return float(result) if not math.isnan(result) else 0.0
        except ArithmeticError, ValueError, TypeError:
            return 0.0


def _lookup_table(
    engine: CalculationEngine,
    table_array: str,
    sheet_name: str,
) -> list[list[object]]:
    """Resolve every lookup table cell, including formula dependencies."""
    table_array = table_array.strip()
    if "!" in table_array:
        sheet_part, range_part = table_array.split("!", 1)
        table_sheet = sheet_part.strip().strip("'")
        table_range = range_part
    else:
        table_sheet = sheet_name
        table_range = table_array

    start_cell, end_cell = [c.replace("$", "") for c in table_range.split(":")]
    start_row, start_col = cell_to_coords(start_cell)
    end_row, end_col = cell_to_coords(end_cell)

    if start_row is None or start_col is None or end_row is None or end_col is None:
        return []
    table_data: list[list[object]] = []
    for r in range(start_row, end_row + 1):
        row_vals: list[object] = []
        for c in range(start_col, end_col + 1):
            cell = coords_to_cell(r, c)
            formula = engine.get_cell_formula(table_sheet, cell)
            if formula and formula.startswith("="):
                val = engine.execute_formula(formula, table_sheet, cell)
            else:
                val = engine.get_cell_value(table_sheet, cell)
            row_vals.append(val)
        table_data.append(row_vals)

    return table_data


def _lookup_match(
    table_data: list[list[object]],
    lookup_value: object,
    col_index: int,
    range_lookup: str,
) -> object:
    """Select an exact or ordered approximate lookup match."""
    col_index = col_index - 1
    if col_index < 0:
        return None
    range_lookup = range_lookup.strip().upper()

    if range_lookup == "FALSE":
        for row in table_data:
            if row and row[0] == lookup_value:
                return row[col_index] if col_index < len(row) else None
        return None
    last_match: list[object] | None = None
    for row in table_data:
        if row and row[0] is not None:
            key = row[0]
            if (
                isinstance(key, int | float) and isinstance(lookup_value, int | float)
            ) or (isinstance(key, str) and isinstance(lookup_value, str)):
                eligible = _ordered_condition(key, lookup_value, "<=")
            else:
                continue
            if eligible:
                last_match = row
            else:
                break
    if last_match:
        return last_match[col_index] if col_index < len(last_match) else None
    return None


class VLookupStrategy(CalculationStrategy):
    """Evaluate VLookup workbook expressions."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        parsed_formula = contracts.V_LOOKUP_ARGUMENTS.validate_python(parsed_formula)
        lookup_token = parsed_formula["lookup_value"].strip()
        if lookup_token.startswith('"') and lookup_token.endswith('"'):
            lookup_value = lookup_token.strip('"')
        else:
            try:
                lookup_value = float(lookup_token)
            except ValueError:
                lookup_value = engine.execute_formula(
                    f"={lookup_token}",
                    sheet_name,
                    f"{cell_ref}_lk",
                )

        table_data = _lookup_table(engine, parsed_formula["table_array"], sheet_name)
        return _lookup_match(
            table_data,
            lookup_value,
            int(parsed_formula["col_index_num"]),
            parsed_formula["range_lookup"],
        )


class NumberMultiplicationStrategy(CalculationStrategy):
    """Strategy for handling simple number multiplication: number*number."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del engine, sheet_name, cell_ref
        parsed_formula = contracts.NUMBER_DIVISION_ARGUMENTS.validate_python(
            parsed_formula,
        )
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]
        return number1 * number2


class CellDivisionByNumberStrategy(CalculationStrategy):
    """Strategy for handling cell division by number: cell/number."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = contracts.CELL_DIVISION_BY_NUMBER_ARGUMENTS.validate_python(
            parsed_formula,
        )
        cell = parsed_formula["cell"]
        number = parsed_formula["number"]

        # Get the cell value
        cell_value = _resolve_formula_or_cached_cell(engine, sheet_name, cell)
        if cell_value is None:
            return None

        # Perform division
        try:
            return cell_value / number
        except ZeroDivisionError, TypeError:
            return None


class ComplexMultiplicationDivisionStrategy(CalculationStrategy):
    """Strategy for handling complex multiplication with division patterns.

    - cell*cell/number*cell
    - (number*number)/(number)
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: dict[str, object],
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        # Check if this is the cell-based format: cell*cell/number*cell
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        if "cell1" in parsed_formula:
            cell1 = parsed_formula["cell1"]
            cell2 = parsed_formula["cell2"]
            number = parsed_formula["number"]
            cell3 = parsed_formula["cell3"]

            if not (
                isinstance(cell1, str)
                and isinstance(cell2, str)
                and isinstance(cell3, str)
                and isinstance(number, int | float)
            ):
                return None
            # Get cell values
            value1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
            value2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)
            value3 = _resolve_formula_or_cached_cell(engine, sheet_name, cell3)

            if value1 is None or value2 is None or value3 is None:
                return None

            return value1 * value2 / number * value3 if number != 0 else None

        # Check if this is the number-based format: (number*number)/(number)
        if "num1" in parsed_formula:
            num1 = parsed_formula["num1"]
            num2 = parsed_formula["num2"]
            divisor = parsed_formula["divisor"]

            if not (
                isinstance(num1, int | float)
                and isinstance(num2, int | float)
                and isinstance(divisor, int | float)
            ):
                return None
            return (num1 * num2) / divisor if divisor != 0 else None

        logger.error(
            "Unknown format for complex_multiplication_division: %s",
            parsed_formula,
        )
        return None


class CellDivisionByNumberMultiplicationStrategy(CalculationStrategy):
    """Strategy for cell division by number, multiplied by cell: cell/number*cell."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.DIVISION_PARENTHESES_MULTIPLICATION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        cell1 = parsed_formula["cell1"]
        number = parsed_formula["number"]
        cell2 = parsed_formula["cell2"]

        value1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
        value2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number * cell2
        try:
            return value1 / number * value2
        except ZeroDivisionError, TypeError:
            return None


class NumberDivisionByCellStrategy(CalculationStrategy):
    """Strategy for number divided by cell: number/cell."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = contracts.CELL_DIVISION_BY_NUMBER_ARGUMENTS.validate_python(
            parsed_formula,
        )
        number = parsed_formula["number"]
        cell = parsed_formula["cell"]

        value = _resolve_formula_or_cached_cell(engine, sheet_name, cell)

        if value is None:
            return None

        # Perform calculation: number / cell
        try:
            return number / value
        except ZeroDivisionError, TypeError:
            return None


class CellDivisionByNumberMultiplicationByNumberStrategy(CalculationStrategy):
    """Strategy for cell division by number, multiplied by cell and number.

    Evaluate cell/number*cell*number.
    """

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        contract = contracts.CELL_DIVISION_BY_NUMBER_MULTIPLICATION_BY_NUMBER_ARGUMENTS
        parsed_formula = contract.validate_python(parsed_formula)
        cell1 = parsed_formula["cell1"]
        number1 = parsed_formula["number1"]
        cell2 = parsed_formula["cell2"]
        number2 = parsed_formula["number2"]

        value1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
        value2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number1 * cell2 * number2
        try:
            return value1 / number1 * value2 * number2
        except ZeroDivisionError, TypeError:
            return None


class CellDivisionByNumberDivisionByNumberStrategy(CalculationStrategy):
    """Strategy for cell division by number, divided by number: cell/number/number."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        contract = contracts.CELL_DIVISION_BY_NUMBER_DIVISION_BY_NUMBER_ARGUMENTS
        parsed_formula = contract.validate_python(parsed_formula)
        cell = parsed_formula["cell"]
        number1 = parsed_formula["number1"]
        number2 = parsed_formula["number2"]

        value = _resolve_formula_or_cached_cell(engine, sheet_name, cell)

        if value is None:
            return None

        # Perform calculation: cell / number1 / number2
        try:
            return value / number1 / number2
        except ZeroDivisionError, TypeError:
            return None


class MultiplicationThreeValuesStrategy(CalculationStrategy):
    """Strategy for multiplication of three values: cell1*cell2*number."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.MULTIPLICATION_THREE_VALUES_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        operands = parsed_formula["operands"]
        number = parsed_formula["number"]

        # Get values for the two cells
        value1 = _resolve_formula_or_cached_cell(
            engine,
            sheet_name,
            operands[0]["cell"],
        )
        value2 = _resolve_formula_or_cached_cell(
            engine,
            sheet_name,
            operands[1]["cell"],
        )

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 * cell2 * number
        try:
            return value1 * value2 * number
        except TypeError, ValueError:
            return None


class DivisionThreeValuesStrategy(CalculationStrategy):
    """Strategy for division of three values: cell1/number/cell2."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.DIVISION_PARENTHESES_MULTIPLICATION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        cell1 = parsed_formula["cell1"]
        number = parsed_formula["number"]
        cell2 = parsed_formula["cell2"]

        # Get values for the two cells
        value1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
        value2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)

        if value1 is None or value2 is None:
            return None

        # Perform calculation: cell1 / number / cell2
        try:
            return value1 / number / value2
        except ZeroDivisionError, TypeError:
            return None


class MultiplicationWithDivisionStrategy(CalculationStrategy):
    """Strategy for handling patterns like =H58*(H57/H58)."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.MULTIPLICATION_WITH_DIVISION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]
        cell3 = parsed_formula["cell3"]

        # Get values
        value1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
        value2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)
        value3 = _resolve_formula_or_cached_cell(engine, sheet_name, cell3)

        if value1 is None or value2 is None or value3 is None or value3 == 0:
            return None  # Avoid division by zero

        # Perform calculation: cell1 * (cell2 / cell3)
        try:
            return value1 * (value2 / value3)
        except ZeroDivisionError, TypeError:
            return None


class PMTStrategy(CalculationStrategy, FinancialCostComponent):
    """Strategy for handling PMT function.

    This strategy handles Excel PMT function which calculates the payment for a loan
    based on constant payments and a constant interest rate.
    PMT(rate, nper, pv, fv, type)
    """

    def __init__(self) -> None:
        """Initialize the cost component identity."""
        FinancialCostComponent.__init__(self, "PMT Strategy")

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: dict[str, object],
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        return self.calculate(engine, parsed_formula, sheet_name, cell_ref)

    def calculate(
        self,
        engine: CalculationEngine,
        parsed_formula: dict[str, object],
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Calculate the component value from validated operands."""

        def argument(raw: object, argument_name: str) -> float | None:
            if isinstance(raw, int | float):
                return float(raw)
            if isinstance(raw, dict):
                value = _evaluate_operand(
                    engine,
                    FORMULA_RECORD.validate_python(raw),
                    sheet_name,
                    cell_ref,
                )
                return float(value) if isinstance(value, int | float) else None
            text = str(raw).strip()
            if text.endswith("%"):
                return float(text[:-1]) / 100
            try:
                return float(text)
            except ValueError:
                sign = -1 if text.startswith("-") else 1
                ref = text.lstrip("+-")
                value = engine.execute_formula(
                    f"={ref}",
                    sheet_name,
                    f"{cell_ref}_PMT{argument_name.upper()}",
                )
                return sign * float(value) if isinstance(value, int | float) else None

        values = [
            argument(parsed_formula.get(k, 0), k)
            for k in ("rate", "nper", "pv", "fv", "when")
        ]
        if any(x is None for x in values) or values[1] == 0:
            return None
        numeric = [value for value in values if value is not None]
        rate, nper, pv, fv, when = numeric
        if when not in (0, 1):
            return None
        return float(npf.pmt(rate, nper, pv, fv, int(when)))

    def get_component_type(self) -> str:
        """Return the component category."""
        return "financial"

    def validate_inputs(self, parsed_formula: dict[str, object]) -> bool:
        """Check that required expression fields are present."""
        required = ["rate", "nper", "pv"]
        return all(key in parsed_formula for key in required)

    def get_financial_function(self) -> str:
        """Return the supported financial function name."""
        return "pmt"

    def get_required_parameters(self) -> list[str]:
        """Return the required financial argument names."""
        return ["rate", "nper", "pv"]


class ParenthesesMultiplicationDivisionStrategy(CalculationStrategy):
    """Strategy for handling complex expressions like (30*52)/(4204600)."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del engine, sheet_name, cell_ref
        parsed_formula = (
            contracts.PARENTHESES_MULTIPLICATION_DIVISION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        divisor = parsed_formula["divisor"]

        if divisor == 0:
            return None

        return (num1 * num2) / divisor


class CellMultiplicationWithDivisionStrategy(CalculationStrategy):
    """Strategy for handling expressions like (H58*(H57/H58))."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.MULTIPLICATION_WITH_DIVISION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        cell1 = parsed_formula["cell1"]
        cell2 = parsed_formula["cell2"]
        cell3 = parsed_formula["cell3"]

        val1 = _resolve_formula_or_cached_cell(engine, sheet_name, cell1)
        val2 = _resolve_formula_or_cached_cell(engine, sheet_name, cell2)
        val3 = _resolve_formula_or_cached_cell(engine, sheet_name, cell3)

        if val1 is None or val2 is None or val3 is None or val3 == 0:
            return None

        return val1 * (val2 / val3)


class NestedArithmeticExpressionStrategy(CalculationStrategy):
    """Strategy for handling expressions like (2*(5/8*F4))."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.NESTED_ARITHMETIC_EXPRESSION_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        num3 = parsed_formula["num3"]
        cell = parsed_formula["cell"]

        val = _resolve_formula_or_cached_cell(engine, sheet_name, cell)

        if num3 == 0 or val is None:
            return None

        return num1 * (num2 / num3 * val)


class DivisionMultiplicationSequenceStrategy(CalculationStrategy):
    """Strategy for handling expressions like 365/3*D58."""

    def execute(
        self,
        engine: CalculationEngine,
        parsed_formula: object,
        sheet_name: str,
        cell_ref: str,
    ) -> object:
        """Evaluate the validated expression in its worksheet context."""
        del cell_ref
        parsed_formula = (
            contracts.DIVISION_MULTIPLICATION_SEQUENCE_ARGUMENTS.validate_python(
                parsed_formula,
            )
        )
        num1 = parsed_formula["num1"]
        num2 = parsed_formula["num2"]
        cell = parsed_formula["cell"]

        if num2 == 0:
            return None

        val = _resolve_formula_or_cached_cell(engine, sheet_name, cell)
        return None if val is None else (num1 / num2) * val
