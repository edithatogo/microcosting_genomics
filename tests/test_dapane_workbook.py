# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise mechanical workbook boundaries using only hand-authored toy data."""

from hashlib import sha256
from io import BytesIO
from typing import Any
from zipfile import ZipFile
lazy from pathlib import Path

import pytest
from openpyxl import Workbook

from genomics_microcosting import dapane_workbook
from tests import checks

SHEET_MEMBER = "xl/worksheets/sheet1.xml"
CONSUMABLES_MEMBER = "xl/worksheets/sheet2.xml"
SYNTHETIC_SHEET_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<dimension ref="D22:AB33"/><sheetData><row r="22">'
    '<c r="D22"><v>30</v></c><c r="E22"><v>6</v></c>'
    '<c r="G22"><f>D22/E22</f><v>5</v></c>'
    '<c r="L22"><f t="shared" si="0" ref="L22:L23">'
    "'Labour - Costs - VCGS'!AC$3</f><v>12.30</v></c>"
    '<c r="AB22"><f>$G22/60*L22</f><v>1.025</v></c></row>'
    '<row r="23"><c r="D23"><v>5</v></c><c r="E23"><v>6</v></c>'
    '<c r="G23"><f>D23/E23</f><v>0.8333333333333334</v></c>'
    '<c r="L23"><f t="shared" si="0"/><v>12.30</v></c>'
    '<c r="AB23"><f>$G23/60*L23</f><v>0.17083333333333334</v></c></row>'
    '<row r="24"><c r="AB24"><f>SUM(AB22:AB23)</f>'
    "<v>1.1958333333333333</v></c></row>"
    '<row r="32"><c r="G32"><f>0.036*60</f><v>2.1599999999999997</v></c>'
    "<c r='L32'><f>'Labour - Costs - VCGS'!AC$3</f><v>12.30</v></c>"
    '<c r="AB32"><f>$G32/60*L32</f><v>0.4428</v></c></row>'
    '<row r="33"><c r="G33"><f>0.036*60</f><v>2.1599999999999997</v></c>'
    "<c r='L33'><f>'Labour - Costs - VCGS'!AC$3</f><v>12.30</v></c>"
    '<c r="AB33"><f>$G33/60*L33</f><v>0.4428</v></c></row>'
    "</sheetData></worksheet>"
)


SYNTHETIC_CONSUMABLES_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<dimension ref="E13:J19"/><sheetData>'
    + "".join(
        f'<row r="{row}"><c r="E{row}"><v>2.30</v></c>'
        f'<c r="F{row}"><v>0.5</v></c>'
        f'<c r="J{row}"><f>E{row}*F{row}</f><v>1.15</v></c></row>'
        for row in range(13, 20)
    )
    + "</sheetData></worksheet>"
)


def replace_member(path: Path, member: str, replacement: bytes) -> None:
    """Rewrite one member of a disposable synthetic archive, never a real source."""
    with ZipFile(path) as archive:
        members = [(info, archive.read(info.filename)) for info in archive.infolist()]
    checks.require(condition=any(info.filename == member for info, _ in members))
    with ZipFile(path, "w") as archive:
        for info, payload in members:
            archive.writestr(
                info,
                replacement if info.filename == member else payload,
            )


def pin_synthetic(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Open the mechanical path only within this test's temporary source identity."""
    monkeypatch.setattr(
        dapane_workbook,
        "WORKBOOK_SHA256",
        sha256(path.read_bytes()).hexdigest(),
    )


@pytest.fixture
def synthetic_workbook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create public toy cells without copying any preserved workbook material."""
    book = Workbook()
    book.create_sheet("Labour - Usage - VCGS", 0)
    book.create_sheet("Cons -  Costs and Util - VCGS", 1)
    del book["Sheet"]
    buffer = BytesIO()
    book.save(buffer)
    book.close()
    path = tmp_path / "synthetic.xlsx"
    path.write_bytes(buffer.getvalue())
    replace_member(path, SHEET_MEMBER, SYNTHETIC_SHEET_XML.encode())
    replace_member(path, CONSUMABLES_MEMBER, SYNTHETIC_CONSUMABLES_XML.encode())
    pin_synthetic(path, monkeypatch)
    return path


def test_shared_formula_expansion_preserves_raw_caches_and_source(
    synthetic_workbook: Path,
) -> None:
    """Expand a shared formula mechanically without rewriting source or caches."""
    before = synthetic_workbook.read_bytes()
    inspection = dapane_workbook.inspect_manual_extraction_workbook(
        synthetic_workbook,
    )
    checks.require_equal(inspection["workbook_sha256"], sha256(before).hexdigest())
    checks.require_equal(len(inspection["cells"]), 11)
    checks.require_equal(
        inspection["cells"]["L23"],
        {"formula": "='Labour - Costs - VCGS'!AC$3", "cached": "12.30"},
    )
    checks.require_equal(
        inspection["cells"]["G23"]["cached"],
        "0.8333333333333334",
    )
    checks.require_equal(inspection["repairs_applied"], [])
    checks.require_equal(synthetic_workbook.read_bytes(), before)


def test_historical_request_preserves_exact_exposure_and_opaque_components(
    synthetic_workbook: Path,
) -> None:
    """The request uses exact source exposures without dividing cached decimals."""
    request = dapane_workbook.historical_manual_extraction_request(
        synthetic_workbook,
        run_id="synthetic-historical-transport",
    )
    checks.require_equal(request["run_id"], "synthetic-historical-transport")
    checks.require_equal(
        [line["quantity"] for line in request["usage"]],
        ["5", {"numerator": "5", "denominator": "6"}],
    )
    checks.require_equal(request["quotes"][0]["amount"], "12.30")
    checks.require_equal(request["quotes"][0]["per_quantity"], "60")
    checks.require_equal(
        request["quotes"][0]["components"],
        ["legacy_loaded_labour_scope_unresolved"],
    )
    checks.require_equal(
        request["quotes"][0]["source"]["content_digest"],
        "sha256:" + sha256(synthetic_workbook.read_bytes()).hexdigest(),
    )


def test_gdna_qc_request_maps_labour_and_seven_consumables(
    synthetic_workbook: Path,
) -> None:
    """Retain binary caches as evidence and use the verified formula's exact time."""
    inspection = dapane_workbook.inspect_gdna_qc_workbook(synthetic_workbook)
    checks.require_equal(
        inspection["sheets"]["Labour - Usage - VCGS"]["G32"],
        {"formula": "=0.036*60", "cached": "2.1599999999999997"},
    )
    request = dapane_workbook.historical_gdna_qc_request(synthetic_workbook)
    checks.require_equal(
        [(line["id"], line["quantity"]) for line in request["usage"]],
        [("G32", "2.16"), ("G33", "2.16")]
        + [(f"F{row}", "0.5") for row in range(13, 20)],
    )
    checks.require_equal(request["quotes"][0]["amount"], "12.30")
    checks.require_equal(request["quotes"][0]["per_quantity"], "60")
    checks.require_equal(
        request["quotes"][0]["source"]["locator"],
        "Labour - Usage - VCGS!L32,L33; historical cached loaded rate",
    )

    checks.require_equal(
        [quote["amount"] for quote in request["quotes"][1:]],
        ["2.30"] * 7,
    )
    checks.require_equal(
        [quote["unit"] for quote in request["quotes"][1:]],
        ["item"] * 7,
    )


@pytest.mark.parametrize(
    ("member", "change", "coordinate"),
    [
        (SHEET_MEMBER, ("0.036*60", "0.04*60"), "G32"),
        (CONSUMABLES_MEMBER, ("E19*F19", "E19*F18"), "J19"),
    ],
)
def test_gdna_qc_rejects_changed_source_formula(
    synthetic_workbook: Path,
    monkeypatch: pytest.MonkeyPatch,
    member: str,
    change: tuple[str, str],
    coordinate: str,
) -> None:
    """Reject a changed source formula even if the workbook gets a new digest."""
    sources = {
        SHEET_MEMBER: SYNTHETIC_SHEET_XML,
        CONSUMABLES_MEMBER: SYNTHETIC_CONSUMABLES_XML,
    }
    before, after = change
    changed = sources[member].replace(before, after, 1)
    replace_member(synthetic_workbook, member, changed.encode())
    pin_synthetic(synthetic_workbook, monkeypatch)
    with pytest.raises(ValueError, match=f"at {coordinate}"):
        dapane_workbook.historical_gdna_qc_request(synthetic_workbook)


@pytest.mark.parametrize("change", ["unchanged", "rate", "components"])
def test_comparison_keeps_replay_current_scenario_and_classification_separate(
    synthetic_workbook: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    """A replay sentinel proves transport and classification, never valuation."""
    before = synthetic_workbook.read_bytes()
    captured: list[dict[str, Any]] = []
    historical: dict[str, Any] = {
        "status": "complete",
        "synthetic_sentinel": "not a numerical result",
        "quote_snapshots": [
            {
                "amount": "12.30",
                "components": ["legacy_loaded_labour_scope_unresolved"],
            },
        ],
    }

    def native_spy(request: dict[str, Any]) -> dict[str, Any]:
        captured.append(request)
        return historical

    monkeypatch.setattr(dapane_workbook, "evaluate_native_request", native_spy)
    current: dict[str, Any] = {
        "status": "complete",
        "quote_snapshots": [
            {
                "amount": "99.99" if change == "rate" else "12.30",
                "components": ["synthetic_base_only"]
                if change == "components"
                else ["legacy_loaded_labour_scope_unresolved"],
            },
        ],
    }
    result = dapane_workbook.compare_manual_extraction_workbook(
        synthetic_workbook,
        current,
    )
    checks.require(condition=result["historical_replay"] is historical)
    checks.require(condition=result["current_revaluation"] is current)
    checks.require_equal(
        result["classification"]["changed_rate_or_components"],
        change != "unchanged",
    )
    checks.require_equal(result["classification"]["formula_repairs_applied"], [])
    checks.require(
        condition=result["classification"]["scientific_validation"] is False,
    )
    checks.require_equal(
        [line["quantity"] for line in captured[0]["usage"]],
        ["5", {"numerator": "5", "denominator": "6"}],
    )
    checks.require_equal(synthetic_workbook.read_bytes(), before)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("<v>30</v>", "<v>31</v>", "precondition"),
        ("<v>0.8333333333333334</v>", "", "precondition"),
        ("$G22/60*L22", "$G22/60*L23", "precondition"),
        (
            '<c r="AB24"><f>SUM(AB22:AB23)</f><v>1.1958333333333333</v></c>',
            "",
            "incomplete",
        ),
        (
            '<c r="L23"><f t="shared" si="0"/><v>12.30</v></c>',
            '<c r="L23"><f t="shared" si="0"/><v>13.30</v></c>',
            "same source rate",
        ),
    ],
)
def test_rehashed_synthetic_mapping_changes_still_fail_preconditions(
    synthetic_workbook: Path,
    monkeypatch: pytest.MonkeyPatch,
    old: str,
    new: str,
    message: str,
) -> None:
    """Identity admission does not waive source formulas, caches or cohort checks."""
    changed = SYNTHETIC_SHEET_XML.replace(old, new)
    checks.require(condition=changed != SYNTHETIC_SHEET_XML)
    replace_member(synthetic_workbook, SHEET_MEMBER, changed.encode())
    pin_synthetic(synthetic_workbook, monkeypatch)
    with pytest.raises(ValueError, match=message):
        dapane_workbook.inspect_manual_extraction_workbook(synthetic_workbook)


@pytest.mark.parametrize("target", ["../outside.xml", "https://example.org/toy"])
def test_nonlocal_sheet_relationships_are_rejected(
    synthetic_workbook: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    """A selected source sheet must stay within its admitted workbook archive."""
    mode = ' TargetMode="External"' if target.startswith("https:") else ""
    relationships = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships">'
        f'<Relationship Id="rId1" Target="{target}"{mode}/>'
        "</Relationships>"
    )
    replace_member(
        synthetic_workbook,
        "xl/_rels/workbook.xml.rels",
        relationships.encode(),
    )
    pin_synthetic(synthetic_workbook, monkeypatch)
    with pytest.raises(ValueError, match="local archive member"):
        dapane_workbook.inspect_manual_extraction_workbook(synthetic_workbook)


def test_workbook_size_bound_precedes_parsing(
    synthetic_workbook: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a source above the declared byte bound before opening its archive."""
    monkeypatch.setattr(dapane_workbook, "MAX_WORKBOOK_BYTES", 1)
    with pytest.raises(ValueError, match="bound"):
        dapane_workbook.inspect_manual_extraction_workbook(synthetic_workbook)
