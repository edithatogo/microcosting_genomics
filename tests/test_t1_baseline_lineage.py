# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check known source-bound zero-cost dependencies cannot be omitted."""

import pytest

from genomics_microcosting.t1_baseline_lineage import (
    BASELINE_SHA256,
    require_known_baseline_scope,
)


def test_scoped_exome_baseline_requires_both_known_inputs() -> None:
    """Reject either missing library-preparation zero in the exact source."""
    two = ("cost:WB30:E47", "cost:WB30:E48")
    for declared in ((), (two[0],), (two[1],)):
        with pytest.raises(ValueError, match="omits known unresolved"):
            require_known_baseline_scope(BASELINE_SHA256, "WB17:N430", declared)
    require_known_baseline_scope(BASELINE_SHA256, "WB17:N430", two)


def test_assay_total_requires_only_its_traced_known_dependencies() -> None:
    """Genome total includes the sodium input, but not exome-only inputs."""
    with pytest.raises(ValueError, match="WB30:E105"):
        require_known_baseline_scope(BASELINE_SHA256, "WB02:N60", ("other",))
    require_known_baseline_scope(BASELINE_SHA256, "WB02:N60", ("cost:WB30:E105",))
    require_known_baseline_scope("a" * 64, "WB02:N60", ("other",))
