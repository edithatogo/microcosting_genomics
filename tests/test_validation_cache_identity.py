# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Never reuse validation results for different rows, schemas or tolerances."""

import json
import time
from typing import TYPE_CHECKING

import polars as pl

from genomics_microcosting.validate_engine import (
    VALIDATION_CONFIG,
    create_dataframe_hash,
    load_from_cache,
    perform_validation_parallel,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

CACHE_ENABLED = True
PREVIEW_LAST_INDEX = 10
EXPECTED_DISTINCT_HASHES = 3


def test_validation_hash_covers_rows_after_preview() -> None:
    """A changed eleventh row must invalidate a cached comparison."""
    original = pl.DataFrame({"cost": list(range(11))})
    altered = original.with_columns(
        pl.when(pl.int_range(pl.len()) == PREVIEW_LAST_INDEX)
        .then(900)
        .otherwise(pl.col("cost"))
        .alias("cost"),
    )
    if create_dataframe_hash(original) == create_dataframe_hash(altered):
        raise AssertionError


def test_validation_hash_retains_schema_and_order() -> None:
    """Row order and numeric dtype are part of positional comparison identity."""
    original = pl.DataFrame({"cost": [1, 2, 3]})
    hashes = {
        create_dataframe_hash(original),
        create_dataframe_hash(original.reverse()),
        create_dataframe_hash(original.cast(pl.Float64)),
    }
    if len(hashes) != EXPECTED_DISTINCT_HASHES:
        raise AssertionError(hashes)


def test_validation_hash_supports_mixed_workbook_scalars() -> None:
    """Object columns from the formula engine remain hashable without coercion."""
    numeric = pl.DataFrame([pl.Series("cost", [1, None], dtype=pl.Object)])
    textual = pl.DataFrame([pl.Series("cost", ["1", None], dtype=pl.Object)])
    if create_dataframe_hash(numeric) == create_dataframe_hash(textual):
        raise AssertionError


def test_cache_policy_changes_invalidate_comparisons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing an acceptance threshold must recompute an existing cache entry."""
    monkeypatch.setitem(VALIDATION_CONFIG, "use_cache", CACHE_ENABLED)
    monkeypatch.setitem(VALIDATION_CONFIG, "cache_dir", str(tmp_path))
    monkeypatch.setitem(VALIDATION_CONFIG, "significant_error_threshold", 0.01)
    reference = pl.DataFrame({"cost": [1.0]})
    result = pl.DataFrame({"cost": [1.5]})
    strict = perform_validation_parallel(reference, result, {"cost": "cost"})
    monkeypatch.setitem(VALIDATION_CONFIG, "significant_error_threshold", 1.0)
    lenient = perform_validation_parallel(reference, result, {"cost": "cost"})
    if strict[0]["significant_abs_errors"] != 1:
        raise AssertionError(strict)
    if lenient[0]["significant_abs_errors"] != 0:
        raise AssertionError(lenient)


def test_malformed_cache_is_a_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh timestamp cannot make incomplete JSON into accepted results."""
    monkeypatch.setitem(VALIDATION_CONFIG, "use_cache", CACHE_ENABLED)
    monkeypatch.setitem(VALIDATION_CONFIG, "cache_dir", str(tmp_path))
    (tmp_path / "synthetic.json").write_text(
        json.dumps({"timestamp": time.time(), "result": [{"comparisons": 900}]}),
    )
    if load_from_cache("synthetic") is not None:
        raise AssertionError
