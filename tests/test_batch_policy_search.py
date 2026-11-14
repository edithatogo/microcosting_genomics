# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify finite policy comparisons against hand-derived cost/TAT outcomes."""

from decimal import Decimal
from typing import cast
lazy from pathlib import Path

import pytest

from genomics_microcosting.batch_policy_search import (
    PolicyGrid,
    enumerate_batch_policies,
)
from tests import checks
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


def test_grid_retains_tradeoffs_ties_and_infeasible_policies(tmp_path: Path) -> None:
    """Two separated arrivals trade an extra pack/run against waiting time."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    result = enumerate_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        payload_limits=(1, 2),
        max_wait_seconds=(Decimal(0), Decimal(4)),
    )
    checks.require_equal(result.state, "feasible")
    checks.require_equal(len(result.points), 4)
    checks.require_equal(len({p.policy.batch.policy_id for p in result.points}), 4)
    # Payload 1 runs immediately regardless of timeout: cost 65, worst TAT 2.
    # Payload 2 wait 0 has the same outcome; wait 4 pools: 39.5, worst TAT 6.
    checks.require_equal(
        tuple(
            (p.result.cost.total_cost, p.worst_turnaround_seconds)
            for p in result.points
        ),
        (
            (Decimal(65), Decimal(2)),
            (Decimal(65), Decimal(2)),
            (Decimal(65), Decimal(2)),
            (Decimal("39.5"), Decimal(6)),
        ),
    )
    checks.require_equal(result.pareto_indices, (0, 1, 2, 3))
    strict = dynamic().model_copy(update={"turnaround_limit_seconds": Decimal(3)})
    constrained = enumerate_batch_policies(
        w,
        strict,
        pricing,
        context,
        payload_limits=(1, 2),
        max_wait_seconds=(Decimal(0), Decimal(4)),
    )
    checks.require_equal(constrained.pareto_indices, (0, 1, 2))
    checks.require_equal(
        constrained.points[3].result.schedule.feasibility,
        "infeasible",
    )
    checks.require_equal(result.points[3].policy.batch.controls_per_run, 1)
    checks.require_equal(result.points[3].policy.windows, dynamic().windows)


def test_grid_reports_no_data_and_no_feasible_solution(tmp_path: Path) -> None:
    """Idle work has no TAT objective; unschedulable work is not cheap success."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    empty = enumerate_batch_policies(
        timed(0),
        dynamic(),
        pricing,
        context,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(empty.state, "no_demand")
    checks.require_equal(empty.pareto_indices, ())
    checks.require_equal(empty.points[0].worst_turnaround_seconds, None)
    unavailable = dynamic().model_copy(update={"windows": ()})
    failed = enumerate_batch_policies(
        timed(1),
        unavailable,
        pricing,
        context,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(failed.state, "infeasible")
    checks.require_equal(failed.pareto_indices, ())
    checks.require_equal(failed.points[0].result.cost_state, "partial_workload")


def test_grid_bounds_and_identity_are_explicit(tmp_path: Path) -> None:
    """Reject unsupported grids and bind reproducibility to the selected points."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    for payloads, waits in (
        ((), (Decimal(0),)),
        ((True,), (Decimal(0),)),
        ((4,), (Decimal(0),)),
        ((1, 1), (Decimal(0),)),
        ((1,), (Decimal("NaN"),)),
        ((1,), (Decimal(-1),)),
        ((1,), (Decimal(0), Decimal(0))),
        ((1,), tuple(Decimal(i) for i in range(257))),
    ):
        with pytest.raises(ValueError, match="grid"):
            enumerate_batch_policies(
                timed(1),
                dynamic(),
                pricing,
                context,
                payload_limits=payloads,
                max_wait_seconds=waits,
            )
    args = (timed(1), dynamic(), pricing, context)
    first = enumerate_batch_policies(
        *args,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    repeat = enumerate_batch_policies(
        *args,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    changed = enumerate_batch_policies(
        *args,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(1),),
    )
    checks.require_equal(first, repeat)
    checks.require_equal(int(first.input_sha256 == changed.input_sha256), 0)


def test_dominance_and_run_bound_do_not_discard_failed_policies(tmp_path: Path) -> None:
    """A slower equal-cost choice is dominated; too few runs stays infeasible."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    result = enumerate_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        payload_limits=(2, 3),
        max_wait_seconds=(Decimal(4), Decimal(6)),
    )
    checks.require_equal(result.pareto_indices, (0, 1, 2))
    checks.require_equal(result.points[3].worst_turnaround_seconds, Decimal(8))
    policy = dynamic()
    policy = policy.model_copy(
        update={
            "batch": policy.batch.model_copy(update={"max_runs": 1}),
        },
    )
    bounded = enumerate_batch_policies(
        timed(2),
        policy,
        pricing,
        context,
        payload_limits=(1, 2),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(
        bounded.points[0].result.schedule.termination_reason,
        "run_bound",
    )
    checks.require_equal(bounded.points[0].result.schedule.unserved_case_ids, ("c1",))
    checks.require_equal(bounded.pareto_indices, (1,))


def test_policy_grid_rejects_invalid_runtime_keyword_names(tmp_path: Path) -> None:
    """Reject untyped callers with misspelled policy grid keys."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    options = cast("PolicyGrid", {"payload_limits": (1,), "max_wait_seconds_typo": ()})
    with pytest.raises(TypeError, match="Expected exactly payload_limits"):
        enumerate_batch_policies(timed(1), dynamic(), pricing, context, **options)
