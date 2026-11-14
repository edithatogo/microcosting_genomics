# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify the explicit 80x source-quantity reconstruction."""

import json
import sys
from hashlib import sha256
from shutil import copyfile
from typing import TYPE_CHECKING, cast

from openpyxl import load_workbook
lazy import pytest
lazy from openpyxl.cell.cell import Cell

from tests import checks
from tools import build_t1_scenario

if TYPE_CHECKING:
    from pathlib import Path


FIXTURES = build_t1_scenario.ROOT / "tests/fixtures/t1_scenarios"


def test_wes80_quantities_follow_the_recorded_source_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply each quantity once, preserve the unmodified source and v3 receipt."""
    source = (
        build_t1_scenario.ROOT
        / "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    original_hash = sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "scenario.xlsm"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_t1_scenario",
            str(source),
            str(target),
            "--manifest-dir",
            str(FIXTURES),
            "--version",
            "t1-wes80-quantity-v6",
        ],
    )
    build_t1_scenario.main()
    manifest = json.loads(
        (FIXTURES / "t1-wes80-quantity-v6.json").read_text(),
    )
    workbook = load_workbook(target, read_only=True, data_only=False)
    sheet = workbook["Detailed Table"]
    checks.require_equal(len(manifest["change"]), 11)
    for change in manifest["change"]:
        checks.require_equal(
            cast("Cell", sheet[change["cell"]]).value,
            change["proposed_formula"],
        )
    checks.require_equal(sheet["F723"].value, "='Cons -  Costs and Util - VCGS'!G95")
    checks.require_equal(sheet["N537"].value, "=SUM(N532:N536)")
    workbook.close()
    checks.require_equal(sha256(source.read_bytes()).hexdigest(), original_hash)


def test_wes80_coverage_uses_labelled_80x_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Select the 80x allocation and quantities, retaining the 50x parents."""
    source = (
        build_t1_scenario.ROOT
        / "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    target = tmp_path / "scenario.xlsm"
    original = load_workbook(source, read_only=True, data_only=True)
    inputs = original["Cons -  Costs and Util - VCGS"]
    checks.require_equal(inputs["G3"].value, "50x (WES)")
    checks.require_equal(inputs["H3"].value, "80x (WES)")
    original.close()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_t1_scenario",
            str(source),
            str(target),
            "--manifest-dir",
            str(FIXTURES),
            "--version",
            "t1-wes80-coverage-v7",
        ],
    )
    build_t1_scenario.main()
    workbook = load_workbook(target, read_only=True, data_only=False)
    sheet = workbook["Detailed Table"]
    changes = json.loads(
        (FIXTURES / "t1-wes80-coverage-v7.json").read_text(),
    )["change"]
    checks.require_equal(len(changes), 12)
    for item in changes:
        checks.require_equal(
            cast("Cell", sheet[item["cell"]]).value,
            item["proposed_formula"],
        )
    checks.require_equal(
        sheet["F737"].value,
        "='Cons -  Costs and Util - VCGS'!$F95*'Cons -  Costs and Util - VCGS'!$G95*2",
    )
    checks.require_equal(sheet["N537"].value, "=SUM(N532:N536)")
    workbook.close()


def test_wes80_rejects_changed_inherited_assumptions(
    tmp_path: Path,
) -> None:
    """A recorded v7 identity cannot silently absorb changed base formulas."""
    version = "t1-wes80-coverage-v7"
    manifest = json.loads((FIXTURES / f"{version}.json").read_text())
    names = [
        f"{version}.json",
        "t1-reception-per-sample-v3.json",
        *manifest["inherited_manifest_sha256"],
    ]
    for name in names:
        copyfile(FIXTURES / name, tmp_path / name)
    build_t1_scenario.apply_wes80_quantities(
        [],
        manifest["source_workbook_sha256"],
        version,
        manifest_dir=tmp_path,
    )
    target = tmp_path / "t1-branch-corrections-v2.json"
    target.write_text(target.read_text() + " ")
    with pytest.raises(ValueError, match="inherited scenario identity mismatch"):
        build_t1_scenario.apply_wes80_quantities(
            [],
            manifest["source_workbook_sha256"],
            version,
            manifest_dir=tmp_path,
        )
