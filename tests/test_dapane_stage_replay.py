# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check historical stage mappings and JSON assembly against the source workbook."""

from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from openpyxl import load_workbook

from genomics_microcosting import dapane_stage_replay as stages
from tests import checks

WORKBOOK = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
)
WORKBOOK_CACHE_TOLERANCE = Fraction(1, 10**12)


def _number(value: str | dict[str, str]) -> Fraction:
    if isinstance(value, str):
        return Fraction(value)
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _cost_by_use(request: dict[str, Any]) -> dict[str, Fraction]:
    quotes = {quote["id"]: quote for quote in request["quotes"]}
    costs: dict[str, Fraction] = {}
    for use in request["usage"]:
        quote = quotes[use["quote_id"]]
        costs[use["id"]] = (
            _number(use["quantity"])
            * _number(quote["amount"])
            / _number(quote["per_quantity"])
        )
    return costs


@pytest.fixture
def exact_direct_subtotal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the engine only while testing how overhead inputs are assembled."""

    def subtotal(request: dict[str, Any]) -> dict[str, object]:
        direct = sum(_cost_by_use(request).values(), Fraction())
        return {
            "totals": {
                "exact": {
                    "numerator": str(direct.numerator),
                    "denominator": str(direct.denominator),
                },
            },
        }

    monkeypatch.setattr(stages, "evaluate_native_request", subtotal)


def _assert_cache_parity(value: Fraction, sheet: str, cell: str) -> None:
    book = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        source = Fraction(str(book[sheet][cell].value))
    finally:
        book.close()
    checks.require(condition=abs(value - source) <= WORKBOOK_CACHE_TOLERANCE)


@pytest.mark.usefixtures("exact_direct_subtotal")
@pytest.mark.parametrize(
    ("pathway", "row", "line_count"),
    [
        ("Panel", 8, 51),
        ("EA-P", 23, 51),
        ("EA-T", 38, 58),
        ("WGA-P", 53, 46),
        ("WGA-T", 68, 46),
    ],
)
def test_library_preparation_follows_each_booked_pathway(
    pathway: str,
    row: int,
    line_count: int,
) -> None:
    """Exercise equipment, supplies, labour and the unrounded overhead base."""
    request = stages.historical_library_preparation_request(WORKBOOK, pathway)
    costs = _cost_by_use(request)
    checks.require_equal(len(costs), line_count)
    _assert_cache_parity(costs["stage-overhead"], "Summary Table", f"K{row}")
    _assert_cache_parity(sum(costs.values(), Fraction()), "Summary Table", f"N{row}")


@pytest.mark.usefixtures("exact_direct_subtotal")
@pytest.mark.parametrize(
    ("pathway", "labour_row", "equipment_row"),
    [
        ("Panel", 22, 78),
        ("EA-P", 280, 342),
        ("EA-T", 544, 611),
        ("WGA-P", 844, 907),
        ("WGA-T", 1090, 1155),
    ],
)
def test_qc_preserves_the_booked_equipment_and_labour_counts(
    pathway: str,
    labour_row: int,
    equipment_row: int,
) -> None:
    """Catch a blanket tripling of all costs for the WGA-T QC case."""
    costs = _cost_by_use(stages.historical_qc_full_request(WORKBOOK, pathway))
    checks.require_equal(len(costs), 11)
    _assert_cache_parity(costs["G32"], "Detailed Table", f"N{labour_row}")
    _assert_cache_parity(costs["equipment-U7"], "Detailed Table", f"N{equipment_row}")
    overhead = costs.pop("stage-overhead")
    checks.require_equal(overhead, Fraction("0.27") * sum(costs.values(), Fraction()))


@pytest.mark.parametrize(
    ("band", "cell"),
    [
        ("technician-midpoint", "AC3"),
        ("scientist-midpoint", "AC4"),
        ("scientist-lower", "AB4"),
    ],
)
def test_loaded_rate_includes_the_original_leave_expression(
    band: str,
    cell: str,
) -> None:
    """Keep the repeated base salary visible in the component ledger."""
    costs = _cost_by_use(stages.historical_loaded_labour_request(WORKBOOK, band))
    checks.require_equal(costs["base_salary"], costs["repeated_base_in_leave_formula"])
    _assert_cache_parity(sum(costs.values(), Fraction()), "Labour - Costs - VCGS", cell)


def test_unregistered_pathway_and_band_are_rejected() -> None:
    """Keep historically qualified identifiers explicit."""
    with pytest.raises(ValueError, match="Unknown preserved VCGS pathway"):
        stages.historical_qc_full_request(WORKBOOK, "invented-pathway")
    with pytest.raises(ValueError, match="Unknown preserved VCGS labour band"):
        stages.historical_loaded_labour_request(WORKBOOK, "invented-band")
