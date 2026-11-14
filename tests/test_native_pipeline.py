# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""End-to-end native pipeline and missing-value validation regressions."""

lazy from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from genomics_microcosting.data_consistency_validator import DataConsistencyValidator
from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.data_pipeline import DataPipeline, PreparedSheetExtractor
from genomics_microcosting.loaders import MetadataLoader, MultiFormatLoader
from tests.checks import require_equal


def test_native_pipeline_roundtrip(tmp_path: Path) -> None:
    """Preserve rows and schema through prepared input and all file loaders."""
    manager = DataManager(tmp_path / "input")
    frame = pl.DataFrame({"id": ["001", "002"], "amount": [1.25, None]})
    if not (manager.save_sheet("source", frame, ["parquet"])):
        raise AssertionError
    destination = tmp_path / "nested" / "output"
    pipeline = DataPipeline("native")
    pipeline.add_extractor(PreparedSheetExtractor("source", manager, "source"))
    pipeline.add_loader(
        MultiFormatLoader("files", destination, formats=["parquet", "csv", "json"]),
    )
    pipeline.add_loader(MetadataLoader("metadata", destination))
    if not (pipeline.validate_pipeline()):
        raise AssertionError
    result = pipeline.run()
    if not isinstance(result, pl.DataFrame):
        raise TypeError
    assert_frame_equal(frame, result)
    assert_frame_equal(frame, pl.read_parquet(destination / "data.parquet"))
    assert_frame_equal(
        frame,
        pl.read_csv(destination / "data.csv", schema=frame.schema),
    )
    assert_frame_equal(frame, pl.read_json(destination / "data.json"))
    if not ((destination / "metadata.json").exists()):
        raise AssertionError


def test_missing_comparison_has_no_sentinel_collision(tmp_path: Path) -> None:
    """Distinguish a real sentinel-like value from missing source activity."""
    validator = DataConsistencyValidator(DataManager(tmp_path))
    result = validator.validate_sheet_consistency(
        "source",
        pl.DataFrame({"cost": [-999999.0]}),
        pl.DataFrame({"cost": [None]}, schema={"cost": pl.Float64}),
    )
    if not (any("Data mismatch" in value for value in result["warnings"])):
        raise AssertionError
    frame = pl.DataFrame({"value": [1.0, 1.0, 1.0, None, float("nan")]})
    result = validator.validate_sheet_integrity("source", frame)
    require_equal(result["metrics"]["duplicate_rows"], 3)
    require_equal(result["metrics"]["null_percentage"], 40)
    if not (frame["value"].null_count() == 1):
        raise AssertionError
    if not (frame["value"].is_nan().sum() == 1):
        raise AssertionError


def test_failed_requested_format_fails_pipeline(tmp_path: Path) -> None:
    """Do not report success when a requested export format cannot be written."""
    loader = MultiFormatLoader("files", tmp_path / "output", formats=["unsupported"])
    with pytest.raises(RuntimeError, match="Requested formats failed"):
        loader.load(pl.DataFrame({"x": [1]}))
