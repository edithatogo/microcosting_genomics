# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Retain exact finite-horizon use, slot fill and queue waits in joint states."""

import json
from decimal import Decimal
from fractions import Fraction
lazy from pathlib import Path

import pytest

from genomics_microcosting.batch_uncertainty import simulate_batch_uncertainty
from tests.checks import require_equal
from tests.test_batch_uncertainty import recipe
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


@pytest.mark.parametrize("end", ["1e1000", "1e-1000", "9." + "1" * 129])
def test_resource_time_conversion_has_explicit_numeric_bounds(
    tmp_path: Path,
    end: str,
) -> None:
    """Reject oversized exact-integer construction before deriving fractions."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    for state in data["states"]:
        state["windows"] = [{"start_seconds": "0", "end_seconds": end}]
    path.write_text(json.dumps(data), encoding="utf-8")
    workload = timed(2).model_copy(
        update={
            "horizon_seconds": max(Decimal(10), Decimal(end)),
        },
    )
    with pytest.raises(ValueError, match=r"resource time.*bounds"):
        simulate_batch_uncertainty(
            path,
            workload,
            dynamic(),
            pricing,
            context,
            seed=7,
            draws=2,
        )


def test_resource_time_and_slot_distributions_are_separate(tmp_path: Path) -> None:
    """Machine busy time, payload fill and controls are distinct quantities."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    result = simulate_batch_uncertainty(
        recipe(tmp_path),
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=8,
    )
    first, second = (o.resource_use for o in result.outcomes)
    if first is None or second is None:
        raise AssertionError
    require_equal(
        (first.available_seconds, first.busy_seconds, first.idle_seconds),
        (Fraction(10), Fraction(2), Fraction(8)),
    )
    require_equal(
        (second.available_seconds, second.busy_seconds, second.idle_seconds),
        (Fraction(10), Fraction(6), Fraction(4)),
    )
    require_equal(first.resource_utilization, Fraction(1, 5))
    require_equal(second.resource_utilization, Fraction(3, 5))
    require_equal(first.payload_slot_fill, Fraction(2, 3))
    require_equal(first.occupied_slot_fill, Fraction(3, 4))
    require_equal(second.payload_slot_fill, Fraction(1, 3))
    require_equal(second.occupied_slot_fill, Fraction(1, 2))
    require_equal(first.served_queue_waits, (("c0", Fraction(1)), ("c1", Fraction(1))))
    require_equal(result.mean_resource_utilization, Fraction(1, 2))
    require_equal(result.pooled_resource_utilization, Fraction(1, 2))
    require_equal(result.mean_complete_service_queue_wait_seconds, Fraction(1))
    require_equal(result.resource_summary_version, "batch-resource-summary-v1")


def test_mean_and_pooled_utilization_have_distinct_denominators(tmp_path: Path) -> None:
    """A mean of state fractions is not a ratio of weighted capacity totals."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["windows"][0]["end_seconds"] = "8"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=1,
    )
    require_equal(result.draw_indices, (1,))
    require_equal(result.mean_resource_utilization, Fraction(49, 80))
    require_equal(result.pooled_resource_utilization, Fraction(10, 17))
    require_equal(result.feasible_probability, Fraction(1))


def test_no_available_time_is_unknown_not_zero_utilization(tmp_path: Path) -> None:
    """Partial service cannot create a whole-workload waiting-time average."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["windows"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    use = result.outcomes[1].resource_use
    if use is None:
        raise AssertionError
    require_equal(
        (use.available_seconds, use.busy_seconds, use.idle_seconds),
        (0, 0, 0),
    )
    require_equal(use.resource_utilization, None)
    require_equal(use.payload_slot_fill, None)
    require_equal(use.occupied_slot_fill, None)
    require_equal(use.served_queue_waits, ())
    require_equal(result.mean_resource_utilization, None)
    require_equal(result.pooled_resource_utilization, Fraction(1, 5))
    require_equal(result.mean_complete_service_queue_wait_seconds, None)
    require_equal(result.mean_complete_service_cost, None)


def test_zero_demand_retains_idle_and_undefined_slot_fill(tmp_path: Path) -> None:
    """No requested cases still permits available idle time and fixed cost."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    for state in data["states"]:
        state["arrivals"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(0),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    for outcome in result.outcomes:
        use = outcome.resource_use
        if use is None:
            raise AssertionError
        require_equal((use.busy_seconds, use.idle_seconds), (0, 10))
        require_equal(use.resource_utilization, Fraction(0))
        require_equal(use.occupied_slot_fill, None)
        require_equal(outcome.result.cost.unit_cost, None)
    require_equal(result.mean_complete_service_cost, Fraction(10))
    require_equal(result.mean_complete_service_queue_wait_seconds, None)
    require_equal(result.mean_resource_utilization, Fraction(0))


def test_partial_served_waits_do_not_hide_unserved_cases(tmp_path: Path) -> None:
    """Retain observed run use while refusing a survivor-only waiting mean."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["windows"] = [{"start_seconds": "0", "end_seconds": "4"}]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    state = result.outcomes[1]
    use = state.resource_use
    if use is None:
        raise AssertionError
    require_equal(state.result.schedule.unserved_case_ids, ("c1",))
    require_equal(use.served_queue_waits, (("c0", Fraction(1)),))
    require_equal(
        (use.available_seconds, use.busy_seconds, use.idle_seconds),
        (4, 3, 1),
    )
    require_equal(result.mean_complete_service_queue_wait_seconds, None)
    require_equal(result.mean_complete_service_cost, None)
    require_equal(result.pooled_resource_utilization, Fraction(1, 2))


def test_entirely_unavailable_ensemble_has_no_utilization_denominator(
    tmp_path: Path,
) -> None:
    """Unavailable work is retained without inventing a zero utilization rate."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    for state in data["states"]:
        state["windows"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    require_equal(result.mean_resource_utilization, None)
    require_equal(result.pooled_resource_utilization, None)
    require_equal(result.mean_complete_service_queue_wait_seconds, None)
    require_equal(result.feasible_probability, Fraction(0))
    require_equal(result.mean_complete_service_cost, None)
    require_equal(tuple(o.result.cost.total_cost for o in result.outcomes), (10, 10))


def test_shift_wait_is_not_paid_labour_or_machine_busy_time(tmp_path: Path) -> None:
    """Only scheduled runs consume modeled machine time; gaps are unavailable."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][0]["windows"] = [
        {"start_seconds": "0", "end_seconds": "2"},
        {"start_seconds": "5", "end_seconds": "10"},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    use = result.outcomes[0].resource_use
    if use is None:
        raise AssertionError
    require_equal(
        (use.available_seconds, use.busy_seconds, use.idle_seconds),
        (7, 2, 5),
    )
    require_equal(use.resource_utilization, Fraction(2, 7))
    require_equal(use.served_queue_waits, (("c0", Fraction(5)), ("c1", Fraction(5))))
    require_equal(result.mean_complete_service_queue_wait_seconds, Fraction(2))
    require_equal(
        tuple(o.result.cost.total_cost for o in result.outcomes),
        (Decimal("39.5"), Decimal(65)),
    )


def test_late_complete_states_are_not_dropped_from_utilization(tmp_path: Path) -> None:
    """Feasibility and observed scenario resource accounting stay separate."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    policy = dynamic().model_copy(update={"turnaround_limit_seconds": Decimal(3)})
    result = simulate_batch_uncertainty(
        recipe(tmp_path),
        timed(2),
        policy,
        pricing,
        context,
        seed=7,
        draws=2,
    )
    require_equal(result.feasible_probability, Fraction(1, 4))
    require_equal(result.mean_resource_utilization, Fraction(1, 2))
    require_equal(result.mean_complete_service_queue_wait_seconds, Fraction(1))


def test_resource_summary_keeps_exact_subsecond_window_values(tmp_path: Path) -> None:
    """Do not round metric arithmetic through the ambient Decimal context."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    start = "3.0000000000000000000000000000001"
    data["states"][0]["windows"] = [{"start_seconds": start, "end_seconds": "10"}]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=2,
    )
    use = result.outcomes[0].resource_use
    if use is None:
        raise AssertionError
    available = Fraction(10) - Fraction(start)
    require_equal(use.available_seconds, available)
    require_equal(use.idle_seconds + use.busy_seconds, available)
    require_equal(use.resource_utilization, Fraction(2) / available)
    require_equal(use.served_queue_waits[0][1], Fraction(start))
