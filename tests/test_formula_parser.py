import pytest
from unimelb_phd_phase_1.formula_parser import parse_formula

def test_parse_multiplication_same_sheet():
    formula = "='1. Detailed Table'!E3*'1. Detailed Table'!I3"
    expected = {
        "type": "multiplication",
        "operands": [
            {"sheet": "1. Detailed Table", "cell": "E3"},
            {"sheet": "1. Detailed Table", "cell": "I3"},
        ]
    }
    assert parse_formula(formula) == expected

def test_parse_multiplication_different_sheets():
    formula = "='1. Detailed Table'!E5*'2. Labor Prices'!C5"
    expected = {
        "type": "multiplication",
        "operands": [
            {"sheet": "1. Detailed Table", "cell": "E5"},
            {"sheet": "2. Labor Prices", "cell": "C5"},
        ]
    }
    assert parse_formula(formula) == expected

def test_parse_multiplication_no_sheet():
    formula = "=E744*I744"
    expected = {
        "type": "multiplication",
        "operands": [
            {"sheet": None, "cell": "E744"},
            {"sheet": None, "cell": "I744"},
        ]
    }
    assert parse_formula(formula) == expected

def test_parse_multiplication_by_number():
    formula = "=F769*3"
    expected = {
        "type": "multiplication_by_number",
        "cell": "F769",
        "number": 3
    }
    assert parse_formula(formula) == expected

def test_parse_multiplication_three_values():
    formula = "=E744*I744*3"
    expected = {
        "type": "multiplication_three_values",
        "operands": [
            {"sheet": None, "cell": "E744"},
            {"sheet": None, "cell": "I744"},
        ],
        "number": 3
    }
    assert parse_formula(formula) == expected

def test_parse_addition_simple():
    formula = "=A1+A2"
    expected = {
        "type": "addition",
        "operands": [
            {"type": "reference", "sheet": None, "cell": "A1"},
            {"type": "reference", "sheet": None, "cell": "A2"},
        ],
    }
    assert parse_formula(formula) == expected

def test_parse_reference_with_sheet():
    formula = "='3. Estimates'!F5"
    expected = {"type": "reference", "sheet": "3. Estimates", "cell": "F5"}
    assert parse_formula(formula) == expected

def test_parse_reference_no_sheet():
    formula = "=F10"
    expected = {"type": "reference", "sheet": None, "cell": "F10"}
    assert parse_formula(formula) == expected

def test_parse_reference_with_plus():
    formula = "=+'3. Estimates'!F10"
    expected = {"type": "reference", "sheet": "3. Estimates", "cell": "F10"}
    assert parse_formula(formula) == expected

def test_parse_sum_range():
    formula = "=SUM(M3:M6)"
    expected = {"type": "sum_range", "start_cell": "M3", "end_cell": "M6"}
    assert parse_formula(formula) == expected

def test_parse_sum_cells():
    formula = "=SUM(M744,M748,M752)"
    expected = {"type": "sum_cells", "cells": ["M744", "M748", "M752"]}
    assert parse_formula(formula) == expected

def test_parse_multiplication_by_number_with_sheet():
    formula = "='Sheet2'!A2*3"
    expected = {
        "type": "multiplication_by_number",
        "sheet": "Sheet2",
        "cell": "A2",
        "number": 3,
    }
    assert parse_formula(formula) == expected

def test_parse_vlookup():
    formula = "=VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE)"
    expected = {
        "type": "vlookup",
        "lookup_value": "C12",
        "table_array": "'3. Estimates'!$A$4:$G$13",
        "col_index_num": "7",
        "range_lookup": "FALSE"
    }
    assert parse_formula(formula) == expected

def test_parse_pmt_simple():
    formula = "=PMT(0.05,10,-1000)"
    expected = {
        "type": "pmt",
        "rate": "0.05",
        "nper": "10",
        "pv": "-1000",
    }
    assert parse_formula(formula) == expected

def test_parse_pmt_percent_and_cells():
    formula = "=PMT(4.52%, E5, -H5)"
    expected = {
        "type": "pmt",
        "rate": "4.52%",
        "nper": "E5",
        "pv": "-H5",
    }
    assert parse_formula(formula) == expected

def test_parse_iferror_with_vlookup():
    formula = "=IFERROR(VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE),0)"
    expected = {
        "type": "iferror",
        "value": {
            "type": "vlookup",
            "lookup_value": "C12",
            "table_array": "'3. Estimates'!$A$4:$G$13",
            "col_index_num": "7",
            "range_lookup": "FALSE"
        },
        "value_if_error": "0"
    }
    assert parse_formula(formula) == expected

def test_parse_if():
    formula = "=IF(E770=0,0,E770*I770)"
    expected = {
        "type": "if",
        "condition": "E770=0",
        "true_val": {"type": "literal", "value": 0},
        "false_val": {
            "type": "multiplication",
            "operands": [
                {"sheet": None, "cell": "E770"},
                {"sheet": None, "cell": "I770"},
            ]
        }
    }
    assert parse_formula(formula) == expected

def test_parse_numeric_literal_formula():
    formula = "=3"
    assert parse_formula(formula) == {"type": "literal", "value": 3}

def test_parse_string_literal():
    formula = '="Test"'
    expected = {"type": "string_literal", "value": "Test"}
    assert parse_formula(formula) == expected

def test_parse_literal_integer():
    assert parse_formula(0) == {"type": "literal", "value": 0}

def test_parse_literal_float():
    assert parse_formula(1.5) == {"type": "literal", "value": 1.5}

def test_parse_unknown():
    formula = "=SOMEOTHERFUNCTION(A1)"
    expected = {"type": "unknown", "formula": formula}
    assert parse_formula(formula) == expected

def test_parse_none():
    assert parse_formula(None) is None

def test_parse_not_a_formula():
    assert parse_formula("some string") is None
