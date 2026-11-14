# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check deterministic release, availability and static-limit conservation."""

from decimal import Decimal

import pytest

from genomics_microcosting.dynamic_batch import (
    AvailabilityWindow,
    DynamicBatchPolicy,
    schedule_batches,
)
from genomics_microcosting.static_batch import plan_static_batches
from tests import checks
from tests.test_static_batch import policy, workload
lazy from genomics_microcosting.workload_contract import Workload


def dynamic() -> DynamicBatchPolicy:
    """Supply explicit synthetic timing assumptions."""
    batch = policy().model_copy(update={"entity_kind": "requested_tests"})
    return DynamicBatchPolicy(
        batch=batch,
        run_duration_seconds=Decimal(2),
        max_wait_seconds=Decimal(1),
        turnaround_limit_seconds=Decimal(10),
        windows=(
            AvailabilityWindow(start_seconds=Decimal(0), end_seconds=Decimal(10)),
        ),
    )


def timed(n: int) -> Workload:
    """Make all demand arrive at time zero."""
    w = workload(n)
    return w.model_copy(
        update={
            "cases": tuple(
                c.model_copy(update={"arrival_seconds": Decimal(0)}) for c in w.cases
            ),
        },
    )


def test_dynamic_static_limit_and_zero_demand() -> None:
    """Simultaneous arrivals preserve static run/control totals and demand."""
    selected = dynamic()
    for n in (0, 1, 3, 4, 6):
        w = timed(n)
        result = schedule_batches(w, selected)
        static = plan_static_batches(w, selected.batch)
        checks.require_equal(
            tuple(len(r.case_ids) for r in result.runs),
            static.payloads,
        )
        checks.require_equal(
            sum(r.control_slots for r in result.runs),
            static.control_slots,
        )
        checks.require_equal(result.feasibility, "feasible")
        checks.require_equal(result.unserved_case_ids, ())
        checks.require_equal(
            sorted(case for run in result.runs for case in run.case_ids),
            sorted(case.case_id for case in w.cases),
        )


def test_window_and_turnaround_failures_are_explicit() -> None:
    """A workload can be infeasible through unserved work or late completion."""
    selected = dynamic()
    short = selected.model_copy(
        update={
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(0), end_seconds=Decimal(3)),
            ),
        },
    )
    checks.require_equal(schedule_batches(timed(4), short).unserved_case_ids, ("c3",))
    late = selected.model_copy(update={"turnaround_limit_seconds": Decimal(3)})
    result = schedule_batches(timed(4), late)
    checks.require_equal(result.feasibility, "infeasible")
    checks.require_equal(result.turnaround_violations, ("c3",))


def test_unknown_arrivals_and_overlapping_windows_are_rejected() -> None:
    """No arrival distribution or parallel availability is silently invented."""
    with pytest.raises(ValueError, match="arrival"):
        schedule_batches(workload(1), dynamic())
    overlap = dynamic().model_copy(
        update={
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(0), end_seconds=Decimal(5)),
                AvailabilityWindow(start_seconds=Decimal(4), end_seconds=Decimal(10)),
            ),
        },
    )
    with pytest.raises(ValueError, match="window"):
        schedule_batches(timed(1), overlap)


def test_timeout_shift_wait_and_turnaround_are_deterministic() -> None:
    """Wait for availability and retain intervening arrivals."""
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(2)}),
            ),
        },
    )
    selected = dynamic().model_copy(
        update={
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(3), end_seconds=Decimal(10)),
            ),
        },
    )
    result = schedule_batches(w, selected)
    checks.require_equal(len(result.runs), 1)
    checks.require_equal(result.runs[0].case_ids, ("c0", "c1"))
    checks.require_equal(result.runs[0].start_seconds, Decimal(3))
    checks.require_equal(result.runs[0].complete_seconds, Decimal(5))
    checks.require_equal(result, schedule_batches(w, selected))


def test_release_policy_can_exhaust_run_bound_before_serving_all_cases() -> None:
    """An explicit guard returns residual work rather than dropping it."""
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    selected = dynamic()
    selected = selected.model_copy(
        update={
            "batch": selected.batch.model_copy(update={"max_runs": 1}),
        },
    )
    result = schedule_batches(w, selected)
    checks.require_equal(result.termination_reason, "run_bound")
    checks.require_equal(result.unserved_case_ids, ("c1",))
    checks.require_equal(result.feasibility, "infeasible")
