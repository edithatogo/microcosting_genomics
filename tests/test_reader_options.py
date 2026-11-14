# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Qualify native reader option forwarding and identifier/null preservation."""

import inspect
lazy from collections.abc import Callable
lazy from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from genomics_microcosting.extractors import CSVExtractor, ParquetExtractor
from genomics_microcosting.reader_options import CSVReadOptions, ParquetReadOptions


@pytest.mark.parametrize(
    ("reader", "contract"),
    [(pl.read_csv, CSVReadOptions), (pl.read_parquet, ParquetReadOptions)],
)
def test_native_reader_keyword_coverage(
    reader: Callable[..., object],
    contract: type,
) -> None:
    """Detect missing option names when the locked native reader API changes."""
    actual = set(inspect.signature(reader).parameters) - {"source"}
    expected = set(contract.__annotations__)
    if actual != expected:
        raise AssertionError((actual - expected, expected - actual))


def test_csv_and_parquet_reader_options(tmp_path: Path) -> None:
    """Forward nondefault reader settings without altering leading zeroes or nulls."""
    expected = pl.DataFrame(
        {"identifier": ["001", "020"], "cost": [2.5, None]},
        schema={"identifier": pl.String, "cost": pl.Float64},
    )
    csv_path = tmp_path / "source.csv"
    csv_path.write_text("identifier;cost\n001;2.5\n020;MISSING\n")
    csv = CSVExtractor(
        "csv",
        csv_path,
        separator=";",
        null_values="MISSING",
        schema={"identifier": pl.String, "cost": pl.Float64},
    ).extract()
    assert_frame_equal(csv, expected)
    parquet_path = tmp_path / "source.parquet"
    expected.write_parquet(parquet_path)
    parquet = ParquetExtractor(
        "parquet",
        parquet_path,
        columns=["identifier"],
        n_rows=1,
    ).extract()
    assert_frame_equal(parquet, expected.select("identifier").head(1))


def test_csv_requires_declared_schema(tmp_path: Path) -> None:
    """Keep the fail-closed raw-identifier schema requirement."""
    csv_path = tmp_path / "source.csv"
    csv_path.write_text("identifier\n001\n")
    with pytest.raises(ValueError, match="requires a declared schema"):
        CSVExtractor("unqualified", csv_path).extract()
