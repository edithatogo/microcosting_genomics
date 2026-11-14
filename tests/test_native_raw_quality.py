# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Qualify native raw extraction, explicit transformations and quality reports."""

lazy from pathlib import Path

import openpyxl
import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pydantic import ValidationError

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.data_pipeline import DataPipeline
from genomics_microcosting.data_quality_assurance import DataQualityAssurance
from genomics_microcosting.extractors import (
    CSVExtractor,
    ExcelExtractor,
    ParquetExtractor,
)
from genomics_microcosting.loaders import MetadataLoader, MultiFormatLoader
from genomics_microcosting.transformers import (
    CLEANING_CONFIG_ADAPTER,
    CostCalculator,
    DataCleaner,
    HeaderNormalizer,
    ValidationChecker,
)
from tests.checks import require_equal


def test_raw_workbook_pipeline_and_quality(tmp_path: Path) -> None:
    """Preserve identifiers, provenance, duplicate rows and declared cost values."""
    source = tmp_path / "source.xlsx"
    book = openpyxl.Workbook()
    sheet = book.active
    if not (sheet is not None):
        raise AssertionError
    sheet.title = "Input"
    sheet.append(["ID", "Unit Cost", "Source"])
    sheet.append(["001", 1.25, "paper"])
    sheet.append(["001", 1.25, "paper"])
    book.save(source)
    book.close()
    destination = tmp_path / "output"
    extractor = ExcelExtractor(
        "excel",
        source,
        sheet_configs={
            "Input": {
                "header_rows": 1,
                "data_starts_at": 2,
                "string_columns": ["id"],
            },
        },
    )
    checker = ValidationChecker("validation", validation_rules={})
    pipeline = DataPipeline("raw-native")
    pipeline.add_extractor(extractor)
    pipeline.add_transformer(HeaderNormalizer("headers", column_mappings={}))
    pipeline.add_transformer(CostCalculator("costs", cost_config={}))
    pipeline.add_transformer(DataCleaner("clean"))
    pipeline.add_transformer(checker)
    pipeline.add_loader(
        MultiFormatLoader("files", destination, formats=["parquet", "csv", "json"]),
    )
    pipeline.add_loader(
        MetadataLoader("metadata", destination, validation_results=checker.results),
    )
    result = pipeline.run()
    if not isinstance(result, dict):
        raise TypeError(result)
    expected = pl.DataFrame(
        {"id": ["001", "001"], "unit_cost": [1.25, 1.25], "source": ["paper", "paper"]},
    )
    assert_frame_equal(expected, result["Input"])
    assert_frame_equal(
        expected,
        ParquetExtractor("parquet", destination / "input.parquet").extract(),
    )
    assert_frame_equal(
        expected,
        CSVExtractor(
            "csv",
            destination / "input.csv",
            schema=expected.schema,
        ).extract(),
    )
    manager = DataManager(tmp_path)
    manager.prepared_dir = destination
    quality = DataQualityAssurance(manager)
    metrics = quality.assess_data_quality(
        "Input",
        cost_columns=["unit_cost"],
        unique_columns=["id"],
    )
    if not (metrics.duplicate_rows == 1):
        raise AssertionError
    if not (metrics.integrity_violations):
        raise AssertionError
    if "Integrity Violations" not in quality.generate_quality_report():
        raise AssertionError
    if not (checker.results["Input"]["issues"]):
        raise AssertionError


def test_cleaner_preserves_defaults_and_explicit_interpolation() -> None:
    """Require explicit cleaning and retain the legacy trailing-fill option."""
    frame = pl.DataFrame(
        {"id": ["001", "001", "002", None], "cost": [1.0, None, 3.0, None]},
    )
    default = DataCleaner("default").transform(frame)
    if not isinstance(default, pl.DataFrame):
        raise TypeError(default)
    assert_frame_equal(frame, default)
    explicit = DataCleaner(
        "explicit",
        cleaning_config={"handle_missing": "interpolate"},
    ).transform(frame)
    if not isinstance(explicit, pl.DataFrame):
        raise TypeError(explicit)
    if not (explicit["cost"].to_list() == [1.0, 2.0, 3.0, 3.0]):
        raise AssertionError
    if not (explicit["id"].to_list() == frame["id"].to_list()):
        raise AssertionError
    require_equal(frame["cost"].null_count(), 2)


def test_raw_header_collision_is_lossless(tmp_path: Path) -> None:
    """Disambiguate a duplicate whose generated suffix is itself a source label."""
    source = tmp_path / "collision.xlsx"
    book = openpyxl.Workbook()
    sheet = book.active
    if not (sheet is not None):
        raise AssertionError
    sheet.title = "Input"
    sheet.append(["Value", "Value", "Value_1"])
    sheet.append([1, 2, 3])
    book.save(source)
    book.close()
    frame = ExcelExtractor(
        "excel",
        source,
        sheet_configs={
            "Input": {
                "header_rows": 1,
                "data_starts_at": 2,
            },
        },
    ).extract()["Input"]
    require_equal(frame.width, 3)
    require_equal(len(set(frame.columns)), 3)
    if not (frame.row(0) == (1.0, 2.0, 3.0)):
        raise AssertionError


def test_cleaning_flags_reject_string_booleans() -> None:
    """Prevent a JSON string from enabling row deletion through truthiness."""
    with pytest.raises(ValidationError):
        CLEANING_CONFIG_ADAPTER.validate_python({"remove_duplicates": "false"})
