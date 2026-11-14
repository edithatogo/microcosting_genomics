# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Keep concurrent software access distinct from staff and equipment."""

import json
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256

import pytest
from pydantic import BaseModel

from genomics_microcosting.workflow_schedule import (
    ResourceSchedulePolicy,
    WorkflowScenario,
    schedule_workflow,
)
from genomics_microcosting.workload_contract import Workload
from tests import checks
from tests.test_workflow_schedule import workflow_inputs


def licence_inputs(
    *,
    licences: int = 1,
    cases: int = 3,
) -> tuple[bytes, Workload, ResourceSchedulePolicy, WorkflowScenario]:
    """Declare synthetic licence counts and holding times."""
    payload, workload, policy, scenario = workflow_inputs()
    graph = json.loads(payload)
    graph["stages"][1]["roles"].append(
        {
            "role_id": "access",
            "kind": "licence",
            "capacity_unit": "active-users",
        },
    )
    payload = json.dumps(graph).encode()
    digest = sha256(payload).hexdigest()
    data = workload.model_dump(mode="json")
    template = data["cases"][0]
    data["cases"] = [
        {**template, "case_id": f"c{i}", "requested_test_id": f"t{i}"}
        for i in range(1, cases + 1)
    ]
    data["process_graph_sha256"] = digest
    workload = Workload.model_validate(data)
    p = policy.model_dump(mode="json")
    p["process_graph_sha256"] = digest
    p["policy_id"] = f"assumed-{licences}-licences"
    for resource in p["resources"]:
        resource["capacity"] = max(cases, 1)
    p["resources"].append(
        {
            "resource_id": "access",
            "kind": "licence",
            "capacity_unit": "active-users",
            "capacity": licences,
            "windows": [{"start_seconds": "0", "end_seconds": "20"}],
        },
    )
    p["timings"][1]["needs"].append(
        {
            "role_id": "access",
            "resource_id": "access",
            "units": 1,
            "offset_seconds": "0",
            "duration_seconds": "2",
        },
    )
    policy = ResourceSchedulePolicy.model_validate(p)
    s = scenario.model_dump(mode="json")
    s["operations"] = [
        {
            "operation_id": stage + case.case_id,
            "stage_id": stage,
            "members": [
                {"case_id": case.case_id, "ordinal": 1, "outcome": "passed"},
            ],
            "release_seconds": "0",
            "dependencies": [] if stage == "prepare" else ["prepare" + case.case_id],
        }
        for stage in ("prepare", "interpret")
        for case in workload.cases
    ]
    return payload, workload, policy, WorkflowScenario.model_validate(s)


@pytest.mark.parametrize(
    ("licences", "completions", "feasibility"),
    [
        (1, [6, 8, 10], "infeasible"),
        (2, [6, 6, 8], "feasible"),
        (3, [6, 6, 6], "feasible"),
    ],
)
def test_concurrent_access_changes_waits_without_inventing_staff_work(
    licences: int,
    completions: list[int],
    feasibility: str,
) -> None:
    """Change waits/TAT while preserving modeled work reservations."""
    graph, w, p, s = licence_inputs(licences=licences)
    result = schedule_workflow(graph, w, p, s)
    checks.require_equal(
        [c.complete_seconds for c in result.cases],
        completions,
    )
    checks.require_equal(result.feasibility, feasibility)
    resources = {r.resource_id: r for r in result.resources}
    checks.require_equal(resources["access"].kind, "licence")
    checks.require_equal(
        resources["access"].allocated_unit_seconds,
        Fraction(6),
    )
    checks.require_equal(resources["staff"].allocated_unit_seconds, Fraction(9))
    reservations = [r for r in result.reservations if r.resource_id == "access"]
    occupied = [
        sum(r.units for r in reservations if r.start_seconds <= t < r.complete_seconds)
        for t in range(20)
    ]
    checks.require_equal(sum(occupied), 6)
    checks.require_equal(max(occupied) <= licences, expected=True)
    checks.require_equal(
        resources["access"].idle_unit_seconds,
        Fraction(20 * licences - 6),
    )
    checks.require_equal(sum(r.control_slots for r in result.runs), 3)


def test_access_calendar_limits_service_and_preserves_work() -> None:
    """A declared access window keeps the third operation unserved."""
    graph, w, p, s = licence_inputs()
    data = p.model_dump(mode="json")
    data["resources"][-1]["windows"] = [
        {"start_seconds": "5", "end_seconds": "10"},
    ]
    result = schedule_workflow(
        graph,
        w,
        ResourceSchedulePolicy.model_validate(data),
        s,
    )
    checks.require_equal(
        [c.state for c in result.cases],
        ["completed", "completed", "unserved"],
    )
    access = next(r for r in result.resources if r.resource_id == "access")
    checks.require_equal(access.available_unit_seconds, Fraction(5))
    checks.require_equal(access.allocated_unit_seconds, Fraction(4))
    staff = next(r for r in result.resources if r.resource_id == "staff")
    checks.require_equal(staff.allocated_unit_seconds, Fraction(7))


def test_no_access_preserves_unserved_work_and_unknown_utilization() -> None:
    """Declare unavailable access without inferring real entitlement."""
    graph, w, p, s = licence_inputs(cases=1)
    data = p.model_dump(mode="json")
    data["resources"][-1]["windows"] = []
    result = schedule_workflow(
        graph,
        w,
        ResourceSchedulePolicy.model_validate(data),
        s,
    )
    checks.require_equal(result.cases[0].state, "unserved")
    access = next(r for r in result.resources if r.resource_id == "access")
    checks.require_equal(access.utilization_fraction, None)
    checks.require_equal(access.allocated_unit_seconds, Fraction(0))


def test_no_demand_retains_declared_access_calendar() -> None:
    """Zero demand does not delete the resource or invent licensed use."""
    result = schedule_workflow(*licence_inputs(cases=0))
    checks.require_equal(result.runs, ())
    access = next(r for r in result.resources if r.resource_id == "access")
    checks.require_equal(access.idle_unit_seconds, Fraction(20))
    checks.require_equal(access.utilization_fraction, Fraction(0))


def test_failed_access_attempt_keeps_reservation_before_retry() -> None:
    """Retain separate failed and repeated access reservations."""
    graph, w, p, s = licence_inputs(cases=1)
    data = s.model_dump(mode="json")
    data["operations"][1]["members"][0]["outcome"] = "failed"
    data["operations"].append(
        {
            "operation_id": "retry",
            "stage_id": "interpret",
            "members": [{"case_id": "c1", "ordinal": 2, "outcome": "passed"}],
            "release_seconds": "0",
            "dependencies": ["preparec1", "interpretc1"],
        },
    )
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].complete_seconds, Fraction(8))
    access = next(r for r in result.resources if r.resource_id == "access")
    checks.require_equal(access.allocated_unit_seconds, Fraction(4))


def test_cancellation_does_not_refund_inflight_access() -> None:
    """The selected nonpreemptive holding assumption preserves active work."""
    graph, w, p, s = licence_inputs(cases=1)
    data = s.model_dump(mode="json")
    data["cancellations"] = [{"case_id": "c1", "at_seconds": "5"}]
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "cancelled")
    access = next(r for r in result.resources if r.resource_id == "access")
    checks.require_equal(access.allocated_unit_seconds, Fraction(2))


@pytest.mark.parametrize(
    ("field", "value"),
    [("kind", "equipment"), ("capacity_unit", "registered-users")],
)
def test_access_cannot_be_relabelled_equipment_or_registered_users(
    field: str,
    value: str,
) -> None:
    """Reject implicit conversions between kinds and capacity units."""
    graph, w, p, s = licence_inputs()
    data = p.model_dump(mode="json")
    data["resources"][-1][field] = value
    with pytest.raises(ValueError, match="kind/unit"):
        schedule_workflow(
            graph,
            w,
            ResourceSchedulePolicy.model_validate(data),
            s,
        )


def encode_legacy_result(value: object) -> object:
    """Keep nested member records in the complete prior-result fingerprint."""
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(type(value).__name__)


def test_prior_graph_result_and_input_identity_remain_exact() -> None:
    """Retain a complete old-domain result captured from the preceding wheel."""
    result = schedule_workflow(*workflow_inputs())
    encoded = json.dumps(
        asdict(result),
        sort_keys=True,
        default=encode_legacy_result,
    )
    checks.require_equal(
        result.input_sha256,
        "7a3bea44786558a5a76dcfba7e81d7f5b19f8b657c226970666fcb64fde69322",
    )
    checks.require_equal(
        sha256(encoded.encode()).hexdigest(),
        "5f50ef62e3ef8032bd3000960887064903107a94975c6365781d49fba64f2f60",
    )
