# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect a selected preserved source without publishing or repairing its data."""

from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, cast
from zipfile import ZipFile
lazy from collections.abc import Mapping
lazy from pathlib import Path

from defusedxml import ElementTree
from openpyxl import load_workbook

from genomics_microcosting.dapane_adapter import (
    SHEET,
    WORKBOOK_SHA256,
    evaluate_native_request,
)

EXPECTED = {
    "D22": (None, "30"),
    "E22": (None, "6"),
    "G22": ("=D22/E22", None),
    "D23": (None, "5"),
    "E23": (None, "6"),
    "G23": ("=D23/E23", None),
    "L22": ("='Labour - Costs - VCGS'!AC$3", None),
    "L23": ("='Labour - Costs - VCGS'!AC$3", None),
    "AB22": ("=$G22/60*L22", None),
    "AB23": ("=$G23/60*L23", None),
    "AB24": ("=SUM(AB22:AB23)", None),
}
GDNA_QC_EXPECTED = {
    "G32": ("=0.036*60", None),
    "G33": ("=0.036*60", None),
    "L32": ("='Labour - Costs - VCGS'!AC$3", None),
    "L33": ("='Labour - Costs - VCGS'!AC$3", None),
    "AB32": ("=$G32/60*L32", None),
    "AB33": ("=$G33/60*L33", None),
}
CONSUMABLES_SHEET = "Cons -  Costs and Util - VCGS"
GDNA_QC_CONSUMABLE_ROWS = range(13, 20)
GDNA_QC_CONSUMABLE_EXPECTED = {
    cell: (formula, None)
    for row in GDNA_QC_CONSUMABLE_ROWS
    for cell, formula in (
        (f"E{row}", None),
        (f"F{row}", None),
        (f"J{row}", f"=E{row}*F{row}"),
    )
}
MAX_WORKBOOK_BYTES = 32 * 1024 * 1024


def _sheet_path(archive: ZipFile, sheet: str) -> str:
    book = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {element.attrib["Id"]: element.attrib for element in relationships}
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    matches = [
        element
        for element in book.findall(".//{*}sheet")
        if element.attrib["name"] == sheet
    ]
    if len(matches) != 1:
        message = "Preserved source sheet is missing or ambiguous"
        raise ValueError(message)
    selected = targets[matches[0].attrib[rid]]
    target = selected["Target"]
    path = target.lstrip("/") if target.startswith("/xl/") else "xl/" + target
    if selected.get("TargetMode") == "External" or ".." in PurePosixPath(path).parts:
        message = "Workbook sheet relationship is not a local archive member"
        raise ValueError(message)
    return path


def _verified_payload(path: Path) -> bytes:
    if path.stat().st_size > MAX_WORKBOOK_BYTES:
        message = "Workbook exceeds the selected source bound"
        raise ValueError(message)
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != WORKBOOK_SHA256:
        message = "Workbook hash differs from the preserved v15 source"
        raise ValueError(message)
    return payload


def _inspect_cells(
    payload: bytes,
    sheet: str,
    expected: Mapping[str, tuple[str | None, str | None]],
    *,
    rows: tuple[int, int],
) -> dict[str, dict[str, str | None]]:
    """Read selected workbook formulas and caches without recalculation."""
    with ZipFile(BytesIO(payload)) as archive:
        worksheet = ElementTree.fromstring(archive.read(_sheet_path(archive, sheet)))
    # Excel shared-formula records can omit repeated formula text. The existing
    # reader expands those references mechanically; it does not recalculate them.
    book = load_workbook(BytesIO(payload), read_only=True, data_only=False)
    try:
        formulas = {
            cell.coordinate: str(cell.value) if cell.data_type == "f" else None
            for row in book[sheet].iter_rows(
                min_row=rows[0],
                max_row=rows[1],
                min_col=4,
                max_col=28,
            )
            for cell in row
            if getattr(cell, "coordinate", "") in expected
        }
    finally:
        book.close()
    selected: dict[str, dict[str, str | None]] = {}
    for cell in worksheet.findall(".//{*}c"):
        coordinate = cell.attrib["r"]
        if coordinate not in expected:
            continue
        cached = cell.find("{*}v")
        selected[coordinate] = {
            "formula": formulas[coordinate],
            "cached": None if cached is None else cached.text,
        }
    if set(selected) != set(expected):
        message = "Selected source mapping is incomplete"
        raise ValueError(message)
    for coordinate, (formula, value) in expected.items():
        observed = selected[coordinate]
        if (
            observed["formula"] != formula
            or observed["cached"] is None
            or (value is not None and observed["cached"] != value)
        ):
            message = f"Source mapping precondition differs at {coordinate}"
            raise ValueError(message)
    return selected


def _require_shared_rate(
    cells: dict[str, dict[str, str | None]],
    first: str,
    second: str,
) -> None:
    if cells[first]["cached"] != cells[second]["cached"]:
        message = "Historical selected roles no longer share the same source rate"
        raise ValueError(message)


def inspect_manual_extraction_workbook(path: Path) -> dict[str, Any]:
    """Return raw selected extraction cells from the hash-verified workbook."""
    cells = _inspect_cells(_verified_payload(path), SHEET, EXPECTED, rows=(22, 24))
    _require_shared_rate(cells, "L22", "L23")
    return {
        "workbook_sha256": WORKBOOK_SHA256,
        "sheet": SHEET,
        "mapping_version": "manual-dna-extraction-v1",
        "cells": cells,
        "repairs_applied": [],
        "scope": "selected_manual_extraction_cells_only",
    }


def inspect_gdna_qc_workbook(path: Path) -> dict[str, Any]:
    """Return the hash-verified TapeStation QC labour and consumable cells."""
    payload = _verified_payload(path)
    labour = _inspect_cells(payload, SHEET, GDNA_QC_EXPECTED, rows=(32, 33))
    _require_shared_rate(labour, "L32", "L33")
    consumables = _inspect_cells(
        payload,
        CONSUMABLES_SHEET,
        GDNA_QC_CONSUMABLE_EXPECTED,
        rows=(GDNA_QC_CONSUMABLE_ROWS.start, GDNA_QC_CONSUMABLE_ROWS.stop - 1),
    )
    return {
        "workbook_sha256": WORKBOOK_SHA256,
        "mapping_version": "tapestation-gdna-qc-direct-cost-v1",
        "sheets": {SHEET: labour, CONSUMABLES_SHEET: consumables},
        "repairs_applied": [],
        "scope": "selected_tapestation_gdna_qc_labour_and_consumables",
    }


def historical_manual_extraction_request(
    path: Path,
    *,
    run_id: str = "historical-manual-dna-extraction",
) -> dict[str, Any]:
    """Replay the selected historical per-specimen arithmetic in Rust.

    The date/year identify this workbook snapshot replay, not a newly validated
    employment period or economic price basis. The legacy rate is opaque:
    on-cost decomposition and current employment applicability remain unknown.
    """
    return _historical_labour_request(
        run_id=run_id,
        source_id="manual-extraction-v15",
        rate_cells=("L22", "L23"),
        cells=inspect_manual_extraction_workbook(path)["cells"],
        exposures=(("G22", "5"), ("G23", {"numerator": "5", "denominator": "6"})),
    )


def historical_gdna_qc_request(
    path: Path,
    *,
    run_id: str = "historical-tapestation-gdna-qc",
) -> dict[str, Any]:
    """Replay the selected historical TapeStation QC labour and consumables."""
    sheets = inspect_gdna_qc_workbook(path)["sheets"]
    request = _historical_labour_request(
        run_id=run_id,
        source_id="tapestation-gdna-qc-v15",
        rate_cells=("L32", "L33"),
        cells=sheets[SHEET],
        # Both verified source formulas use 0.036 hours, exactly 2.16 minutes.
        exposures=(("G32", "2.16"), ("G33", "2.16")),
    )
    labour_quote = request["quotes"][0]
    consumables = sheets[CONSUMABLES_SHEET]
    for row in GDNA_QC_CONSUMABLE_ROWS:
        price_cell, use_cell = f"E{row}", f"F{row}"
        resource = f"historical-qc-consumable-{row}"
        quote = {
            **labour_quote,
            "id": resource,
            "target": resource,
            "unit": "item",
            "amount": consumables[price_cell]["cached"],
            "per_quantity": "1",
            "components": ["legacy_consumable"],
            "source": {
                **labour_quote["source"],
                "id": "tapestation-gdna-qc-consumables-v15",
                "locator": f"{CONSUMABLES_SHEET}!{price_cell}",
            },
        }
        request["quotes"].append(quote)
        request["usage"].append(
            _historical_use(
                use_cell,
                consumables[use_cell]["cached"],
                quote,
                locator=f"{CONSUMABLES_SHEET}!{use_cell}",
            ),
        )
    return request


def _historical_labour_request(
    *,
    run_id: str,
    source_id: str,
    rate_cells: tuple[str, str],
    cells: dict[str, dict[str, str | None]],
    exposures: tuple[tuple[str, str | dict[str, str]], ...],
) -> dict[str, Any]:
    source = {
        "id": source_id,
        "version": "preserved-v15",
        "evidence": "derived",
        "access": "public",
        "validation": "unvalidated",
        "content_digest": "sha256:" + WORKBOOK_SHA256,
        "locator": SHEET
        + "!"
        + ",".join(rate_cells)
        + "; historical cached loaded rate",
    }
    quote = {
        "id": "historical-loaded-labour",
        "kind": "resource_use",
        "target": "historical-LT",
        "unit": "minute",
        "amount": cells[rate_cells[0]]["cached"],
        "per_quantity": "60",
        "currency": "AUD",
        "price_year": 2023,
        "basis": "financial_cost",
        "components": ["legacy_loaded_labour_scope_unresolved"],
        "valid_from": "2023-09-02",
        "valid_to": "2023-09-03",
        "known_from": "2023-09-02",
        "source": source,
    }
    return {
        "schema_version": "0.1",
        "run_id": run_id,
        "knowledge_cutoff": "2023-09-02",
        "policy": {
            "id": "historical-cache-replay",
            "version": "1",
            "currency": "AUD",
            "price_year": 2023,
            "perspective": "historical_workbook_snapshot",
            "basis": "financial_cost",
            "rounding": {"scale": 2, "mode": "half_even"},
        },
        "quotes": [quote],
        "usage": [
            _historical_use(cell, quantity, quote, locator=f"{SHEET}!{cell}")
            for cell, quantity in exposures
        ],
    }


def _historical_use(
    cell: str,
    quantity: str | dict[str, str],
    quote: dict[str, Any],
    *,
    locator: str,
) -> dict[str, Any]:
    return {
        "id": cell,
        "use_id": cell,
        "kind": "resource_use",
        "target": quote["target"],
        "unit": quote["unit"],
        "quantity": quantity,
        "service_date": quote["valid_from"],
        "quote_id": quote["id"],
        "source": {**quote["source"], "locator": locator},
    }


def _current_quote(current_report: dict[str, Any]) -> dict[str, Any]:
    current_quotes = current_report.get("quote_snapshots")
    message = "Comparison requires a complete single-quotation current report"
    if current_report.get("status") != "complete" or not isinstance(
        current_quotes,
        list,
    ):
        raise ValueError(message)
    quotes = cast("list[object]", current_quotes)
    if len(quotes) != 1 or not isinstance(quotes[0], dict):
        raise ValueError(message)
    quote = cast("dict[str, Any]", quotes[0])
    if not {"amount", "components"}.issubset(quote):
        raise ValueError(message)
    return quote


def compare_manual_extraction_workbook(
    path: Path,
    current_report: dict[str, Any],
) -> dict[str, Any]:
    """Keep source extraction, native replay and scenario changes distinguishable.

    The current report is caller-supplied. This comparison does not requalify its
    input declarations, calculate deltas in Python or correct original formulas.
    """
    current_quote = _current_quote(current_report)
    inspection = inspect_manual_extraction_workbook(path)
    historical = evaluate_native_request(historical_manual_extraction_request(path))
    previous_quote = historical["quote_snapshots"][0]
    return {
        "mechanical_extraction": inspection,
        "historical_replay": historical,
        "current_revaluation": current_report,
        "classification": {
            "formula_repairs_applied": [],
            "historical_rounding": "source_line_half_even_2dp",
            "changed_rate_or_components": (
                previous_quote["amount"] != current_quote["amount"]
                or previous_quote["components"] != current_quote["components"]
            ),
            "allocation_scope": "actual_batch_members",
            "scientific_validation": False,
            "interpretation": [
                "Raw Excel caches retain their original floating-point representation",
                "Rust replay uses exact 5 and 5/6 minute exposures with line rounding",
                "Current scenario selects a dated quote and explicit components",
                "All declared batch attempts retain their incurred labour",
                "No formula repair or whole-workbook qualification is implied",
            ],
        },
    }
