# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Enforce the archive boundary before release packaging is accepted."""

lazy from pathlib import Path

import pytest

from tools.check_package import check_distribution_paths, check_paths


@pytest.mark.parametrize(
    "name",
    [
        "package/data/source.xlsx",
        "package/src/private.parquet",
        "package/.private-runs/receipt.json",
        "package/conductor/plan.md",
        "package/../outside.py",
        "/absolute.py",
        "package\\outside.py",
    ],
)
def test_research_or_unsafe_paths_are_rejected(name: str) -> None:
    """Reject sensitive file classes, private work and archive traversal."""
    with pytest.raises(ValueError, match="Disallowed distribution path"):
        check_paths([name])


def test_source_and_complete_licence_paths_are_allowed() -> None:
    """Allow maintained code, native templates and licence metadata."""
    check_paths(
        [
            "genomics_microcosting/calculation_engine.py",
            "genomics_microcosting/templates/table.html",
            "genomics_microcosting-0.2.0.dist-info/licenses/LICENSE",
        ],
    )


def test_generated_index_requires_exact_reviewed_bytes() -> None:
    """A generated code asset cannot become a route for arbitrary research data."""
    path = (
        Path(__file__).resolve().parents[1]
        / "src/genomics_microcosting/data/t1_known_zero_lineage.json"
    )
    name = "genomics_microcosting/data/t1_known_zero_lineage.json"
    check_distribution_paths({name: path.read_bytes()})
    with pytest.raises(ValueError, match="differs from reviewed"):
        check_distribution_paths({name: b"private values"})
    with pytest.raises(ValueError, match="Disallowed"):
        check_distribution_paths({"genomics_microcosting/data/other.json": b"{}"})
