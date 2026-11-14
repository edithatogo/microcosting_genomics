# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Preserve publication tables while making dictionary examples opt-in."""

lazy from pathlib import Path

import polars as pl
from polars.testing import assert_frame_equal

from genomics_microcosting.data_manager import DataManager


def test_native_publication_export(tmp_path: Path) -> None:
    """Retain exported values, metadata and null counts without automatic samples."""
    manager = DataManager(tmp_path / "data")
    manager.publication_dir = tmp_path / "publication"
    manager.publication_dir.mkdir()
    frame = pl.DataFrame({"id": ["001", "002"], "amount": [1.25, None]})
    if not (manager.save_for_publication("Example", frame, {"currency": "AUD"})):
        raise AssertionError
    restored = pl.read_csv(manager.publication_dir / "example.csv", schema=frame.schema)
    assert_frame_equal(frame, restored)
    dictionary = pl.read_csv(manager.publication_dir / "example_dictionary.csv")
    if not (dictionary["sample_values"].fill_null("").to_list() == ["", ""]):
        raise AssertionError
    if not (dictionary["null_count"].to_list() == [0, 1]):
        raise AssertionError
    if not ((manager.publication_dir / "example_metadata.json").exists()):
        raise AssertionError
    if not (manager.save_for_publication("Example", frame, include_examples=True)):
        raise AssertionError
    explicit = pl.read_csv(manager.publication_dir / "example_dictionary.csv")
    if "001" not in explicit["sample_values"][0]:
        raise AssertionError
