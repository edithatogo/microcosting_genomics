# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check the explicit reception allocation sensitivity against its source."""

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
lazy from openpyxl.cell.cell import Cell

from tests import checks

ROOT = Path(__file__).resolve().parents[1]


def test_per_sample_sensitivity_covers_both_trios_and_all_cost_columns() -> None:
    """The subtotal sums three receipt tasks and both once-per-case liaisons."""
    manifest = json.loads(
        (
            ROOT / "tests/fixtures/t1_scenarios" / "t1-reception-per-sample-v3.json"
        ).read_text(),
    )
    source = (
        ROOT
        / "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    checks.require_equal(
        sha256(source.read_bytes()).hexdigest(),
        manifest["source_workbook_sha256"],
    )
    workbook = load_workbook(source, read_only=True, data_only=False)
    source_sheet = workbook["Detailed Table"]
    changes = {item["cell"]: item for item in manifest["change"]}
    expected = {
        f"{get_column_letter(column)}{total}": (
            f"=SUM({get_column_letter(column)}{total - 5}:"
            f"{get_column_letter(column)}{total - 1})"
        )
        for total in (537, 1083)
        for column in range(13, 28)
    }
    checks.require_equal(
        {key: item["proposed_formula"] for key, item in changes.items()},
        expected,
    )
    for coordinate, item in changes.items():
        checks.require_equal(
            cast("Cell", source_sheet[coordinate]).value,
            item["source_formula"],
        )
    workbook.close()
