# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check immutable diagnostic overlays and fail-closed preconditions."""

import pytest

from genomics_microcosting import baseline_repairs
from tests import checks


def test_overlay_preserves_source_and_unselected_cells() -> None:
    """A selected correction changes only its target in a new map."""
    source = {("S", "A1"): "=1", ("S", "A2"): "=2"}
    result = baseline_repairs.diagnostic_overlay(
        source,
        [("S", "A1", "=1", "=3")],
        source_sha256=baseline_repairs.SOURCE_SHA256,
        diagnostic_opt_in=True,
    )
    checks.require_equal(result, {("S", "A1"): "=3", ("S", "A2"): "=2"})
    checks.require_equal(source, {("S", "A1"): "=1", ("S", "A2"): "=2"})


@pytest.mark.parametrize("failure", ["opt_in", "hash", "formula", "duplicate", "empty"])
def test_invalid_overlay_is_atomic(failure: str) -> None:
    """Invalid selections fail without partially editing source formulas."""
    source = {("S", "A1"): "=1"}
    changes = [("S", "A1", "=wrong" if failure == "formula" else "=1", "=3")]
    if failure == "duplicate":
        changes *= 2
    if failure == "empty":
        changes = []
    with pytest.raises(ValueError, match=r"."):
        baseline_repairs.diagnostic_overlay(
            source,
            changes,
            source_sha256="wrong"
            if failure == "hash"
            else baseline_repairs.SOURCE_SHA256,
            diagnostic_opt_in=failure != "opt_in",
        )
    checks.require_equal(source, {("S", "A1"): "=1"})
