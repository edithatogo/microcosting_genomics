# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify the combined T1 scenario selects both conditional changes."""

import json
import sys
from hashlib import sha256
from shutil import copyfile
from typing import TYPE_CHECKING

from openpyxl import load_workbook
lazy import pytest

from tests import checks
from tools import build_t1_scenario

if TYPE_CHECKING:
    from pathlib import Path


FIXTURES = build_t1_scenario.ROOT / "tests/fixtures/t1_scenarios"


def test_combined_scenario_composes_reception_and_compute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build from the exact source and retain both sets of selected formulas."""
    source = (
        build_t1_scenario.ROOT
        / "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    original = sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "combined.xlsm"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_t1_scenario",
            str(source),
            str(output),
            "--manifest-dir",
            str(FIXTURES),
            "--version",
            "t1-combined-sensitivity-v5",
        ],
    )
    build_t1_scenario.main()
    book = load_workbook(output, read_only=True, data_only=False)
    detail = book["Detailed Table"]
    compute = book["BI - Comp Use - VCGS"]
    checks.require_equal(detail["N537"].value, "=SUM(N532:N536)")
    checks.require_equal(detail["N1083"].value, "=SUM(N1078:N1082)")
    checks.require_equal(detail["M1058"].value, "=SUM(M1056)+$M1050")
    checks.require_equal(compute["V105"].value, "=SUM(V69:V104)-V76-V100")
    host = json.loads((FIXTURES / "t1-host-overlap-v4.json").read_text())
    checks.require_equal(compute["U105"].value, host["remaining"]["low"])
    checks.require_equal(compute["W105"].value, host["remaining"]["high"])
    book.close()
    checks.require_equal(sha256(source.read_bytes()).hexdigest(), original)


def test_combined_manifest_detects_constituent_changes(
    tmp_path: Path,
) -> None:
    """A versioned combination cannot silently absorb a changed assumption."""
    manifest_name = "t1-combined-sensitivity-v5.json"
    source_manifest = FIXTURES / manifest_name
    manifest = json.loads(source_manifest.read_text())
    copyfile(source_manifest, tmp_path / manifest_name)
    for name in manifest["constituent_sha256"]:
        copyfile(FIXTURES / name, tmp_path / name)
    build_t1_scenario.verify_combined_manifest(
        manifest["source_workbook_sha256"],
        manifest_dir=tmp_path,
    )
    path = tmp_path / "t1-host-overlap-v4.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="constituent changed"):
        build_t1_scenario.verify_combined_manifest(
            manifest["source_workbook_sha256"],
            manifest_dir=tmp_path,
        )
