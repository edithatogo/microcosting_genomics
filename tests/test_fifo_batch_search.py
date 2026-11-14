# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify FIFO variable loads against timed partitions."""

from decimal import Decimal
from itertools import combinations, pairwise, product
lazy from pathlib import Path

import pytest

from genomics_microcosting.dynamic_batch import AvailabilityWindow, earliest_batch_start
from genomics_microcosting.static_batch_cost import enumerate_fifo_batch_plans
from tests import checks
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch import workload as unknown_workload
from tests.test_static_batch_cost import batch_inputs


def test_fifo_arrivals_produce_cost_turnaround_tradeoff(tmp_path: Path) -> None:
    """Waiting to combine two requests saves a run and costs elapsed time."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    workload = timed(2)
    workload = workload.model_copy(
        update={
            "cases": (
                workload.cases[0],
                workload.cases[1].model_copy(update={"arrival_seconds": Decimal(3)}),
            ),
        },
    )
    policy = dynamic().model_copy(update={"max_wait_seconds": Decimal(0)})
    result = enumerate_fifo_batch_plans(workload, policy, pricing, context)
    checks.require_equal(result.state, "feasible")
    checks.require_equal(
        [
            (p.payloads, p.worst_turnaround_seconds, p.cost.total_cost)
            for p in result.frontier
        ],
        [((1, 1), Decimal(2), Decimal(65)), ((2,), Decimal(5), Decimal("39.5"))],
    )
    for point in result.frontier:
        checks.require_equal(sum(point.payloads), 2)
    checks.require_equal(
        result,
        enumerate_fifo_batch_plans(workload, policy, pricing, context),
    )


@pytest.mark.parametrize("scope", ["per_run", "horizon"])
@pytest.mark.parametrize("driver", ["payload_slots", "control_slots", "occupied_slots"])
@pytest.mark.parametrize("deadline", [3, 10])
def test_fifo_frontier_matches_independent_time_grid(
    tmp_path: Path,
    scope: str,
    driver: str,
    deadline: int,
) -> None:
    """All cuts and integer start times independently determine the frontier."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    pricing = pricing.model_copy(update={"pack_scope": scope, "pack_driver": driver})
    arrivals = (0, 1, 3, 4)
    windows = ((0, 4), (5, 10))
    workload = timed(len(arrivals))
    workload = workload.model_copy(
        update={
            "cases": tuple(
                case.model_copy(update={"arrival_seconds": Decimal(arrival)})
                for case, arrival in zip(workload.cases, arrivals, strict=True)
            ),
        },
    )
    policy = dynamic().model_copy(
        update={
            "batch": dynamic().batch.model_copy(update={"max_runs": 3}),
            "max_wait_seconds": Decimal(0),
            "turnaround_limit_seconds": Decimal(deadline),
            "windows": tuple(
                AvailabilityWindow(
                    start_seconds=Decimal(a),
                    end_seconds=Decimal(b),
                )
                for a, b in windows
            ),
        },
    )
    pairs: set[tuple[int, Decimal]] = set()
    max_runs = max_load = 3
    for cuts in product((False, True), repeat=len(arrivals) - 1):
        groups: list[list[int]] = [[]]
        for index, arrival in enumerate(arrivals):
            groups[-1].append(arrival)
            if index < len(cuts) and cuts[index]:
                groups.append([])
        if len(groups) > max_runs or any(len(group) > max_load for group in groups):
            continue
        units = [
            {
                "payload_slots": len(group),
                "control_slots": 1,
                "occupied_slots": len(group) + 1,
            }[driver]
            for group in groups
        ]
        packs = (
            sum((n + 2) // 3 for n in units)
            if scope == "per_run"
            else (sum(units) + 2) // 3
        )
        cost = Decimal(18) + Decimal("0.5") * len(groups) + Decimal(25) * packs
        for starts in combinations(range(9), len(groups)):
            if any(right < left + 2 for left, right in pairwise(starts)):
                continue
            if any(
                start < max(group)
                or not any(a <= start and start + 2 <= b for a, b in windows)
                for start, group in zip(starts, groups, strict=True)
            ):
                continue
            tat = max(
                start + 2 - min(group)
                for start, group in zip(starts, groups, strict=True)
            )
            if tat <= deadline:
                pairs.add((tat, cost))
    expected = {
        pair
        for pair in pairs
        if not any(
            other != pair and other[0] <= pair[0] and other[1] <= pair[1]
            for other in pairs
        )
    }
    result = enumerate_fifo_batch_plans(workload, policy, pricing, context)
    checks.require_equal(
        {
            (int(point.worst_turnaround_seconds), point.cost.total_cost)
            for point in result.frontier
        },
        expected,
    )
    for point in result.frontier:
        checks.require_equal(
            [case for run in point.case_ids_by_run for case in run],
            [case.case_id for case in workload.cases],
        )


def test_fifo_idle_infeasible_and_scope_guards(tmp_path: Path) -> None:
    """Empty, unknown and infeasible workloads retain distinct meanings."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic().model_copy(update={"max_wait_seconds": Decimal(0)})
    idle = enumerate_fifo_batch_plans(timed(0), policy, pricing, context)
    checks.require_equal(idle.state, "no_demand")
    if idle.idle_cost is None:
        raise AssertionError
    checks.require_equal(idle.idle_cost.total_cost, Decimal(10))
    checks.require_equal(idle.idle_cost.unit_cost, None)
    impossible = enumerate_fifo_batch_plans(
        timed(1),
        policy.model_copy(
            update={
                "windows": (),
            },
        ),
        pricing,
        context,
    )
    checks.require_equal(impossible.state, "infeasible")
    checks.require_equal(impossible.frontier, ())
    checks.require_equal(impossible.idle_cost, None)
    with pytest.raises(ValueError, match="supported bound"):
        enumerate_fifo_batch_plans(timed(13), policy, pricing, context)
    with pytest.raises(ValueError, match="zero max wait"):
        enumerate_fifo_batch_plans(timed(1), dynamic(), pricing, context)
    with pytest.raises(ValueError, match="known arrivals"):
        enumerate_fifo_batch_plans(unknown_workload(1), policy, pricing, context)
    context.snapshots["quantity"].write_text("11\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        enumerate_fifo_batch_plans(timed(0), policy, pricing, context)


@pytest.mark.parametrize("release", [Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_calendar_selector_rejects_invalid_release(release: Decimal) -> None:
    """Shared calendar lookup rejects invalid scalar release observations."""
    with pytest.raises(ValueError, match="finite and nonnegative"):
        earliest_batch_start(release, dynamic())
