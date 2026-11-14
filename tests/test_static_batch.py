# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check integer boundaries and workload/control conservation."""

from decimal import Decimal

import pytest

from genomics_microcosting.static_batch import StaticBatchPolicy, plan_static_batches
from genomics_microcosting.workload_contract import Workload, WorkloadCase
from tests import checks


def policy() -> StaticBatchPolicy:
    """Return an explicitly assumed small capacity policy."""
    return StaticBatchPolicy(
        policy_id="p1",
        process_id="process",
        assay_id="assay",
        entity_kind="libraries",
        capacity=4,
        controls_per_run=1,
        payload_limit=3,
        max_runs=10,
        assumption_basis="synthetic only",
    )


def workload(n: int) -> Workload:
    """Supply explicit unattempted library demand."""
    cases = tuple(
        WorkloadCase(
            case_id=f"c{i}",
            requested_test_id=f"t{i}",
            assay_id="assay",
            arrival_seconds=None,
            patient_ids=None,
            family_ids=None,
            specimen_ids=None,
            library_ids=(f"l{i}",),
            reportable_result_ids=None,
        )
        for i in range(n)
    )
    return Workload(
        workload_id="w1",
        process_id="process",
        process_graph_sha256="a" * 64,
        parameter_version_id="v1",
        horizon_seconds=Decimal(10),
        cases=cases,
        control_ids=(),
        attempts=(),
    )


@pytest.mark.parametrize(
    ("n", "payloads"),
    [(0, ()), (1, (1,)), (3, (3,)), (4, (3, 1))],
)
def test_integer_capacity_boundaries_and_conservation(
    n: int,
    payloads: tuple[int, ...],
) -> None:
    """Controls consume physical slots and partial runs remain explicit."""
    result = plan_static_batches(workload(n), policy())
    checks.require_equal(result.payloads, payloads)
    checks.require_equal(sum(result.payloads), n)
    checks.require_equal(result.control_slots, len(payloads))
    checks.require_equal(
        result.available_slots,
        result.occupied_slots + result.unused_slots,
    )
    checks.require_equal(result.time_feasibility, "not_assessed")


def test_unknown_or_mixed_workloads_and_invalid_policy_fail_closed() -> None:
    """Static demand cannot hide unknown mappings, prior work or assay mixing."""
    w = workload(1)
    for change in (
        {"attempts": None},
        {"control_ids": None},
        {"cases": (w.cases[0].model_copy(update={"library_ids": None}),)},
        {"cases": (w.cases[0].model_copy(update={"assay_id": "other"}),)},
    ):
        with pytest.raises(ValueError, match=r"requires|unknown|assay"):
            plan_static_batches(w.model_copy(update=change), policy())
    with pytest.raises(ValueError, match="capacity"):
        plan_static_batches(w, policy().model_copy(update={"payload_limit": 4}))
    with pytest.raises(ValueError, match="bound"):
        plan_static_batches(workload(4), policy().model_copy(update={"max_runs": 1}))


def test_small_case_run_count_matches_finite_reachability_oracle() -> None:
    """Enumerate attainable demand independently of the packing formula."""
    for limit in range(1, 4):
        selected = policy().model_copy(update={"payload_limit": limit})
        for demand in range(7):
            reachable = {0}
            minimum = 0
            while demand not in reachable:
                reachable = {
                    total + payload
                    for total in reachable
                    for payload in range(1, limit + 1)
                }
                minimum += 1
            plan = plan_static_batches(workload(demand), selected)
            checks.require_equal(len(plan.payloads), minimum)
            checks.require_equal(plan.occupied_slots, demand + minimum)
