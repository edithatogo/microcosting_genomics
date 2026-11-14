# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify source integrity and atomic preconditions of scenario builds."""

from hashlib import sha256
from typing import cast
from zipfile import ZipFile
lazy from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
lazy from openpyxl.cell.cell import Cell
lazy from openpyxl.worksheet.worksheet import Worksheet

from genomics_microcosting.t1_workbook_builder import build_workbook_copy
from tests import checks


def test_scenario_build_preserves_source_and_checks_all_preconditions(
    tmp_path: Path,
) -> None:
    """Build one copy and reject a mismatched later change before saving."""
    source = tmp_path / "source.xlsx"
    workbook = Workbook()
    cast("Cell", workbook["Sheet"].cell(1, 1)).value = "=1+2"
    cast("Cell", workbook["Sheet"].cell(1, 2)).value = 7
    workbook.save(source)
    workbook.close()
    source_bytes = source.read_bytes()
    digest = sha256(source_bytes).hexdigest()
    changes: list[dict[str, object]] = [
        {"sheet": "Sheet", "cell": "A1", "original": "=1+2", "replacement": "=2+2"},
        {"sheet": "Sheet", "cell": "B1", "original": 7, "replacement": 8},
    ]
    target = tmp_path / "scenario.xlsx"
    build_workbook_copy(
        source,
        target,
        source_sha256=digest,
        changes=changes,
        selected_version="v1",
    )
    checks.require_equal(source.read_bytes(), source_bytes)
    result = load_workbook(target)
    checks.require_equal(result["Sheet"].cell(1, 1).value, "=2+2")
    checks.require_equal(result["Sheet"].cell(1, 2).value, 8)
    result.close()
    changes[1]["original"] = 9
    rejected = tmp_path / "rejected.xlsx"
    with pytest.raises(ValueError, match="precondition"):
        build_workbook_copy(
            source,
            rejected,
            source_sha256=digest,
            changes=changes,
            selected_version="v1",
        )
    checks.require_equal(rejected.exists(), bool(0))
    with pytest.raises(ValueError, match="Destination"):
        build_workbook_copy(
            source,
            target,
            source_sha256=digest,
            changes=changes,
            selected_version="v1",
        )
    with pytest.raises(ValueError, match="hash"):
        build_workbook_copy(
            source,
            rejected,
            source_sha256="0" * 64,
            changes=changes,
            selected_version="v1",
        )


def test_overlay_preserves_other_parts_and_shared_formula_meaning(
    tmp_path: Path,
) -> None:
    """Changing a shared-formula follower leaves its neighbours independent."""
    ordinary = tmp_path / "ordinary.xlsx"
    source = tmp_path / "source.xlsx"
    target = tmp_path / "scenario.xlsx"
    workbook = Workbook()
    sheet = cast("Worksheet", workbook.active)
    sheet["A1"] = 1
    sheet["A2"] = 2
    sheet["B1"] = "=A1+1"
    sheet["B2"] = "=A2+1"
    workbook.save(ordinary)
    workbook.close()
    with ZipFile(ordinary) as initial, ZipFile(source, "w") as shared:
        for part in initial.infolist():
            data = initial.read(part.filename)
            if part.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(
                    b"<f>A1+1</f>",
                    b'<f t="shared" si="0" ref="B1:B2">A1+1</f>',
                ).replace(b"<f>A2+1</f>", b'<f t="shared" si="0"/>')
            if part.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"A1+1</f><v></v>", b"A1+1</f><v>2</v>")
            shared.writestr(part, data)
    build_workbook_copy(
        source,
        target,
        source_sha256=sha256(source.read_bytes()).hexdigest(),
        changes=[
            {
                "sheet": "Sheet",
                "cell": "B2",
                "original": "=A2+1",
                "replacement": "=A2+5",
            },
        ],
        selected_version="shared-test",
    )
    with ZipFile(source) as before, ZipFile(target) as after:
        checks.require_equal(set(before.namelist()), set(after.namelist()))
        for part in before.namelist():
            if part not in {"xl/workbook.xml", "xl/worksheets/sheet1.xml"}:
                checks.require_equal(before.read(part), after.read(part))
    result = load_workbook(target)
    checks.require_equal(result["Sheet"]["B1"].value, "=A1+1")
    checks.require_equal(result["Sheet"]["B2"].value, "=A2+5")
    checks.require_equal(result.calculation.fullCalcOnLoad, bool(1))
    checks.require_equal(result.calculation.forceFullCalc, bool(1))
    result.close()
    cached = load_workbook(target, data_only=True)
    checks.require_equal(cached["Sheet"]["B1"].value, None)
    cached.close()
