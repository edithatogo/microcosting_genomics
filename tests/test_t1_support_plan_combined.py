# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify the explicitly selected support-plan and coverage diagnostic."""

import sys
from hashlib import sha256
from shutil import copytree
lazy from pathlib import Path

from openpyxl import load_workbook
lazy import pytest

from tools import build_t1_scenario

FIXTURES = build_t1_scenario.ROOT / "tests/fixtures/t1_scenarios"


def test_combined_support_scenario_preserves_source_and_selects_both(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The support diagnostic adds exactly its own formula to the v7 choices."""
    source = build_t1_scenario.ROOT / (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    digest = sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "scenario.xlsm"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "builder",
            str(source),
            str(target),
            "--manifest-dir",
            str(FIXTURES),
            "--version",
            "t1-support-plan-wes80-v8",
        ],
    )
    build_t1_scenario.main()
    workbook = load_workbook(target, read_only=True, data_only=False)
    if workbook["Eq - Costs and Usage - VCGS"]["AF26"].value != "=K26/P16":
        raise AssertionError
    if workbook["Detailed Table"]["F723"].value != (
        "='Cons -  Costs and Util - VCGS'!F95*'Cons -  Costs and Util - VCGS'!H95"
    ):
        raise AssertionError
    if workbook["Detailed Table"]["N537"].value != "=SUM(N532:N536)":
        raise AssertionError
    workbook.close()
    if sha256(source.read_bytes()).hexdigest() != digest:
        raise AssertionError


def test_combined_support_scenario_rejects_changed_assumption(
    tmp_path: Path,
) -> None:
    """Changing the support assumption cannot silently retain v8 identity."""
    track = tmp_path / "track"
    copytree(FIXTURES, track)
    path = track / "t1-support-plan-af26-v1.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="source identities do not agree"):
        build_t1_scenario.apply_support_plan_combination(
            [],
            "2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4",
            manifest_dir=track,
        )
