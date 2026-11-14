# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reconcile static-limit and time-dependent batch costs."""

from decimal import Decimal
lazy from pathlib import Path

from genomics_microcosting.dynamic_batch import AvailabilityWindow
from genomics_microcosting.static_batch_cost import (
    calculate_dynamic_batch_cost,
    calculate_static_batch_cost,
)
from tests import checks
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


def test_static_limit_costs_match_and_partial_costs_keep_unserved_work(
    tmp_path: Path,
) -> None:
    """Equivalent runs reconcile exactly; partial service keeps explicit scope."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic()
    w = timed(4)
    static = calculate_static_batch_cost(w, policy.batch, pricing, context)
    result = calculate_dynamic_batch_cost(w, policy, pricing, context)
    checks.require_equal(result.cost.total_cost, static.total_cost)
    checks.require_equal(result.cost.packs, static.packs)
    checks.require_equal(result.cost_state, "complete_workload")
    short = policy.model_copy(
        update={
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(0), end_seconds=Decimal(3)),
            ),
        },
    )
    partial = calculate_dynamic_batch_cost(w, short, pricing, context)
    checks.require_equal(partial.cost_state, "partial_workload")
    checks.require_equal(partial.schedule.unserved_case_ids, ("c3",))
    checks.require_equal(partial.cost.total_cost, Decimal("66.5"))
    checks.require_equal(partial.cost.demand_count, 3)
    checks.require_equal(partial.cost.planned_runs, 1)
    late = policy.model_copy(update={"turnaround_limit_seconds": Decimal(3)})
    all_served_late = calculate_dynamic_batch_cost(w, late, pricing, context)
    checks.require_equal(all_served_late.cost_state, "complete_workload")
    checks.require_equal(all_served_late.schedule.feasibility, "infeasible")


def test_timeout_release_changes_runs_and_per_run_pack_cost(tmp_path: Path) -> None:
    """Early release can incur more runs/packs than static pooled demand."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic()
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    static = calculate_static_batch_cost(w, policy.batch, pricing, context)
    result = calculate_dynamic_batch_cost(w, policy, pricing, context)
    checks.require_equal(static.total_cost, Decimal("39.5"))
    checks.require_equal(result.cost.total_cost, Decimal(65))
    checks.require_equal(len(result.schedule.runs), 2)
