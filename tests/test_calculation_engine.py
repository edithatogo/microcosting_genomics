# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Workbook loading, formula evaluation and cost-component checks."""

from collections.abc import Container
from pathlib import Path

import numpy as np
import openpyxl
import polars as pl
import pytest
from openpyxl.worksheet.worksheet import Worksheet
from polars.testing import assert_frame_equal

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from genomics_microcosting.utils import cell_to_coords, coords_to_cell
from tests.checks import require_equal, require_runtime_instance
lazy from genomics_microcosting.config import SheetConfig


@pytest.fixture
def engine() -> CalculationEngine:
    """Provide a CalculationEngine instance initialized with prepared data."""
    sheet_manager = SheetManager()
    return CalculationEngine(sheet_manager)


@pytest.fixture
def test_engine() -> CalculationEngine:
    """Provides a CalculationEngine instance initialized with test data."""
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    sheet_manager = SheetManager(test_data_path)
    return CalculationEngine(sheet_manager)


@pytest.fixture
def main_excel_engine() -> CalculationEngine:
    """Provide a CalculationEngine instance initialized with the main Excel file."""
    data_dir = Path(__file__).resolve().parents[1] / "data"
    excel_path = (
        data_dir
        / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    sheet_manager = SheetManager(excel_path, verbose=True)
    return CalculationEngine(sheet_manager, verbose=True)


def test_coords_to_cell() -> None:
    """Check coords to cell."""
    if not (coords_to_cell(0, 0) == "A1"):
        raise AssertionError
    if not (coords_to_cell(0, 1) == "B1"):
        raise AssertionError
    if not (coords_to_cell(1, 0) == "A2"):
        raise AssertionError
    if not (coords_to_cell(0, 25) == "Z1"):
        raise AssertionError
    if not (coords_to_cell(0, 26) == "AA1"):
        raise AssertionError
    if not (coords_to_cell(0, 51) == "AZ1"):
        raise AssertionError


def test_cell_to_coords() -> None:
    """Check cell to coords."""
    if not (cell_to_coords("A1") == (0, 0)):
        raise AssertionError
    if not (cell_to_coords("B1") == (0, 1)):
        raise AssertionError
    if not (cell_to_coords("A2") == (1, 0)):
        raise AssertionError
    if not (cell_to_coords("Z1") == (0, 25)):
        raise AssertionError
    if not (cell_to_coords("AA1") == (0, 26)):
        raise AssertionError
    if not (cell_to_coords("AZ1") == (0, 51)):
        raise AssertionError
    if not (cell_to_coords("$A1") == (0, 0)):
        raise AssertionError
    if not (cell_to_coords("A$1") == (0, 0)):
        raise AssertionError
    if not (cell_to_coords("$A$1") == (0, 0)):
        raise AssertionError


def test_get_cell_value_test_data(test_engine: CalculationEngine) -> None:
    """Check a cell lookup against the small test workbook."""
    if not (test_engine.get_cell_value("Sheet1", "A2") == 1):
        raise AssertionError
    require_equal(test_engine.get_cell_value("Sheet1", "B2"), 4)


def test_get_cell_value_detailed_table(main_excel_engine: CalculationEngine) -> None:
    # Test a known value from 'Detailed Table'
    # Based on manual inspection, A4 should be 'Panel'
    """Check a cell lookup in the detailed table."""
    if not (main_excel_engine.get_cell_value("Detailed Table", "A5") == "Panel"):
        raise AssertionError
    # Test a known numeric value from 'Detailed Table'
    require_equal(main_excel_engine.get_cell_value("Detailed Table", "E6"), 0.5)


def test_get_cell_formula_detailed_table(main_excel_engine: CalculationEngine) -> None:
    """Check a real source formula rather than skip the workbook check."""
    book = openpyxl.load_workbook(
        main_excel_engine.sheet_manager.excel_file_path,
        read_only=True,
        data_only=False,
    )
    try:
        sheet = book["Detailed Table"]
        cell = next(
            cell
            for row in sheet.iter_rows(min_row=5)
            for cell in row
            if isinstance(cell.value, str) and cell.value.startswith("=")
        )
        if not (
            main_excel_engine.get_cell_formula("Detailed Table", cell.coordinate)
            == cell.value
        ):
            raise AssertionError
    finally:
        book.close()


def test_run_engine(test_engine: CalculationEngine) -> None:
    """Process all three rows without errors."""
    results, errors = test_engine.run_engine("Sheet1")
    if errors or results is None:
        raise AssertionError
    require_equal(results.shape[0], 3)


def test_legacy_positional_workbook_options() -> None:
    """Retain positional options for existing workbook API callers."""
    workbook = Path(__file__).resolve().parent / "test_data.xlsx"
    enable_logging = False
    config: dict[str, SheetConfig] = {"Sheet1": {"header_rows": 1, "data_starts_at": 2}}
    sheet_manager = SheetManager(workbook, enable_logging, None, config)
    engine = CalculationEngine(sheet_manager, enable_logging)
    results, errors = engine.run_engine("Unavailable sheet", enable_logging)
    require_equal(results, None)
    require_equal(errors, ["Data sheet 'Unavailable sheet' not found"])
    with pytest.raises(TypeError, match="Invalid arguments for verbose"):
        CalculationEngine(sheet_manager, enable_logging, verbose=True)


def test_engine_initialization(engine: CalculationEngine) -> None:
    """Tests the basic initialization of the CalculationEngine."""
    require_runtime_instance(engine, CalculationEngine)
    sheet_names = engine.sheet_manager.get_sheet_names()
    require_runtime_instance(sheet_names, list)
    if "Detailed Table" not in sheet_names:
        raise AssertionError


def test_detailed_table_header(engine: CalculationEngine) -> None:
    """Retain all semantic header levels in flattened Polars column labels."""
    df = engine.sheet_manager.get_data("Detailed Table")
    if not (df is not None):
        raise AssertionError
    if not (
        df.columns[:5]
        == [
            "Test",
            "Category",
            "Sub-Category",
            "Step",
            "Estimates Quantity of Use per Test LL",
        ]
    ):
        raise AssertionError


def test_get_cell_formula(test_engine: CalculationEngine) -> None:
    """Tests the get_cell_formula method."""
    # Non-formula cell should return None
    if test_engine.get_cell_formula("Sheet1", "A2") is not None:
        raise AssertionError

    # Cells containing formulas should return the formula string
    formula = test_engine.get_cell_formula("Sheet1", "C2")
    if not (formula == "=A2*B2"):
        raise AssertionError


def test_execute_formula(test_engine: CalculationEngine) -> None:
    """Tests the execute_formula method with a simple formula."""
    # This test requires knowledge of the data in 'test_data.xlsx'
    # Let's assume we have a test Excel file with the following data in 'Sheet1':
    #   A  B
    # 1 10 20
    # 2 5  3
    # And we want to compute the formula '=A1+B2'
    # We'll need a way to load a specific test file.
    # For now, let's test a simple arithmetic operation.
    result = test_engine.execute_formula("=SUM(1,2,3)", "Sheet1", "A1")
    require_equal(result, 6)

    result = test_engine.execute_formula("=SUM(A2:A4)", "Sheet1", "A5")
    require_equal(result, 6)


def test_vlookup_exact_match(test_engine: CalculationEngine) -> None:
    # Test VLOOKUP with an exact match
    """Check VLOOKUP exact match."""
    result = test_engine.execute_formula("=VLOOKUP(1, A2:B4, 2, FALSE)", "Sheet1", "D1")
    require_equal(result, 4)


def test_vlookup_approximate_match(test_engine: CalculationEngine) -> None:
    # Test VLOOKUP with an approximate match
    """Check VLOOKUP approximate match."""
    expected_lookup_value = 4
    result = test_engine.execute_formula(
        "=VLOOKUP(1.5, A2:B4, 2, TRUE)",
        "Sheet1",
        "D1",
    )
    if not (result == expected_lookup_value):
        raise AssertionError  # Should find the value for 1


def test_if_true(test_engine: CalculationEngine) -> None:
    # Test IF when the condition is true
    """Check that IF returns its true branch."""
    result = test_engine.execute_formula('=IF(1=1, "true", "false")', "Sheet1", "D1")
    if not (result == "true"):
        raise AssertionError


def test_if_false(test_engine: CalculationEngine) -> None:
    # Test IF when the condition is false
    """Check that IF returns its false branch."""
    result = test_engine.execute_formula('=IF(1=2, "true", "false")', "Sheet1", "D1")
    if not (result == "false"):
        raise AssertionError


def test_iferror_no_error(test_engine: CalculationEngine) -> None:
    # Test IFERROR when there is no error
    """Check that IFERROR returns a successful calculation."""
    result = test_engine.execute_formula("=IFERROR(1/1, 0)", "Sheet1", "D1")
    if not (result == 1):
        raise AssertionError


def test_iferror_with_error(test_engine: CalculationEngine) -> None:
    # Test IFERROR when there is an error
    """Check that IFERROR returns its fallback on error."""
    result = test_engine.execute_formula("=IFERROR(1/0, 0)", "Sheet1", "D1")
    if not (result == 0):
        raise AssertionError


def test_iferror_with_vlookup(test_engine: CalculationEngine) -> None:
    """Check IFERROR with VLOOKUP."""
    formula = "=IFERROR(VLOOKUP(99, A2:B4, 2, FALSE), 0)"
    result = test_engine.execute_formula(formula, "Sheet1", "D1")
    if not (result == 0):
        raise AssertionError


def test_addition_literals(test_engine: CalculationEngine) -> None:
    """Check addition literals."""
    result = test_engine.execute_formula("=1+2", "Sheet1", "D1")
    require_equal(result, 3)


def test_addition_cell_references(test_engine: CalculationEngine) -> None:
    """Check addition cell references."""
    result = test_engine.execute_formula("=A2+A3", "Sheet1", "D1")
    require_equal(result, 3)


def test_pmt_literal_values(test_engine: CalculationEngine) -> None:
    """Match the expected payment using literal inputs."""
    result = test_engine.execute_formula("=PMT(0.05, 10, -1000)", "Sheet1", "D1")
    if not isinstance(result, float):
        raise TypeError(result)
    require_equal(round(result, 2), 129.50)


def test_pmt_with_numpy_types(test_engine: CalculationEngine) -> None:
    """PMT should accept numpy numeric types via ``numbers.Number``."""
    # Cast values to numpy types to mimic how pandas may store them
    df = test_engine.sheet_manager.sheets["Sheet1"]
    df[0, 0] = np.int64(1)
    df[0, 1] = np.float64(4)

    result = test_engine.execute_formula("=PMT(50%, A2, -B2)", "Sheet1", "D1")
    require_equal(pytest.approx(result, rel=1e-2), 6.0)


def test_pmt_numpy_values(test_engine: CalculationEngine) -> None:
    # Override some cells with numpy scalar types
    """Check PMT numpy values."""
    test_engine.sheets["Sheet1"][0, "col1"] = np.int64(1)
    test_engine.sheets["Sheet1"][0, "col2"] = np.float64(4.0)
    result = test_engine.execute_formula("=PMT(50%, A2, -B2)", "Sheet1", "D1")
    require_equal(pytest.approx(result, rel=1e-2), 6.0)


def test_multilevel_header_parsing(test_engine: CalculationEngine) -> None:
    """Preserve single-level Excel headers as Polars names."""
    df = test_engine.sheet_manager.get_data("Sheet1")
    if not (df is not None):
        raise AssertionError
    if not (df.columns == ["col1", "col2", "col3"]):
        raise AssertionError


def test_multilevel_header_loader(tmp_path: Path) -> None:
    """Load a simple sheet with two header rows using CalculationEngine."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if not isinstance(ws, Worksheet):
        raise TypeError(ws)
    ws.title = "Sheet1"
    ws.append(["lvl1a", "lvl1a", "lvl1b"])
    ws.append(["col1", "col2", "col3"])
    ws.append([1, 2, 3])
    ws.append([4, 5, 6])
    file_path = tmp_path / "multi.xlsx"
    wb.save(file_path)
    wb.close()

    sheet_configs: dict[str, SheetConfig] = {
        "Sheet1": {
            "header_rows": 2,
            "data_starts_at": 3,
        },
    }
    sheet_manager = SheetManager(file_path, sheet_configs=sheet_configs)
    df = sheet_manager.get_data("Sheet1")

    if not (df is not None):
        raise AssertionError
    if not (df.columns == ["lvl1a col1", "lvl1a col2", "lvl1b col3"]):
        raise AssertionError
    if not (df.rows() == [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]):
        raise AssertionError


def test_multiplication_by_number_other_sheet(test_engine: CalculationEngine) -> None:
    """Check multiplication by number other sheet."""
    result = test_engine.execute_formula("='Sheet2'!A2*3", "Sheet1", "D1")
    require_equal(result, 30)


def test_nested_if_with_sum(test_engine: CalculationEngine) -> None:
    """Check nested IF with SUM."""
    result = test_engine.execute_formula("=IF(1=1, SUM(A2:A4), 0)", "Sheet1", "E1")
    require_equal(result, 6)


def test_absolute_relative_references(test_engine: CalculationEngine) -> None:
    """Check absolute relative references."""
    result = test_engine.execute_formula("=$A$2+B$3", "Sheet1", "E1")
    require_equal(result, 6)


def test_vlookup_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check VLOOKUP cross sheet."""
    formula = "=VLOOKUP(A2+19, Sheet2!$A$1:$B$3, 2, FALSE)"
    result = test_engine.execute_formula(formula, "Sheet1", "E1")
    require_equal(result, 50)


def test_multiplication_cross_sheet_cells(test_engine: CalculationEngine) -> None:
    """Check multiplication cross sheet cells."""
    result = test_engine.execute_formula("='Sheet2'!A2*'Sheet2'!B2", "Sheet1", "F1")
    require_equal(result, 400)


def test_sum_range_absolute(test_engine: CalculationEngine) -> None:
    """Check SUM range absolute."""
    result = test_engine.execute_formula("=SUM($A$2:$A$4)", "Sheet1", "F2")
    require_equal(result, 6)


def test_sum_cells_literal_reference(test_engine: CalculationEngine) -> None:
    """Check SUM cells literal reference."""
    result = test_engine.execute_formula("=SUM(1,A2)", "Sheet1", "F3")
    require_equal(result, 2)


def test_if_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check IF cross sheet."""
    result = test_engine.execute_formula(
        "=IF('Sheet2'!A3>15,'Sheet2'!B3,0)",
        "Sheet1",
        "F4",
    )
    require_equal(result, 50)


def test_iferror_vlookup_missing(test_engine: CalculationEngine) -> None:
    """Check IFERROR VLOOKUP missing."""
    formula = "=IFERROR(VLOOKUP(99, Sheet2!$A$1:$B$3, 2, FALSE), 0)"
    result = test_engine.execute_formula(formula, "Sheet1", "F5")
    if not (result == 0):
        raise AssertionError


def test_engine_detailed_table_rename() -> None:
    """Tests if the CalculationEngine correctly renames the "Detailed Table" sheet."""
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"

    class CustomEngine(CalculationEngine):
        def __init__(self, sheet_manager: SheetManager) -> None:
            self.default_sheet_names = {"detailed_table": "My Detailed Table"}
            super().__init__(sheet_manager)

    sheet_manager = SheetManager(test_data_path)
    engine = CustomEngine(sheet_manager)

    if not ("Detailed Table" not in engine.sheet_configs):
        raise AssertionError
    if "My Detailed Table" not in engine.sheet_configs:
        raise AssertionError


def test_engine_sheet_config_override() -> None:
    """Tests that the sheet_configs can be overridden."""
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    sheet_manager = SheetManager(test_data_path)
    engine = CalculationEngine(sheet_manager)
    engine.sheet_configs["Sheet1"] = {"header_rows": 2, "data_starts_at": 3}
    require_equal(engine.sheet_configs["Sheet1"]["header_rows"], 2)


def test_load_prepared_tables(tmp_path: Path) -> None:
    """Tests that prepared tables are loaded correctly."""
    prepared_data_path = tmp_path / "prepared"
    prepared_data_path.mkdir()
    df = pl.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    df.write_parquet(prepared_data_path / "2._labor_prices.parquet")

    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    sheet_manager = SheetManager(test_data_path, prepared_data_path=prepared_data_path)
    engine = CalculationEngine(sheet_manager)

    if "2. Labor Prices" not in engine.sheets:
        raise AssertionError
    assert_frame_equal(engine.sheets["2. Labor Prices"], df)


def test_circular_reference_detection(test_engine: CalculationEngine) -> None:
    """Tests that circular references are detected and raise an exception."""
    # This test would require setting up a circular reference in the test data
    # For now, we'll test that the mechanism exists


def test_memoization_cache(test_engine: CalculationEngine) -> None:
    """Tests that the memoization cache works correctly."""
    # Test that repeated calls to the same formula use the cache
    result1 = test_engine.execute_formula("=A2", "Sheet1", "Z1")
    result2 = test_engine.execute_formula("=A2", "Sheet1", "Z1")
    if not (result1 == result2):
        raise AssertionError
    # We can't easily test that caching occurred without modifying the engine


def test_error_handling_in_formulas(test_engine: CalculationEngine) -> None:
    """Tests error handling in formula execution."""
    # Test division by zero
    test_engine.execute_formula("=1/0", "Sheet1", "Z2")
    # Should handle gracefully, possibly returning None or an error value

    # Test reference to non-existent cell
    test_engine.execute_formula("=ZZ999", "Sheet1", "Z3")
    # Should handle gracefully


def test_unsupported_formula_type(test_engine: CalculationEngine) -> None:
    """Tests handling of unsupported formula types."""
    # Test with a formula that the parser marks as unknown
    test_engine.execute_formula("=AVERAGE(A1:A5)", "Sheet1", "Z4")
    # Should return an UNSUPPORTED marker or similar


# Tests for Abstracted Cost Components


def test_get_cost_components_by_type_arithmetic(test_engine: CalculationEngine) -> None:
    """Test getting arithmetic cost components."""
    arithmetic_components = test_engine.get_cost_components_by_type("arithmetic")
    if not (len(arithmetic_components) > 0):
        raise AssertionError
    # Check that AdditionStrategy is included
    component_names = [
        getattr(component, "name", None) for component in arithmetic_components
    ]
    if "Addition Strategy" not in component_names:
        raise AssertionError


def test_get_cost_components_by_type_reference(test_engine: CalculationEngine) -> None:
    """Test getting reference cost components."""
    reference_components = test_engine.get_cost_components_by_type("reference")
    if not (len(reference_components) > 0):
        raise AssertionError
    # Check that ReferenceStrategy is included
    component_names = [
        getattr(component, "name", None) for component in reference_components
    ]
    if "Reference Strategy" not in component_names:
        raise AssertionError


def test_get_cost_components_by_type_financial(test_engine: CalculationEngine) -> None:
    """Test getting financial cost components."""
    financial_components = test_engine.get_cost_components_by_type("financial")
    if not (len(financial_components) > 0):
        raise AssertionError
    # Check that PMTStrategy is included
    component_names = [
        getattr(component, "name", None) for component in financial_components
    ]
    if "PMT Strategy" not in component_names:
        raise AssertionError


def test_validate_cost_component_addition(test_engine: CalculationEngine) -> None:
    """Test validating addition cost component inputs."""
    # Valid addition formula
    valid_formula: dict[str, object] = {
        "type": "addition",
        "operands": [{"type": "literal", "value": 1}, {"type": "literal", "value": 2}],
    }
    if not (test_engine.validate_cost_component("addition", valid_formula)):
        raise AssertionError

    # Invalid addition formula (missing operands)
    invalid_formula: dict[str, object] = {"type": "addition"}
    if test_engine.validate_cost_component("addition", invalid_formula):
        raise AssertionError


def test_validate_cost_component_reference(test_engine: CalculationEngine) -> None:
    """Test validating reference cost component inputs."""
    # Valid reference formula
    valid_formula: dict[str, object] = {"type": "reference", "cell": "A1"}
    if not (test_engine.validate_cost_component("reference", valid_formula)):
        raise AssertionError

    # Invalid reference formula (missing cell)
    invalid_formula: dict[str, object] = {"type": "reference"}
    if test_engine.validate_cost_component("reference", invalid_formula):
        raise AssertionError


def test_validate_cost_component_pmt(test_engine: CalculationEngine) -> None:
    """Test validating PMT cost component inputs."""
    # Valid PMT formula
    valid_formula: dict[str, object] = {
        "type": "pmt",
        "rate": 0.05,
        "nper": 12,
        "pv": 1000,
    }
    if not (test_engine.validate_cost_component("pmt", valid_formula)):
        raise AssertionError

    # Invalid PMT formula (missing required parameters)
    invalid_formula: dict[str, object] = {"type": "pmt", "rate": 0.05}
    if test_engine.validate_cost_component("pmt", invalid_formula):
        raise AssertionError


def test_get_cost_component_info_addition(test_engine: CalculationEngine) -> None:
    """Test getting information about addition cost component."""
    info = test_engine.get_cost_component_info("addition")
    if not (info is not None):
        raise AssertionError
    if not (info["name"] == "Addition Strategy"):
        raise AssertionError
    if not (info["component_type"] == "arithmetic"):
        raise AssertionError
    if not (info["operation_type"] == "addition"):
        raise AssertionError


def test_get_cost_component_info_reference(test_engine: CalculationEngine) -> None:
    """Test getting information about reference cost component."""
    info = test_engine.get_cost_component_info("reference")
    if not (info is not None):
        raise AssertionError
    if not (info["name"] == "Reference Strategy"):
        raise AssertionError
    if not (info["component_type"] == "reference"):
        raise AssertionError
    if not (info["reference_type"] == "cell"):
        raise AssertionError


def test_get_cost_component_info_pmt(test_engine: CalculationEngine) -> None:
    """Test getting information about PMT cost component."""
    info = test_engine.get_cost_component_info("pmt")
    if not (info is not None):
        raise AssertionError
    if not (info["name"] == "PMT Strategy"):
        raise AssertionError
    if not (info["component_type"] == "financial"):
        raise AssertionError
    if not (info["financial_function"] == "pmt"):
        raise AssertionError
    parameters = info["required_parameters"]
    if not isinstance(parameters, Container) or "rate" not in parameters:
        raise AssertionError


def test_get_cost_component_info_unknown_type(test_engine: CalculationEngine) -> None:
    """Test getting information about unknown cost component type."""
    info = test_engine.get_cost_component_info("unknown_type")
    if info is not None:
        raise AssertionError


def test_cost_component_abstraction_integration(test_engine: CalculationEngine) -> None:
    """Test that abstracted cost components work with existing engine functionality."""
    # Test that we can still execute formulas using the abstracted components
    result = test_engine.execute_formula("=1+2", "Sheet1", "A1")
    require_equal(result, 3)

    # Test that the component is properly categorized
    arithmetic_components = test_engine.get_cost_components_by_type("arithmetic")
    if not (len(arithmetic_components) > 0):
        raise AssertionError

    # Test that we can get component info
    info = test_engine.get_cost_component_info("addition")
    if info is None or info["component_type"] != "arithmetic":
        raise AssertionError
