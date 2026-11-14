# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check formula structure and typed literals."""

from typing import cast

from genomics_microcosting.arithmetic_parser import parse_arithmetic
from genomics_microcosting.formula_parser import parse_formula
from tests.checks import require_equal, require_runtime_instance


def test_parse_multiplication_same_sheet() -> None:
    """Check parse multiplication same sheet."""
    formula = "='1. Detailed Table'!E3*'1. Detailed Table'!I3"
    expected = {
        "type": "multiplication",
        "operands": [
            {"type": "reference", "sheet": "1. Detailed Table", "cell": "E3"},
            {"type": "reference", "sheet": "1. Detailed Table", "cell": "I3"},
        ],
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_multiplication_different_sheets() -> None:
    """Check parse multiplication different sheets."""
    formula = "='1. Detailed Table'!E5*'2. Labor Prices'!C5"
    expected = {
        "type": "multiplication",
        "operands": [
            {"type": "reference", "sheet": "1. Detailed Table", "cell": "E5"},
            {"type": "reference", "sheet": "2. Labor Prices", "cell": "C5"},
        ],
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_multiplication_no_sheet() -> None:
    """Check parse multiplication no sheet."""
    formula = "=E744*I744"
    expected = {
        "type": "multiplication",
        "operands": [
            {"type": "reference", "sheet": None, "cell": "E744"},
            {"type": "reference", "sheet": None, "cell": "I744"},
        ],
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_multiplication_by_number() -> None:
    """Check parse multiplication by number."""
    formula = "=F769*3"
    expected = {
        "type": "multiplication_by_number",
        "sheet": None,
        "cell": "F769",
        "number": 3.0,
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_multiplication_three_values() -> None:
    """Check parse multiplication three values."""
    formula = "=E744*I744*3"
    expected = {
        "type": "multiplication_three_values",
        "operands": [
            {"sheet": None, "cell": "E744"},
            {"sheet": None, "cell": "I744"},
        ],
        "number": 3,
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_addition_simple() -> None:
    """Check parse addition simple."""
    formula = "=A1+A2"
    expected = {
        "type": "addition",
        "operands": [
            {"type": "reference", "sheet": None, "cell": "A1"},
            {"type": "reference", "sheet": None, "cell": "A2"},
        ],
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_with_sheet() -> None:
    """Check parse reference with sheet."""
    formula = "='3. Estimates'!F5"
    expected = {"type": "reference", "sheet": "3. Estimates", "cell": "F5"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_no_sheet() -> None:
    """Check parse reference no sheet."""
    formula = "=F10"
    expected = {"type": "reference", "sheet": None, "cell": "F10"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_with_plus() -> None:
    """Check parse reference with plus."""
    formula = "=+'3. Estimates'!F10"
    expected = {"type": "reference", "sheet": "3. Estimates", "cell": "F10"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_sum_range() -> None:
    """Check parse SUM range."""
    formula = "=SUM(M3:M6)"
    expected = {"type": "sum_range", "start_cell": "M3", "end_cell": "M6"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_sum_cells() -> None:
    """Check parse SUM cells."""
    formula = "=SUM(M744,M748,M752)"
    expected = {"type": "sum_cells", "cells": ["M744", "M748", "M752"]}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_multiplication_by_number_with_sheet() -> None:
    """Check parse multiplication by number with sheet."""
    formula = "='Sheet2'!A2*3"
    expected = {
        "type": "multiplication_by_number",
        "sheet": "Sheet2",
        "cell": "A2",
        "number": 3,
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_vlookup() -> None:
    """Check parse VLOOKUP."""
    formula = "=VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE)"
    expected = {
        "type": "vlookup",
        "lookup_value": "C12",
        "table_array": "'3. Estimates'!$A$4:$G$13",
        "col_index_num": "7",
        "range_lookup": "FALSE",
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_pmt_simple() -> None:
    """Check parse PMT simple."""
    formula = "=PMT(0.05,10,-1000)"
    expected = {
        "type": "pmt",
        "rate": "0.05",
        "nper": "10",
        "pv": "-1000",
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_pmt_percent_and_cells() -> None:
    """Check parse PMT percent and cells."""
    formula = "=PMT(4.52%, E5, -H5)"
    expected = {
        "type": "pmt",
        "rate": "4.52%",
        "nper": "E5",
        "pv": "-H5",
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_iferror_with_vlookup() -> None:
    """Check parse IFERROR with VLOOKUP."""
    formula = "=IFERROR(VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE),0)"
    expected = {
        "type": "iferror",
        "value": {
            "type": "vlookup",
            "lookup_value": "C12",
            "table_array": "'3. Estimates'!$A$4:$G$13",
            "col_index_num": "7",
            "range_lookup": "FALSE",
        },
        "value_if_error": "0",
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_if() -> None:
    """Check parse IF."""
    formula = "=IF(E770=0,0,E770*I770)"
    expected = {
        "type": "if",
        "condition": "E770=0",
        "true_val": {"type": "literal", "value": 0},
        "false_val": {
            "type": "multiplication",
            "operands": [
                {"type": "reference", "sheet": None, "cell": "E770"},
                {"type": "reference", "sheet": None, "cell": "I770"},
            ],
        },
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_numeric_literal_formula() -> None:
    """Check parse numeric literal formula."""
    formula = "=3"
    if not (parse_formula(formula) == {"type": "literal", "value": 3}):
        raise AssertionError


def test_parse_string_literal() -> None:
    """Check parse string literal."""
    formula = '="Test"'
    expected = {"type": "string_literal", "value": "Test"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_literal_integer() -> None:
    """Check parse literal integer."""
    if not (parse_formula(0) == {"type": "literal", "value": 0}):
        raise AssertionError


def test_parse_literal_float() -> None:
    """Check parse literal float."""
    if not (parse_formula(1.5) == {"type": "literal", "value": 1.5}):
        raise AssertionError


def test_parse_sum_cells_range() -> None:
    """Test parsing SUM with multiple cell ranges."""
    formula = "=SUM(A1:A5,B1:B5)"
    expected = {"type": "sum_cells", "cells": ["A1:A5", "B1:B5"]}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_with_unquoted_sheet() -> None:
    """Test parsing reference with unquoted sheet name."""
    formula = "=Sheet1!A1"
    expected = {"type": "reference", "sheet": "Sheet1", "cell": "A1"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_with_dollar_signs() -> None:
    """Test parsing reference with dollar signs."""
    formula = "=$A$1"
    expected = {"type": "reference", "sheet": None, "cell": "$A$1"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_reference_with_sheet_and_dollar_signs() -> None:
    """Test parsing reference with sheet name and dollar signs."""
    formula = "=Sheet1!$A$1"
    expected = {"type": "reference", "sheet": "Sheet1", "cell": "$A$1"}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_negative_number() -> None:
    """Test parsing negative numeric literals."""
    formula = "=-5"
    expected = {"type": "literal", "value": -5}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_float_with_leading_dot() -> None:
    """Test parsing float with leading dot.

    Currently not supported - returns unknown type.
    This is an edge case that could be improved in future.
    """
    formula = "=.5"
    result = parse_formula(formula)
    if result is None or result["type"] != "unknown":
        raise AssertionError


def test_parse_complex_if_condition() -> None:
    """Test parsing complex IF with comparison operators."""
    formula = "=IF(A1<=B1,1,0)"
    result = parse_formula(formula)
    if result is None or result["type"] != "if":
        raise AssertionError
    if not (result["condition"] == "A1<=B1"):
        raise AssertionError


def test_parse_if_with_nested_operations() -> None:
    """Test parsing IF with nested operations in branches."""
    formula = "=IF(A1>0,SUM(B1:B5),A1*B1)"
    result = parse_formula(formula)
    if result is None or result["type"] != "if":
        raise AssertionError
    if not (result["condition"] == "A1>0"):
        raise AssertionError
    true_branch = result["true_val"]
    if not isinstance(true_branch, dict) or true_branch["type"] != "sum_range":
        raise AssertionError
    false_branch = result["false_val"]
    if not isinstance(false_branch, dict) or false_branch["type"] != "multiplication":
        raise AssertionError


def test_parse_vlookup_with_true_range_lookup() -> None:
    """Test parsing VLOOKUP with TRUE range lookup."""
    formula = "=VLOOKUP(C12,E3:G13,2,TRUE)"
    expected = {
        "type": "vlookup",
        "lookup_value": "C12",
        "table_array": "E3:G13",
        "col_index_num": "2",
        "range_lookup": "TRUE",
    }
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_division() -> None:
    """Test parsing division operations.

    Currently not supported - returns unknown type.
    This is an edge case that could be improved in future.
    """
    formula = "=A1/B1"
    result = parse_formula(formula)
    if not (result == {"type": "simple_division", "cell1": "A1", "cell2": "B1"}):
        raise AssertionError


def test_parse_complex_formula() -> None:
    """Test parsing a complex formula combining multiple operations."""
    formula = "=SUM(A1:A5)*B1+IF(C1>0,1,0)"
    result = parse_formula(formula)
    # This would be parsed as addition with SUM and IF operations
    if result is None or result["type"] != "addition":
        raise AssertionError
    operands = result["operands"]
    require_runtime_instance(operands, list)
    require_equal(len(cast("list[object]", operands)), 2)


def test_parse_unsupported_formula() -> None:
    """Test parsing an unsupported formula type."""
    formula = "=AVERAGE(A1:A5)"
    result = parse_formula(formula)
    if not (result == {"type": "average_range", "start_cell": "A1", "end_cell": "A5"}):
        raise AssertionError


def test_parse_unknown() -> None:
    """Check parse unknown."""
    formula = "=SOMEOTHERFUNCTION(A1)"
    expected = {"type": "unknown", "formula": formula}
    if not (parse_formula(formula) == expected):
        raise AssertionError


def test_parse_none() -> None:
    """Check parsing when no formula is supplied."""
    if parse_formula(None) is not None:
        raise AssertionError


def test_parse_not_a_formula() -> None:
    """Check parse not a formula."""
    if parse_formula("some string") is not None:
        raise AssertionError


def test_quoted_sheet_plus_is_part_of_reference() -> None:
    """A plus inside a quoted worksheet title is not an addition operator."""
    result = parse_formula("='BI - Comp+Stor Costs - VCGS'!J18")
    if not (
        result
        == {
            "type": "reference",
            "sheet": "BI - Comp+Stor Costs - VCGS",
            "cell": "J18",
        }
    ):
        raise AssertionError


def test_arithmetic_fallback_rejects_executable_syntax() -> None:
    """Keep function calls and attribute access outside the restricted translator."""
    if parse_arithmetic("__import__('os').system('true')") is not None:
        raise AssertionError
    if parse_arithmetic("A1.__class__") is not None:
        raise AssertionError
