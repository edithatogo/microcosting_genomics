# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Strict typed records for the existing formula-strategy input shapes."""

from typing import TypedDict

from pydantic import ConfigDict, TypeAdapter, with_config

lazy from .formula_contracts import ReferenceTarget


@with_config(ConfigDict(strict=True, extra="allow"))
class AdditionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    operands: list[dict[str, object]]


ADDITION_ARGUMENTS = TypeAdapter(AdditionArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class MultiplicationByNumberArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell: str
    number: int | float
    sheet: str | None


MULTIPLICATION_BY_NUMBER_ARGUMENTS = TypeAdapter(MultiplicationByNumberArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class SumRangeArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    end_cell: str
    start_cell: str


SUM_RANGE_ARGUMENTS = TypeAdapter(SumRangeArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class SumCellsArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cells: list[str | ReferenceTarget]


SUM_CELLS_ARGUMENTS = TypeAdapter(SumCellsArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class SimpleDivisionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell1: str
    cell2: str


SIMPLE_DIVISION_ARGUMENTS = TypeAdapter(SimpleDivisionArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class NumberDivisionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    number1: int | float
    number2: int | float


NUMBER_DIVISION_ARGUMENTS = TypeAdapter(NumberDivisionArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class DivisionParenthesesMultiplicationArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell1: str
    cell2: str
    number: int | float


DIVISION_PARENTHESES_MULTIPLICATION_ARGUMENTS = TypeAdapter(
    DivisionParenthesesMultiplicationArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class AverageCellsArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cells: list[str]


AVERAGE_CELLS_ARGUMENTS = TypeAdapter(AverageCellsArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class CrossSheetMultiplicationThreeArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell1: str
    cell2: str
    number: int | float
    sheet1: str | None
    sheet2: str | None


CROSS_SHEET_MULTIPLICATION_THREE_ARGUMENTS = TypeAdapter(
    CrossSheetMultiplicationThreeArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class IfArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    condition: str
    false_val: object
    true_val: object


IF_ARGUMENTS = TypeAdapter(IfArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class IfErrorArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    value: object
    value_if_error: str


IF_ERROR_ARGUMENTS = TypeAdapter(IfErrorArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class PmtArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    nper: str
    pv: str
    rate: str


PMT_ARGUMENTS = TypeAdapter(PmtArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class VLookupArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    col_index_num: str
    lookup_value: str
    range_lookup: str
    table_array: str


V_LOOKUP_ARGUMENTS = TypeAdapter(VLookupArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class CellDivisionByNumberArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell: str
    number: int | float


CELL_DIVISION_BY_NUMBER_ARGUMENTS = TypeAdapter(CellDivisionByNumberArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class CellDivisionByNumberMultiplicationByNumberArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell1: str
    cell2: str
    number1: int | float
    number2: int | float


CELL_DIVISION_BY_NUMBER_MULTIPLICATION_BY_NUMBER_ARGUMENTS = TypeAdapter(
    CellDivisionByNumberMultiplicationByNumberArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class CellDivisionByNumberDivisionByNumberArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell: str
    number1: int | float
    number2: int | float


CELL_DIVISION_BY_NUMBER_DIVISION_BY_NUMBER_ARGUMENTS = TypeAdapter(
    CellDivisionByNumberDivisionByNumberArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class MultiplicationThreeValuesArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    number: int | float
    operands: list[ReferenceTarget]


MULTIPLICATION_THREE_VALUES_ARGUMENTS = TypeAdapter(MultiplicationThreeValuesArguments)


@with_config(ConfigDict(strict=True, extra="allow"))
class MultiplicationWithDivisionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell1: str
    cell2: str
    cell3: str


MULTIPLICATION_WITH_DIVISION_ARGUMENTS = TypeAdapter(
    MultiplicationWithDivisionArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class ParenthesesMultiplicationDivisionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    divisor: int | float
    num1: int | float
    num2: int | float


PARENTHESES_MULTIPLICATION_DIVISION_ARGUMENTS = TypeAdapter(
    ParenthesesMultiplicationDivisionArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class NestedArithmeticExpressionArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell: str
    num1: int | float
    num2: int | float
    num3: int | float


NESTED_ARITHMETIC_EXPRESSION_ARGUMENTS = TypeAdapter(
    NestedArithmeticExpressionArguments,
)


@with_config(ConfigDict(strict=True, extra="allow"))
class DivisionMultiplicationSequenceArguments(TypedDict):
    """Retain the required fields and scalar types of this formula shape."""

    cell: str
    num1: int | float
    num2: int | float


DIVISION_MULTIPLICATION_SEQUENCE_ARGUMENTS = TypeAdapter(
    DivisionMultiplicationSequenceArguments,
)
