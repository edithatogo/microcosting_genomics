# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise opt-in variable run sizes under explicit single-resource bounds."""

from decimal import Decimal
from itertools import product
lazy from pathlib import Path

import pytest

from genomics_microcosting.dynamic_batch import AvailabilityWindow
from genomics_microcosting.static_batch_cost import optimize_variable_batch_runs
from tests import checks
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


def test_variable_runs_reduce_packs_at_fixed_deadline(tmp_path: Path) -> None:
    """Seven requests use four packs when their three loads can vary."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic().model_copy(
        update={
            "max_wait_seconds": Decimal(0),
            "turnaround_limit_seconds": Decimal(7),
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(1), end_seconds=Decimal(10)),
            ),
        },
    )
    result = optimize_variable_batch_runs(timed(7), policy, pricing, context)
    checks.require_equal(result.state, "feasible")
    (point,) = result.frontier
    checks.require_equal(point.payloads, (2, 2, 3))
    checks.require_equal(point.worst_turnaround_seconds, Decimal(7))
    checks.require_equal(point.cost.total_cost, Decimal("125.5"))
    checks.require_equal(point.cost.packs, 4)
    checks.require_equal(
        result,
        optimize_variable_batch_runs(timed(7), policy, pricing, context),
    )


def test_idle_and_impossible_deadline(tmp_path: Path) -> None:
    """Idle has a priced fixed cost and impossible service has no complete cost."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic().model_copy(
        update={
            "max_wait_seconds": Decimal(0),
            "turnaround_limit_seconds": Decimal(1),
        },
    )
    idle = optimize_variable_batch_runs(timed(0), policy, pricing, context)
    checks.require_equal(idle.state, "no_demand")
    checks.require_equal(idle.frontier, ())
    if idle.idle_cost is None:
        raise AssertionError
    checks.require_equal(idle.idle_cost.idle_cost, Decimal(10))
    checks.require_equal(idle.idle_cost.unit_cost, None)
    impossible = optimize_variable_batch_runs(timed(1), policy, pricing, context)
    checks.require_equal(impossible.state, "infeasible")
    checks.require_equal(impossible.frontier, ())
    checks.require_equal(impossible.idle_cost, None)


def test_variable_scope_rejects_asynchronous_or_wait_policy(tmp_path: Path) -> None:
    """A release rule or asynchronous workload needs a different planner."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    with pytest.raises(ValueError, match="zero max wait"):
        optimize_variable_batch_runs(timed(2), dynamic(), pricing, context)
    workload = timed(2)
    workload = workload.model_copy(
        update={
            "cases": (
                workload.cases[0],
                workload.cases[1].model_copy(update={"arrival_seconds": Decimal(1)}),
            ),
        },
    )
    policy = dynamic().model_copy(update={"max_wait_seconds": Decimal(0)})
    with pytest.raises(ValueError, match="simultaneous"):
        optimize_variable_batch_runs(workload, policy, pricing, context)


@pytest.mark.parametrize("scope", ["per_run", "horizon"])
@pytest.mark.parametrize("driver", ["payload_slots", "control_slots", "occupied_slots"])
def test_calendar_and_pack_scope_frontier(
    tmp_path: Path,
    scope: str,
    driver: str,
) -> None:
    """Brute force verifies the frontier for every pack driver and sharing scope."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    pricing = pricing.model_copy(update={"pack_scope": scope, "pack_driver": driver})
    policy = dynamic().model_copy(
        update={
            "max_wait_seconds": Decimal(0),
            "turnaround_limit_seconds": Decimal(10),
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(1), end_seconds=Decimal(5)),
                AvailabilityWindow(start_seconds=Decimal(6), end_seconds=Decimal(10)),
            ),
        },
    )
    result = optimize_variable_batch_runs(timed(6), policy, pricing, context)
    expected: list[tuple[Decimal, Decimal]] = []
    demand = 6
    for count, end in enumerate((3, 5, 8, 10), 1):
        costs: list[Decimal] = []
        for loads in product(range(1, 4), repeat=count):
            if sum(loads) != demand:
                continue
            units = [
                {"payload_slots": load, "control_slots": 1, "occupied_slots": load + 1}[
                    driver
                ]
                for load in loads
            ]
            packs = (
                sum((n + 2) // 3 for n in units)
                if scope == "per_run"
                else (sum(units) + 2) // 3
            )
            costs.append(Decimal(22) + Decimal("0.5") * count + Decimal(25) * packs)
        if costs and (not expected or min(costs) < expected[-1][1]):
            expected.append((Decimal(end), min(costs)))
    checks.require_equal(
        [
            (point.worst_turnaround_seconds, point.cost.total_cost)
            for point in result.frontier
        ],
        expected,
    )
    for point in result.frontier:
        checks.require_equal(sum(point.payloads), 6)


def test_search_rechecks_sources_and_bounds(tmp_path: Path) -> None:
    """Invalid evidence and demand bounds fail even for idle or infeasible search."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic().model_copy(update={"max_wait_seconds": Decimal(0)})
    with pytest.raises(ValueError, match="supported bound"):
        optimize_variable_batch_runs(timed(129), policy, pricing, context)
    context.snapshots["quantity"].write_text("11\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        optimize_variable_batch_runs(timed(0), policy, pricing, context)
