# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Keep workbook selection explicit when loading historical scenarios."""

lazy from pathlib import Path

import pytest

from genomics_microcosting.sheet_manager import SheetManager


def test_missing_selected_workbook_is_not_silently_substituted(tmp_path: Path) -> None:
    """A missing scenario must not load an unrelated validation workbook."""
    selected = tmp_path / "missing_scenario.xlsx"
    with pytest.raises(
        FileNotFoundError,
        match="Selected Excel workbook does not exist",
    ):
        SheetManager(selected)


def test_explicit_workbook_does_not_implicitly_load_prepared_sheets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit workbook selection cannot acquire an unrelated default table."""
    called: list[bool] = []

    def record_load(_manager: SheetManager) -> None:
        called.append(True)

    monkeypatch.setattr(SheetManager, "_load_prepared_tables", record_load)
    source = Path(__file__).resolve().parent / "test_data.xlsx"
    SheetManager(source)
    if called:
        raise AssertionError


def test_explicit_prepared_directory_is_still_selected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A caller may deliberately provide prepared tables for a workbook."""
    called: list[bool] = []

    def record_load(_manager: SheetManager) -> None:
        called.append(True)

    monkeypatch.setattr(SheetManager, "_load_prepared_tables", record_load)
    source = Path(__file__).resolve().parent / "test_data.xlsx"
    SheetManager(source, prepared_data_path=tmp_path)
    if not called:
        raise AssertionError
