# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Create the synthetic formula workbook through openpyxl when explicitly run."""

from pathlib import Path

from openpyxl import Workbook


def create_test_workbook(path: Path) -> None:
    """Write the same two worksheets without importing pandas or running on import."""
    workbook = Workbook()
    first = workbook.active
    if first is None:
        message = "New workbook has no active worksheet"
        raise RuntimeError(message)
    first.title = "Sheet1"
    first.append(["col1", "col2", "col3"])
    for row in ((1, 4, "=A2*B2"), (2, 5, "=A3*B3"), (3, 6, "=A4*B4")):
        first.append(row)
    second = workbook.create_sheet("Sheet2")
    for row in (("colA", "colB"), (10, 40), (20, 50), (30, 60)):
        second.append(row)
    try:
        workbook.save(path)
    finally:
        workbook.close()


if __name__ == "__main__":
    create_test_workbook(Path("tests/test_data.xlsx"))
