# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Qualify native CSV values and preserve pre-existing publication outputs."""

from typing import TYPE_CHECKING

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from scripts.convert_to_csv import convert_parquet_to_csv

if TYPE_CHECKING:
    from pathlib import Path


def test_native_csv_round_trip(tmp_path: Path) -> None:
    """Keep leading-zero identifiers, nulls, quotes and Unicode in original order."""
    source = tmp_path / "prepared"
    source.mkdir()
    expected = pl.DataFrame(
        {
            "id": ["001", 'é,quoted"', None],
            "cost": [1.5, None, 0.0],
        },
    )
    expected.write_parquet(source / "native.parquet")
    output = tmp_path / "publication"
    converted = convert_parquet_to_csv(prepared_dir=source, publication_dir=output)
    actual = pl.read_csv(output / "native.csv", schema_overrides={"id": pl.String})
    assert_frame_equal(actual, expected)
    if converted != [
        {
            "original": "native.parquet",
            "csv": "native.csv",
            "rows": 3,
            "columns": 2,
        },
    ]:
        raise AssertionError(converted)


def test_csv_preflight_preserves_existing_outputs(tmp_path: Path) -> None:
    """Detect a later collision before creating any earlier new export."""
    source, output = tmp_path / "prepared", tmp_path / "publication"
    source.mkdir()
    output.mkdir()
    for name in ("a", "z"):
        pl.DataFrame({"id": ["001"]}).write_parquet(source / f"{name}.parquet")
    existing = output / "z.csv"
    existing.write_bytes(b"retained owner edits\n")
    with pytest.raises(FileExistsError):
        convert_parquet_to_csv(prepared_dir=source, publication_dir=output)
    if (
        existing.read_bytes() != b"retained owner edits\n"
        or (output / "a.csv").exists()
    ):
        raise AssertionError
