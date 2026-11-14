# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Preserve typed source values at the native DataManager boundary."""

from datetime import date
from decimal import Decimal
lazy from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

import genomics_microcosting.data_manager as data_manager_module
from genomics_microcosting.data_manager import DataManager


def test_installed_defaults_use_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Installed defaults must not write inside the Python environment."""
    installed = tmp_path / "environment" / "site-packages" / "genomics_microcosting"
    installed.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(
        data_manager_module,
        "__file__",
        str(installed / "data_manager.py"),
    )
    monkeypatch.chdir(workspace)
    manager = DataManager()
    if manager.data_dir != workspace / "data":
        raise AssertionError
    if manager.publication_dir != workspace / "publication":
        raise AssertionError
    explicit = tmp_path / "explicit"
    if DataManager(explicit).data_dir != explicit:
        raise AssertionError
    if (installed.parent / "data").exists():
        raise AssertionError


def test_native_parquet_roundtrip(tmp_path: Path) -> None:
    """Preserve identifiers, nulls, exact decimals, dates and empty schemas."""
    manager = DataManager(tmp_path)
    frame = pl.DataFrame(
        {
            "id": ["001", "002"],
            "count": pl.Series([1, None], dtype=pl.Int64),
            "date": [date(2020, 1, 1), None],
            "amount": pl.Series([Decimal("1.20"), None], dtype=pl.Decimal(12, 2)),
        },
    )
    if not (manager.save_sheet_polars("typed", frame, ["parquet"])):
        raise AssertionError
    restored = manager.load_sheet_polars("typed")
    if not (restored is not None):
        raise AssertionError
    assert_frame_equal(frame, restored)
    if not (manager.save_sheet_polars("empty", frame.head(0), ["parquet"])):
        raise AssertionError
    empty = manager.load_sheet_polars("empty")
    if not (empty is not None):
        raise AssertionError
    assert_frame_equal(frame.head(0), empty)


def test_native_csv_requires_contract(tmp_path: Path) -> None:
    """Preserve leading-zero identifiers and refuse implicit CSV inference."""
    manager = DataManager(tmp_path)
    frame = pl.DataFrame({"id": ["001", "002"], "count": [1, 2]})
    if not (manager.save_sheet_polars("typed", frame, ["csv"])):
        raise AssertionError
    with pytest.raises(ValueError, match="explicit field schema"):
        manager.load_sheet_polars("typed", "csv")
    restored = manager.load_sheet_polars(
        "typed",
        "csv",
        csv_schema={"id": pl.String, "count": pl.Int64},
    )
    if not (restored is not None):
        raise AssertionError
    assert_frame_equal(frame, restored)
    if manager.load_sheet_polars("absent") is not None:
        raise AssertionError
