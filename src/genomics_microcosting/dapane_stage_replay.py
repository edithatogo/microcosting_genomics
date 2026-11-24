# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replay selected costing formulas from the preserved VCGS workbook."""

import re
from fractions import Fraction
from typing import Any, NamedTuple
lazy from pathlib import Path

from genomics_microcosting.dapane_adapter import (
    SHEET,
    WORKBOOK_SHA256,
    evaluate_native_request,
)
from genomics_microcosting.dapane_workbook import (
    CONSUMABLES_SHEET,
    historical_gdna_qc_request,
    historical_use,
    new_historical_request,
    read_workbook_cells,
    verified_workbook_payload,
)

SUMMARY = "Summary Table"
DETAIL = "Detailed Table"
EQUIPMENT = "Eq - Usage - VCGS"
LABOUR_RATES = "Labour - Costs - VCGS"

type Cells = dict[str, dict[str, str | None]]
type Exact = str | dict[str, str]


class _Pathway(NamedTuple):
    summary: int
    labour: int
    consumables: int
    equipment: int
    equipment_rows: tuple[int, int]
    qc_equipment: int
    qc_labour: int
    qc_consumables: int
    tests: int = 1


PATHWAYS = {
    "Panel": _Pathway(8, 42, 166, 88, (13, 17), 78, 22, 109),
    "EA-P": _Pathway(23, 300, 430, 352, (13, 17), 342, 280, 373),
    "EA-T": _Pathway(38, 565, 715, 622, (13, 17), 611, 544, 649, 3),
    "WGA-P": _Pathway(53, 863, 990, 917, (13, 17), 907, 844, 938),
    "WGA-T": _Pathway(68, 1109, 1239, 1166, (21, 25), 1155, 1090, 1187, 3),
}

LABOUR_BANDS = {
    "technician-midpoint": (3, "W", "Z", "AC"),
    "scientist-midpoint": (4, "W", "Z", "AC"),
    "scientist-lower": (4, "V", "Y", "AB"),
}


class _Price(NamedTuple):
    amount: Fraction
    quantity: Fraction
    denominator: Fraction = Fraction(1)


def _fraction(value: Exact) -> Fraction:
    if isinstance(value, str):
        return Fraction(value)
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _exact(value: Fraction) -> Exact:
    if value.denominator == 1:
        return str(value.numerator)
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _number(cells: Cells, coordinate: str) -> Fraction:
    value = cells.get(coordinate, {}).get("cached")
    if value is None:
        message = f"Preserved workbook value is missing at {coordinate}"
        raise ValueError(message)
    return Fraction(value)


def _formula(cells: Cells, coordinate: str) -> str:
    return (cells.get(coordinate, {}).get("formula") or "").replace("$", "")


def _require_formula(cells: Cells, coordinate: str, formula: str) -> None:
    if _formula(cells, coordinate) != formula:
        message = f"Preserved workbook formula differs at {coordinate}"
        raise ValueError(message)


def _cells(
    payload: bytes,
    sheet: str,
    rows: tuple[int, int],
    columns: tuple[str, ...],
) -> Cells:
    coordinates = {
        f"{column}{row}" for row in range(rows[0], rows[1] + 1) for column in columns
    }
    return read_workbook_cells(payload, sheet, coordinates, rows=rows)


def _append_cost(
    request: dict[str, Any],
    use_id: str,
    component: str,
    price: _Price,
    locator: str,
) -> None:
    source = {
        "id": "vcgs-workbook-v15",
        "version": "preserved-v15",
        "evidence": "derived",
        "access": "public",
        "validation": "unvalidated",
        "content_digest": f"sha256:{WORKBOOK_SHA256}",
        "locator": locator,
    }
    quote = {
        "id": use_id,
        "kind": "resource_use",
        "target": use_id,
        "unit": "item",
        "amount": _exact(price.amount),
        "per_quantity": _exact(price.denominator),
        "currency": "AUD",
        "price_year": 2023,
        "basis": "financial_cost",
        "components": [component],
        "valid_from": "2023-09-02",
        "valid_to": "2023-09-03",
        "known_from": "2023-09-02",
        "source": source,
    }
    request["quotes"].append(quote)
    request["usage"].append(
        historical_use(use_id, _exact(price.quantity), quote, locator=locator),
    )


def _scenario(scenario: str) -> _Pathway:
    if scenario not in PATHWAYS:
        message = f"Unknown preserved VCGS pathway: {scenario}"
        raise ValueError(message)
    return PATHWAYS[scenario]


def _detail_block(payload: bytes, subtotal: int) -> Cells:
    total = _cells(payload, DETAIL, (subtotal, subtotal), ("N",))
    formula = _formula(total, f"N{subtotal}")
    match = re.fullmatch(r"=SUM\(N(\d+):N(\d+)\)", formula)
    if match is None:
        message = f"Unexpected detail subtotal at {DETAIL}!N{subtotal}"
        raise ValueError(message)
    start, end = (int(item) for item in match.groups())
    return _cells(payload, DETAIL, (start, end), ("F", "J", "N"))


def _equipment(
    payload: bytes,
    request: dict[str, Any],
    rows: tuple[int, int],
    tests: int,
) -> None:
    cells = _cells(payload, EQUIPMENT, rows, ("E", "Q", "U"))
    for row in range(rows[0], rows[1] + 1):
        _require_formula(cells, f"U{row}", f"=(1/E{row})*Q{row}")
        _append_cost(
            request,
            f"equipment-U{row}",
            "equipment",
            _Price(
                _number(cells, f"Q{row}"),
                Fraction(tests),
                _number(cells, f"E{row}"),
            ),
            f"{EQUIPMENT}!Q{row}/E{row}, booked amount U{row}",
        )


def _overhead(
    payload: bytes,
    request: dict[str, Any],
    summary_row: int,
    *,
    qc_only: bool,
) -> None:
    cells = _cells(payload, SUMMARY, (summary_row, summary_row), ("K",))
    _require_formula(
        cells,
        f"K{summary_row}",
        f"=SUM(B{summary_row},E{summary_row},H{summary_row})*0.27",
    )
    direct = evaluate_native_request(request)["totals"]["exact"]
    scope = "QC share of extraction" if qc_only else "library preparation"
    _append_cost(
        request,
        "stage-overhead",
        "overhead",
        _Price(Fraction("0.27"), _fraction(direct)),
        f"{SUMMARY}!K{summary_row}; {scope}; rate applied to exact direct costs",
    )


def _qc_booked_uses(payload: bytes, request: dict[str, Any], pathway: _Pathway) -> None:
    first = pathway.qc_labour
    labour = _cells(payload, DETAIL, (first, first + 1), ("N",))
    first_con = pathway.qc_consumables
    consumables = _cells(payload, DETAIL, (first_con, first_con + 6), ("F", "J", "N"))
    for offset, use in enumerate(request["usage"][:2]):
        row, original = first + offset, 32 + offset
        base = f"='{SHEET}'!AB{original}"
        booked = _formula(labour, f"N{row}")
        if booked not in (base, base + "*3"):
            message = f"Unexpected QC labour booking at {DETAIL}!N{row}"
            raise ValueError(message)
        uses = 3 if booked.endswith("*3") else 1
        use["quantity"] = _exact(_fraction(use["quantity"]) * uses)
        use["source"]["locator"] += f"; booked at {DETAIL}!N{row}"
    multiplier = "" if pathway.tests == 1 else "*3"
    for offset, use in enumerate(request["usage"][2:]):
        row, original = first_con + offset, 13 + offset
        _require_formula(
            consumables,
            f"F{row}",
            f"='{CONSUMABLES_SHEET}'!F{original}{multiplier}",
        )
        _require_formula(consumables, f"J{row}", f"='{CONSUMABLES_SHEET}'!E{original}")
        _require_formula(consumables, f"N{row}", f"=F{row}*J{row}")
        use["quantity"] = _exact(_fraction(use["quantity"]) * pathway.tests)
        use["source"]["locator"] += f"; booked at {DETAIL}!N{row}"


def historical_qc_full_request(path: Path, scenario: str = "Panel") -> dict[str, Any]:
    """Replay QC direct costs, its booked TapeStation charge and attributed overhead."""
    pathway = _scenario(scenario)
    payload = verified_workbook_payload(path)
    row = pathway.qc_equipment
    detail = _cells(payload, DETAIL, (row, row), ("N",))
    multiplier = "" if pathway.tests == 1 else "*3"
    _require_formula(detail, f"N{row}", f"='{EQUIPMENT}'!U7{multiplier}")
    request = historical_gdna_qc_request(
        path,
        run_id=f"historical-gdna-qc-{scenario.lower()}",
    )
    _qc_booked_uses(payload, request, pathway)
    _equipment(payload, request, (7, 7), pathway.tests)
    _overhead(payload, request, pathway.summary - 1, qc_only=True)
    return request


def _library_consumables(
    payload: bytes,
    request: dict[str, Any],
    subtotal: int,
) -> None:
    cells = _detail_block(payload, subtotal)
    for coordinate, cell in cells.items():
        if not coordinate.startswith("N") or cell["cached"] is None:
            continue
        row = coordinate[1:]
        _require_formula(cells, coordinate, f"=F{row}*J{row}")
        _append_cost(
            request,
            f"consumable-{coordinate}",
            "consumables",
            _Price(_number(cells, f"J{row}"), _number(cells, f"F{row}")),
            f"{DETAIL}!F{row},J{row}; output {coordinate}",
        )


def _library_labour(payload: bytes, request: dict[str, Any], subtotal: int) -> None:
    detail = _detail_block(payload, subtotal)
    cells = _cells(payload, SHEET, (37, 56), ("G", "K", "L", "AA", "AB"))
    for coordinate, cell in detail.items():
        if not coordinate.startswith("N") or cell["cached"] is None:
            continue
        formula = _formula(detail, coordinate)
        match = re.fullmatch(rf"='{SHEET}'!(AA|AB)(\d+)(\*3)?", formula)
        if match is None:
            message = f"Unexpected labour value at {DETAIL}!{coordinate}"
            raise ValueError(message)
        payment, row, multiplier = match.groups()
        rate = "K" if payment == "AA" else "L"
        _require_formula(cells, f"{payment}{row}", f"=G{row}/60*{rate}{row}")
        _append_cost(
            request,
            f"labour-{coordinate}",
            "loaded_labour",
            _Price(
                _number(cells, f"{rate}{row}"),
                _number(cells, f"G{row}") * (3 if multiplier else 1),
                Fraction(60),
            ),
            f"{SHEET}!G{row},{rate}{row},{payment}{row}; {DETAIL}!{coordinate}",
        )


def historical_library_preparation_request(path: Path, scenario: str) -> dict[str, Any]:
    """Replay one original library-preparation pathway and its 27% overhead."""
    pathway = _scenario(scenario)
    payload = verified_workbook_payload(path)
    row = pathway.summary
    summary = _cells(payload, SUMMARY, (row, row), ("B", "E", "H"))
    for column, subtotal in (
        ("B", pathway.equipment),
        ("E", pathway.consumables),
        ("H", pathway.labour),
    ):
        _require_formula(summary, f"{column}{row}", f"='{DETAIL}'!N{subtotal}")
    last = pathway.equipment_rows[-1] + 1
    multiplier = "" if pathway.tests == 1 else "*3"
    eq = _cells(payload, DETAIL, (pathway.equipment, pathway.equipment), ("N",))
    _require_formula(eq, f"N{pathway.equipment}", f"='{EQUIPMENT}'!U{last}{multiplier}")
    request = new_historical_request(
        f"historical-library-preparation-{scenario.lower()}",
    )
    _equipment(payload, request, pathway.equipment_rows, pathway.tests)
    _library_consumables(payload, request, pathway.consumables)
    _library_labour(payload, request, pathway.labour)
    _overhead(payload, request, row, qc_only=False)
    return request


def historical_loaded_labour_request(path: Path, band: str) -> dict[str, Any]:
    """Rebuild a recorded hourly rate with explicit original salary components."""
    if band not in LABOUR_BANDS:
        message = f"Unknown preserved VCGS labour band: {band}"
        raise ValueError(message)
    row, base, annual, hourly = LABOUR_BANDS[band]
    payload = verified_workbook_payload(path)
    cells = _cells(
        payload,
        LABOUR_RATES,
        (row, row),
        ("J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", base, annual, hourly),
    )
    _require_formula(cells, f"{hourly}{row}", f"={annual}{row}/52/K{row}")
    b = f"{base}{row}"
    products = "+".join(
        f"({b}*{column}{row})" for column in ("J", "M", "N", "O", "P", "Q")
    )
    _require_formula(
        cells,
        f"{annual}{row}",
        f"=({b}+{products}+(R{row})+({b}*((52+S{row})/52))*(1+T{row}))*1/L{row}",
    )
    salary = _number(cells, b)
    hours = 52 * _number(cells, f"K{row}") * _number(cells, f"L{row}")
    leave = _number(cells, f"S{row}") / 52
    leave_loading = _number(cells, f"T{row}")
    request = new_historical_request(f"historical-loaded-labour-{band}")
    components = (
        ("base_salary", Fraction(1), base),
        ("superannuation", _number(cells, f"J{row}"), "J"),
        ("average_penalties", _number(cells, f"M{row}"), "M"),
        ("public_holiday_penalty", _number(cells, f"N{row}"), "N"),
        ("private_practice_loading", _number(cells, f"O{row}"), "O"),
        ("attraction_retention_allowance", _number(cells, f"P{row}"), "P"),
        ("sick_leave", _number(cells, f"Q{row}"), "Q"),
        ("repeated_base_in_leave_formula", Fraction(1), annual),
        ("annual_leave_weeks", leave, "S"),
        ("annual_leave_loading", (1 + leave) * leave_loading, "T"),
    )
    for component, factor, column in components:
        _append_cost(
            request,
            component,
            component,
            _Price(salary, factor, hours),
            f"{LABOUR_RATES}!{b},{column}{row}; rate {hourly}{row}",
        )
    _append_cost(
        request,
        "professional_development",
        "professional_development",
        _Price(_number(cells, f"R{row}"), Fraction(1), hours),
        f"{LABOUR_RATES}!R{row}; rate {hourly}{row}",
    )
    return request
