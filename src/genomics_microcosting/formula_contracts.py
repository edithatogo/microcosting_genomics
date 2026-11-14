# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Strict contracts for the foundational parsed-formula variants."""

from typing import Literal, NotRequired, TypedDict

from pydantic import ConfigDict, TypeAdapter, with_config


@with_config(ConfigDict(strict=True, extra="allow"))
class NumericLiteral(TypedDict):
    """Retain the numeric and boolean literals accepted by the existing parser."""

    type: Literal["literal"]
    value: int | float | bool


@with_config(ConfigDict(strict=True, extra="allow"))
class StringLiteral(TypedDict):
    """Retain a literal string without numeric coercion."""

    type: Literal["string_literal"]
    value: str


@with_config(ConfigDict(strict=True, extra="allow"))
class CellReference(TypedDict):
    """Preserve absent, local and explicit worksheet reference semantics."""

    type: Literal["reference"]
    cell: str
    sheet: NotRequired[str | None]


@with_config(ConfigDict(strict=True, extra="allow"))
class ReferenceTarget(TypedDict):
    """Cell component API permits references without a parser discriminator."""

    cell: str
    sheet: NotRequired[str | None]


@with_config(ConfigDict(strict=True, extra="allow"))
class ArithmeticFormula(TypedDict):
    """Retain ordered operands for addition and multiplication."""

    type: Literal["addition", "multiplication"]
    operands: list[dict[str, object]]


@with_config(ConfigDict(strict=True, extra="allow"))
class LookupFormula(TypedDict):
    """Preserve lookup expressions and matching mode as parsed source strings."""

    type: Literal["vlookup"]
    lookup_value: str
    table_array: str
    col_index_num: str
    range_lookup: str


ARITHMETIC = TypeAdapter(ArithmeticFormula)
LOOKUP = TypeAdapter(LookupFormula)
NUMERIC_LITERAL = TypeAdapter(NumericLiteral)
STRING_LITERAL = TypeAdapter(StringLiteral)
CELL_REFERENCE = TypeAdapter(CellReference)
REFERENCE_TARGET = TypeAdapter(ReferenceTarget)
FORMULA_RECORD = TypeAdapter(dict[str, object])


def validate_formula_record(value: object) -> dict[str, object] | None:
    """Validate foundational variants and preserve other recorded formula shapes."""
    if value is None:
        return None
    record = FORMULA_RECORD.validate_python(value)
    kind = record.get("type")
    if kind == "literal":
        NUMERIC_LITERAL.validate_python(record)
    elif kind == "string_literal":
        STRING_LITERAL.validate_python(record)
    elif kind == "reference":
        CELL_REFERENCE.validate_python(record)
    elif kind in {"addition", "multiplication"}:
        arithmetic = ARITHMETIC.validate_python(record)
        for operand in arithmetic["operands"]:
            validate_formula_record(operand)
    elif kind == "vlookup":
        LOOKUP.validate_python(record)
    return record
