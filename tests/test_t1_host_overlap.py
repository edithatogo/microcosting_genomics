# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check the explicit host-overlap sensitivity and its task-level arithmetic."""

import json
from math import isclose
from pathlib import Path

from tests import checks
from tools.build_t1_scenario import apply_host_overlap

TRACK = Path(__file__).resolve().parent / "fixtures/t1_scenarios"


def test_host_overlap_extreme_uses_matching_task_extrema() -> None:
    """Selected exclusions match the synthetic counts, cores and rate."""
    extreme = json.loads((TRACK / "t1-host-overlap-v4.json").read_text())
    original = json.loads((TRACK / "option2-compute-sensitivity-v1.json").read_text())
    checks.require_equal(
        extreme["source_workbook_sha256"],
        original["source_workbook_sha256"],
    )
    checks.require_equal({row["cell"] for row in extreme["jobs"]}, {"A76", "A100"})
    for field, category in (("min", "low"), ("mean", "mid"), ("max", "high")):
        removed = sum(
            job[field]
            * job["count"]
            * job["cores"]
            / 3600
            / extreme["genome_batch_size"]
            * extreme["rate_per_core_hour"]
            for job in extreme["jobs"]
        )
        checks.require_equal(
            isclose(removed, extreme["removed"][category], abs_tol=1e-12),
            bool(1),
        )
        checks.require_equal(
            isclose(
                original[category] - removed,
                extreme["remaining"][category],
                abs_tol=1e-12,
            ),
            bool(1),
        )
    changes: list[dict[str, object]] = [
        {"sheet": "BI - Comp Use - VCGS", "cell": cell, "replacement": 0}
        for cell in ("U105", "V105", "W105")
    ]
    apply_host_overlap(changes, extreme["source_workbook_sha256"], manifest_dir=TRACK)
    checks.require_equal(changes[1]["replacement"], "=SUM(V69:V104)-V76-V100")
    checks.require_equal(changes[0]["replacement"], extreme["remaining"]["low"])
    checks.require_equal(changes[2]["replacement"], extreme["remaining"]["high"])
