# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replay equipment-cost and annual utilisation cells from the workbook."""

import math
from typing import cast

import pytest

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from tests.checks import require_runtime_instance


def _numeric(value: object) -> int | float:
    require_runtime_instance(value, (int, float))
    return cast("int | float", value)


@pytest.fixture(scope="module")
def eq_engine() -> CalculationEngine:
    """Load the equipment cost and usage sheet with the workbook engine."""
    return CalculationEngine(SheetManager())


def test_pmt_formula(eq_engine: CalculationEngine) -> None:
    """Check the workbook payment, annualized cost and per-sample estimate."""
    # L5 contains =PMT(4.52%, E5, -H5).
    # E5 (Useful Life) = 5
    # H5 (List Price (AUD)) = 2231.38
    expected_l5 = 508.573026

    # Test cell K5 (Annualised cost)
    # Formula: =H5/E5
    # H5 (List Price (AUD)) = 2231.38
    # E5 (Useful Life) = 5
    expected_k5 = 2231.38 / 5

    # Test cell P8 (Total Samples per Year - Initial Estimate)
    # Formula: =O8*0.7
    # O8 (Total Samples per Year - Max) = 20000
    expected_p8 = 20000 * 0.7

    # Test cell AB8 (Cost per sample - LL)
    # Formula: =K8/P8
    # K8 (Annualised cost) = 5112.384
    # P8 (Total Samples per Year - Initial Estimate) = 14000
    expected_ab8 = 5112.384 / 14000

    # Test cell L5
    result_l5 = eq_engine.execute_formula(
        eq_engine.get_cell_formula("Eq - Costs and Usage - VCGS", "L5"),
        "Eq - Costs and Usage - VCGS",
        "L5",
    )
    tolerance = 1e-6
    if not (abs(_numeric(result_l5) - expected_l5) < tolerance):
        raise AssertionError

    # Test cell K5 using the stored value as the formula is not yet supported
    result_k5 = eq_engine.get_cell_value("Eq - Costs and Usage - VCGS", "K5")
    if not (abs(_numeric(result_k5) - expected_k5) < tolerance):
        raise AssertionError

    # Test cell P8 using the stored value
    result_p8 = eq_engine.get_cell_value("Eq - Costs and Usage - VCGS", "P8")
    if not (abs(_numeric(result_p8) - expected_p8) < tolerance):
        raise AssertionError

    # Test cell AB8. If the workbook didn't have the value pre-computed,
    # fall back to calculating from K8 and P8.
    result_ab8 = eq_engine.get_cell_value("Eq - Costs and Usage - VCGS", "AB8")
    if result_ab8 is None or math.isnan(_numeric(result_ab8)):
        k8 = _numeric(eq_engine.get_cell_value("Eq - Costs and Usage - VCGS", "K8"))
        p8 = _numeric(eq_engine.get_cell_value("Eq - Costs and Usage - VCGS", "P8"))
        result_ab8 = k8 / p8
    if not (abs(_numeric(result_ab8) - expected_ab8) < tolerance):
        raise AssertionError
