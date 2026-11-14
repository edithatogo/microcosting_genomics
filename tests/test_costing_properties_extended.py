# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Bounded invariants for chunk conservation and native identifier round trips."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import polars as pl
from hypothesis import given, settings
from hypothesis import strategies as st
from polars.testing import assert_frame_equal

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.monte_carlo_optimizer import MonteCarloOptimizer
from genomics_microcosting.utils import cell_to_coords, coords_to_cell


@settings(max_examples=50, deadline=None)
@given(
    total=st.integers(min_value=0, max_value=10000),
    chunk_size=st.integers(min_value=1, max_value=1000),
    processes=st.integers(min_value=1, max_value=8),
)
def test_balanced_chunks_conserve_iterations(
    total: int,
    chunk_size: int,
    processes: int,
) -> None:
    """Every requested iteration belongs to exactly one balanced chunk."""
    optimizer = MonteCarloOptimizer(Mock(spec=DataManager))
    chunks = optimizer.create_chunks(total, chunk_size, processes)
    if sum(chunks) != total or any(length < 0 for length in chunks):
        raise AssertionError(chunks)
    if not chunks or len(chunks) > processes * 4:
        raise AssertionError(chunks)
    if max(chunks) - min(chunks) > 1:
        raise AssertionError(chunks)


@settings(max_examples=25, deadline=None)
@given(
    identifiers=st.lists(
        st.text(alphabet="0123456789", min_size=1, max_size=8),
        min_size=1,
        max_size=12,
    ),
)
def test_parquet_preserves_identifier_strings(identifiers: list[str]) -> None:
    """Arrow/Parquet round trips preserve leading zeroes and exact row order."""
    expected = pl.DataFrame(
        {"identifier": identifiers},
        schema={"identifier": pl.String},
    )
    with TemporaryDirectory() as directory:
        path = Path(directory) / "identifiers.parquet"
        expected.write_parquet(path)
        actual = pl.read_parquet(path)
    assert_frame_equal(actual, expected)


@settings(max_examples=60, deadline=None)
@given(row=st.integers(0, 10000), column=st.integers(0, 1000))
def test_coordinate_round_trip(row: int, column: int) -> None:
    """Workbook coordinates round trip across single and multiple letter columns."""
    if cell_to_coords(coords_to_cell(row, column)) != (row, column):
        raise AssertionError((row, column))
