# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Fixed process graphs and shared resources preserve work and failure scope."""

import json
from fractions import Fraction
from hashlib import sha256

import pytest

from genomics_microcosting.static_batch import (
    StaticBatchPolicy,
    plan_static_batches,
)
from genomics_microcosting.workflow_schedule import (
    ResourceSchedulePolicy,
    WorkflowScenario,
    schedule_workflow,
)
from genomics_microcosting.workload_contract import Workload
from tests import checks


def workflow_inputs() -> tuple[
    bytes,
    Workload,
    ResourceSchedulePolicy,
    WorkflowScenario,
]:
    """Provide two assays on an explicit shared two-stage assumed graph."""
    graph = {
        "format_version": "batch-process-graph-v1",
        "process_id": "process1",
        "evidence_state": "assumed",
        "assumption_basis": "Synthetic only",
        "stages": [
            {
                "stage_id": name,
                "predecessors": predecessors,
                "assay_ids": ["a", "b"],
                "mixing_mode": "declared_compatible",
                "capacity": 4,
                "payload_limit_bound": 3,
                "controls_per_run": controls,
                "max_attempts_per_case": 2,
                "roles": roles,
            }
            for name, predecessors, controls, roles in [
                (
                    "prepare",
                    [],
                    1,
                    [
                        {
                            "role_id": "hands",
                            "kind": "staff",
                            "capacity_unit": "staff-slots",
                        },
                        {
                            "role_id": "machine",
                            "kind": "equipment",
                            "capacity_unit": "instrument-slots",
                        },
                    ],
                ),
                (
                    "interpret",
                    ["prepare"],
                    0,
                    [
                        {
                            "role_id": "review",
                            "kind": "staff",
                            "capacity_unit": "staff-slots",
                        },
                    ],
                ),
            ]
        ],
    }
    payload = json.dumps(graph).encode()
    workload = Workload.model_validate(
        {
            "workload_id": "w",
            "process_id": "process1",
            "process_graph_sha256": sha256(payload).hexdigest(),
            "parameter_version_id": "v1",
            "horizon_seconds": "20",
            "control_ids": [],
            "attempts": [],
            "cases": [
                {
                    "case_id": case,
                    "requested_test_id": "test-" + case,
                    "assay_id": assay,
                    "arrival_seconds": "0",
                    "patient_ids": None,
                    "family_ids": None,
                    "specimen_ids": None,
                    "library_ids": None,
                    "reportable_result_ids": None,
                }
                for case, assay in [("c1", "a"), ("c2", "b")]
            ],
        },
    )
    policy = ResourceSchedulePolicy.model_validate(
        {
            "format_version": "resource-schedule-v1",
            "policy_id": "policy1",
            "assumption_basis": "Synthetic resource/timing assumptions",
            "process_graph_sha256": sha256(payload).hexdigest(),
            "parameter_version_id": "v1",
            "turnaround_limit_seconds": "9",
            "max_operations": 20,
            "resources": [
                {
                    "resource_id": name,
                    "kind": kind,
                    "capacity_unit": name + "-slots",
                    "capacity": 1,
                    "windows": [{"start_seconds": "0", "end_seconds": "20"}],
                }
                for name, kind in [
                    ("staff", "staff"),
                    ("instrument", "equipment"),
                ]
            ],
            "timings": [
                {
                    "stage_id": "prepare",
                    "duration_seconds": "4",
                    "needs": [
                        {
                            "role_id": "hands",
                            "resource_id": "staff",
                            "units": 1,
                            "offset_seconds": "0",
                            "duration_seconds": "1",
                        },
                        {
                            "role_id": "machine",
                            "resource_id": "instrument",
                            "units": 1,
                            "offset_seconds": "1",
                            "duration_seconds": "3",
                        },
                    ],
                },
                {
                    "stage_id": "interpret",
                    "duration_seconds": "2",
                    "needs": [
                        {
                            "role_id": "review",
                            "resource_id": "staff",
                            "units": 1,
                            "offset_seconds": "0",
                            "duration_seconds": "2",
                        },
                    ],
                },
            ],
        },
    )
    operations = [
        {
            "operation_id": stage + case,
            "stage_id": stage,
            "members": [{"case_id": case, "ordinal": 1, "outcome": "passed"}],
            "release_seconds": "0",
            "dependencies": [] if stage == "prepare" else ["prepare" + case],
        }
        for stage in ["prepare", "interpret"]
        for case in ["c1", "c2"]
    ]
    scenario = WorkflowScenario.model_validate(
        {
            "scenario_id": "scenario1",
            "parameter_version_id": "v1",
            "evidence_state": "assumed",
            "assumption_basis": "Scripted outcomes",
            "operations": operations,
            "cancellations": [],
        },
    )
    return payload, workload, policy, scenario


def test_shared_staff_and_unattended_equipment_overlap() -> None:
    """Release staff during unattended equipment service."""
    graph, w, p, s = workflow_inputs()
    result = schedule_workflow(graph, w, p, s)
    times = {
        run.operation_id: (run.start_seconds, run.complete_seconds)
        for run in result.runs
    }
    checks.require_equal(
        times,
        {
            "preparec1": (0, 4),
            "preparec2": (3, 7),
            "interpretc1": (4, 6),
            "interpretc2": (7, 9),
        },
    )
    checks.require_equal(
        tuple(c.state for c in result.cases),
        ("completed", "completed"),
    )
    totals = {r.resource_id: r for r in result.resources}
    checks.require_equal(totals["staff"].allocated_unit_seconds, Fraction(6))
    checks.require_equal(
        totals["instrument"].allocated_unit_seconds,
        Fraction(6),
    )
    checks.require_equal(totals["staff"].idle_unit_seconds, Fraction(14))
    checks.require_equal(sum(run.control_slots for run in result.runs), 2)
    checks.require_equal(result.feasibility, "feasible")
    checks.require_equal(schedule_workflow(graph, w, p, s), result)


def test_scripted_failed_run_and_retry_consume_resources_and_controls() -> None:
    """Retain failed work and the fixed retry predecessor."""
    graph, w, p, s = workflow_inputs()
    data = s.model_dump(mode="json")
    data["operations"][0]["members"][0]["outcome"] = "failed"
    data["operations"][2]["dependencies"] = ["retry-c1"]
    data["operations"].append(
        {
            "operation_id": "retry-c1",
            "stage_id": "prepare",
            "members": [{"case_id": "c1", "ordinal": 2, "outcome": "passed"}],
            "release_seconds": "0",
            "dependencies": ["preparec1"],
        },
    )
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(len(result.runs), 5)
    checks.require_equal(sum(run.control_slots for run in result.runs), 3)
    checks.require_equal(result.cases[0].complete_seconds, Fraction(12))
    checks.require_equal(result.cases[0].turnaround_violation, expected=True)
    checks.require_equal(result.feasibility, "infeasible")


@pytest.mark.parametrize(
    ("at", "prepare_count", "staff_seconds"),
    [
        ("0", 1, 3),
        ("2", 2, 4),
    ],
)
def test_cancellation_preserves_inflight_work(
    at: str,
    prepare_count: int,
    staff_seconds: int,
) -> None:
    """Cancel future work while retaining active reservations."""
    graph, w, p, s = workflow_inputs()
    s = s.model_copy(
        update={"cancellations": ({"case_id": "c1", "at_seconds": at},)},
    )
    result = schedule_workflow(graph, w, p, s)
    checks.require_equal(result.cases[0].state, "cancelled")
    checks.require_equal(
        sum(r.stage_id == "prepare" for r in result.runs),
        prepare_count,
    )
    checks.require_equal(
        result.resources[0].allocated_unit_seconds,
        Fraction(staff_seconds),
    )
    checks.require_equal(
        "interpretc1" in result.skipped_operation_ids,
        expected=True,
    )


def test_source_graph_and_required_stage_cannot_be_optimized_away() -> None:
    """Graph bytes and complete essential stage coverage are fixed inputs."""
    graph, w, p, s = workflow_inputs()
    with pytest.raises(ValueError, match="graph hash"):
        schedule_workflow(graph + b"\n", w, p, s)
    missing = s.model_copy(update={"operations": s.operations[:2]})
    with pytest.raises(ValueError, match="stage coverage"):
        schedule_workflow(graph, w, p, missing)
    data = s.model_dump(mode="json")
    data["operations"][2]["dependencies"] = []
    with pytest.raises(ValueError, match="dependencies"):
        schedule_workflow(graph, w, p, WorkflowScenario.model_validate(data))


def test_no_window_and_guard_leave_work_explicitly_unserved() -> None:
    """Retain residual work when capacity or the guard is exhausted."""
    graph, w, p, s = workflow_inputs()
    no_window = p.resources[1].model_copy(update={"windows": ()})
    p = p.model_copy(update={"resources": (p.resources[0], no_window)})
    result = schedule_workflow(graph, w, p, s)
    checks.require_equal(len(result.unserved_operation_ids), 4)
    checks.require_equal(
        tuple(c.state for c in result.cases),
        ("unserved", "unserved"),
    )
    graph, w, p, s = workflow_inputs()
    result = schedule_workflow(
        graph,
        w,
        p.model_copy(update={"max_operations": 1}),
        s,
    )
    checks.require_equal(result.termination_reason, "operation_bound")
    checks.require_equal(len(result.runs), 1)


def test_overlapping_role_claims_respect_same_resource_capacity() -> None:
    """Two roles on the same staff pool compete even inside one operation."""
    graph, w, p, s = workflow_inputs()
    data = json.loads(graph)
    data["stages"][0]["roles"][1]["kind"] = "staff"
    data["stages"][0]["roles"][1]["capacity_unit"] = "staff-slots"
    graph = json.dumps(data).encode()
    digest = sha256(graph).hexdigest()
    w = w.model_copy(update={"process_graph_sha256": digest})
    t = p.timings[0]
    needs = (
        t.needs[0].model_copy(update={"duration_seconds": "4"}),
        t.needs[1].model_copy(update={"resource_id": "staff"}),
    )
    t = t.model_copy(update={"needs": needs})
    p = p.model_copy(
        update={"process_graph_sha256": digest, "timings": (t, p.timings[1])},
    )
    result = schedule_workflow(graph, w, p, s)
    checks.require_equal(len(result.runs), 0)


def test_partial_or_failed_scenario_does_not_report_a_completed_case() -> None:
    """Block descendants after unrecovered failure."""
    graph, w, p, s = workflow_inputs()
    data = s.model_dump(mode="json")
    data["operations"][0]["members"][0]["outcome"] = "failed"
    data["operations"] = [
        op for op in data["operations"] if op["operation_id"] != "interpretc1"
    ]
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "failed")
    checks.require_equal(result.cases[0].complete_seconds, None)
    checks.require_equal(result.cases[1].state, "completed")


def test_retry_failure_is_independent_of_source_operation_order() -> None:
    """An unsorted recipe still identifies the final failed stage attempt."""
    graph, w, p, s = workflow_inputs()
    data = s.model_dump(mode="json")
    data["operations"][0]["members"][0]["outcome"] = "failed"
    data["operations"] = [
        o for o in data["operations"] if o["operation_id"] != "interpretc1"
    ]
    data["operations"].insert(
        0,
        {
            "operation_id": "retry-c1",
            "stage_id": "prepare",
            "members": [{"case_id": "c1", "ordinal": 2, "outcome": "failed"}],
            "release_seconds": "0",
            "dependencies": ["preparec1"],
        },
    )
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "failed")
    checks.require_equal(sum(r.control_slots for r in result.runs), 3)


def test_cancelled_blocked_predecessor_does_not_deadlock_shared_batch() -> None:
    """Resolve cancelled work before it becomes stage-ready."""
    graph, w, p, s = workflow_inputs()
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0].model_copy(update={"arrival_seconds": "19"}),
                w.cases[1],
            ),
        },
    )
    data = s.model_dump(mode="json")
    data["operations"] = [
        *data["operations"][:2],
        {
            "operation_id": "shared-interpret",
            "stage_id": "interpret",
            "members": [
                {"case_id": c, "ordinal": 1, "outcome": "passed"} for c in ["c1", "c2"]
            ],
            "release_seconds": "0",
            "dependencies": ["preparec1", "preparec2"],
        },
    ]
    data["cancellations"] = [{"case_id": "c1", "at_seconds": "1"}]
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "cancelled")
    checks.require_equal(result.cases[1].complete_seconds, Fraction(6))
    checks.require_equal(result.unserved_operation_ids, ())
    checks.require_equal(
        tuple(m.case_id for m in result.runs[-1].members),
        ("c2",),
    )


@pytest.mark.parametrize(
    ("cancel_at", "expected"),
    [("6", "cancelled"), ("7", "completed")],
)
def test_cancellation_completion_tie_is_explicit(
    cancel_at: str,
    expected: str,
) -> None:
    """Define completion ties without refunding active work."""
    graph, w, p, s = workflow_inputs()
    data = s.model_dump(mode="json")
    data["cancellations"] = [{"case_id": "c1", "at_seconds": cancel_at}]
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, expected)
    checks.require_equal(
        sum(r.resource_id == "staff" for r in result.reservations),
        4,
    )


def test_compatible_mixed_batch_shares_one_run_and_fixed_controls() -> None:
    """Require graph compatibility for mixed batches."""
    graph, w, p, s = workflow_inputs()
    data = s.model_dump(mode="json")
    data["operations"] = [
        {
            "operation_id": stage,
            "stage_id": stage,
            "members": [
                {"case_id": c, "ordinal": 1, "outcome": "passed"} for c in ["c1", "c2"]
            ],
            "release_seconds": "0",
            "dependencies": [] if stage == "prepare" else ["prepare"],
        }
        for stage in ["prepare", "interpret"]
    ]
    result = schedule_workflow(
        graph,
        w,
        p,
        WorkflowScenario.model_validate(data),
    )
    checks.require_equal(len(result.runs), 2)
    checks.require_equal(sum(r.control_slots for r in result.runs), 1)
    checks.require_equal(
        tuple(c.complete_seconds for c in result.cases),
        (6, 6),
    )
    g = json.loads(graph)
    g["stages"][0]["mixing_mode"] = "homogeneous"
    graph = json.dumps(g).encode()
    digest = sha256(graph).hexdigest()
    w = w.model_copy(update={"process_graph_sha256": digest})
    p = p.model_copy(update={"process_graph_sha256": digest})
    with pytest.raises(ValueError, match="mixing"):
        schedule_workflow(graph, w, p, WorkflowScenario.model_validate(data))


def test_zero_demand_and_capacity_time_conservation() -> None:
    """Retain idle capacity and verify all occupied unit ticks."""
    graph, w, p, s = workflow_inputs()
    result = schedule_workflow(graph, w, p, s)
    for resource, total in zip(p.resources, result.resources, strict=True):
        occupied = 0
        for tick in range(20):
            active = sum(
                r.units
                for r in result.reservations
                if r.resource_id == resource.resource_id
                and r.start_seconds <= tick < r.complete_seconds
            )
            if active > resource.capacity:
                pytest.fail("Independent tick oracle found resource overload")
            occupied += active
        checks.require_equal(total.allocated_unit_seconds, Fraction(occupied))
        checks.require_equal(
            total.allocated_unit_seconds + total.idle_unit_seconds,
            total.available_unit_seconds,
        )
    w = w.model_copy(update={"cases": ()})
    s = s.model_copy(update={"operations": ()})
    empty = schedule_workflow(graph, w, p, s)
    checks.require_equal(empty.runs, ())
    checks.require_equal(empty.resources[0].idle_unit_seconds, Fraction(20))


def test_integer_calendar_start_oracle() -> None:
    """An independent finite time grid checks resource-offset feasibility."""
    graph, w, p, s = workflow_inputs()
    g = json.loads(graph)
    g["stages"] = g["stages"][:1]
    graph = json.dumps(g).encode()
    digest = sha256(graph).hexdigest()
    w = w.model_copy(
        update={"process_graph_sha256": digest, "cases": w.cases[:1]},
    )
    instrument = p.resources[1].model_copy(
        update={"windows": ({"start_seconds": "2", "end_seconds": "7"},)},
    )
    p = p.model_copy(
        update={
            "process_graph_sha256": digest,
            "timings": p.timings[:1],
            "resources": (p.resources[0], instrument),
        },
    )
    horizon, window_start, window_end = 20, 2, 7
    for release in range(9):
        data = s.model_dump(mode="json")
        data["operations"] = data["operations"][:1]
        data["operations"][0]["release_seconds"] = str(release)
        result = schedule_workflow(
            graph,
            w,
            p,
            WorkflowScenario.model_validate(data),
        )
        feasible = [
            start
            for start in range(release, 21)
            if start + 4 <= horizon
            and all(
                window_start <= tick < window_end
                for tick in range(start + 1, start + 4)
            )
        ]
        checks.require_equal(
            tuple(r.start_seconds for r in result.runs),
            (Fraction(feasible[0]),) if feasible else (),
        )


def test_single_stage_static_limit_zero_capacity_and_partial_runs() -> None:
    """Preserve existing static payload and control totals."""
    graph, w, p, s = workflow_inputs()
    data = json.loads(graph)
    data["stages"] = data["stages"][:1]
    data["stages"][0]["roles"] = data["stages"][0]["roles"][1:]
    graph = json.dumps(data).encode()
    digest = sha256(graph).hexdigest()
    w = w.model_copy(update={"process_graph_sha256": digest})
    policy_data = p.model_dump(mode="json")
    policy_data["process_graph_sha256"] = digest
    policy_data["resources"] = policy_data["resources"][1:]
    policy_data["timings"] = [
        {
            "stage_id": "prepare",
            "duration_seconds": "2",
            "needs": [
                {
                    "role_id": "machine",
                    "resource_id": "instrument",
                    "units": 1,
                    "offset_seconds": "0",
                    "duration_seconds": "2",
                },
            ],
        },
    ]
    p = ResourceSchedulePolicy.model_validate(policy_data)
    static_policy = StaticBatchPolicy(
        policy_id="static-limit",
        process_id=w.process_id,
        assay_id="a",
        entity_kind="requested_tests",
        capacity=4,
        controls_per_run=1,
        payload_limit=3,
        max_runs=20,
        assumption_basis="Synthetic limit",
    )
    for count in (0, 1, 3, 4, 6):
        cases = tuple(
            w.cases[0].model_copy(
                update={
                    "case_id": f"c{i}",
                    "requested_test_id": f"test{i}",
                },
            )
            for i in range(count)
        )
        current = w.model_copy(update={"cases": cases})
        static = plan_static_batches(current, static_policy)
        operations: list[dict[str, object]] = []
        consumed = 0
        for index, payload in enumerate(static.payloads):
            operations.append(
                {
                    "operation_id": f"run{index}",
                    "stage_id": "prepare",
                    "members": [
                        {
                            "case_id": case.case_id,
                            "ordinal": 1,
                            "outcome": "passed",
                        }
                        for case in cases[consumed : consumed + payload]
                    ],
                    "release_seconds": "0",
                    "dependencies": [],
                },
            )
            consumed += payload
        scenario = WorkflowScenario.model_validate(
            {**s.model_dump(), "operations": operations},
        )
        result = schedule_workflow(graph, current, p, scenario)
        checks.require_equal(
            tuple(len(r.members) for r in result.runs),
            static.payloads,
        )
        checks.require_equal(
            sum(r.control_slots for r in result.runs),
            static.control_slots,
        )
        checks.require_equal(
            result.resources[0].allocated_unit_seconds,
            Fraction(2 * len(static.payloads)),
        )


@pytest.mark.parametrize("kind", ["cycle", "duplicate_json", "window_overlap"])
def test_invalid_graph_and_calendars_fail_closed(kind: str) -> None:
    """Structural ambiguity and overlapping calendars never become capacity."""
    graph, w, p, s = workflow_inputs()
    if kind == "window_overlap":
        data = p.model_dump(mode="json")
        data["resources"][0]["windows"] = [
            {"start_seconds": "0", "end_seconds": "10"},
            {"start_seconds": "9", "end_seconds": "20"},
        ]
        with pytest.raises(ValueError, match="windows"):
            ResourceSchedulePolicy.model_validate(data)
        return
    if kind == "cycle":
        data = json.loads(graph)
        data["stages"][0]["predecessors"] = ["interpret"]
        graph = json.dumps(data).encode()
    else:
        graph = graph.replace(
            b'"process_id": "process1"',
            b'"process_id": "process1", "process_id": "process1"',
        )
    digest = sha256(graph).hexdigest()
    w = w.model_copy(update={"process_graph_sha256": digest})
    p = p.model_copy(update={"process_graph_sha256": digest})
    with pytest.raises(ValueError, match=r"cycle|Duplicate.*JSON"):
        schedule_workflow(graph, w, p, s)


def test_downstream_compute_capacity_and_unit_identity() -> None:
    """Compute bottlenecks retain staff release and cannot become GPU slots."""
    graph, w, p, s = workflow_inputs()
    g = json.loads(graph)
    compute = {
        **g["stages"][1],
        "stage_id": "compute",
        "predecessors": ["prepare"],
        "roles": [
            {
                "role_id": "cpu",
                "kind": "compute",
                "capacity_unit": "vCPU-slots",
            },
        ],
    }
    g["stages"][1]["predecessors"] = ["compute"]
    g["stages"].insert(1, compute)
    graph = json.dumps(g).encode()
    digest = sha256(graph).hexdigest()
    w = w.model_copy(update={"process_graph_sha256": digest})
    data = p.model_dump(mode="json")
    data["process_graph_sha256"] = digest
    data["resources"].append(
        {
            "resource_id": "cpu",
            "kind": "compute",
            "capacity_unit": "vCPU-slots",
            "capacity": 1,
            "windows": [{"start_seconds": "0", "end_seconds": "20"}],
        },
    )
    data["timings"].append(
        {
            "stage_id": "compute",
            "duration_seconds": "2",
            "needs": [
                {
                    "role_id": "cpu",
                    "resource_id": "cpu",
                    "units": 1,
                    "offset_seconds": "0",
                    "duration_seconds": "2",
                },
            ],
        },
    )
    p = ResourceSchedulePolicy.model_validate(data)
    recipe = s.model_dump(mode="json")
    for op in recipe["operations"]:
        if op["stage_id"] == "interpret":
            op["dependencies"] = ["compute" + op["members"][0]["case_id"]]
    recipe["operations"].extend(
        {
            "operation_id": "compute" + c,
            "stage_id": "compute",
            "members": [{"case_id": c, "ordinal": 1, "outcome": "passed"}],
            "release_seconds": "0",
            "dependencies": ["prepare" + c],
        }
        for c in ["c1", "c2"]
    )
    scenario = WorkflowScenario.model_validate(recipe)
    result = schedule_workflow(graph, w, p, scenario)
    checks.require_equal(
        tuple(c.complete_seconds for c in result.cases),
        (8, 11),
    )
    checks.require_equal(
        result.resources[-1].allocated_unit_seconds,
        Fraction(4),
    )
    checks.require_equal(result.resources[-1].capacity_unit, "vCPU-slots")
    checks.require_equal(result.workload_id, w.workload_id)
    checks.require_equal(result.process_graph_sha256, digest)
    data["resources"][-1]["capacity_unit"] = "GPU-slots"
    with pytest.raises(ValueError, match="kind/unit"):
        schedule_workflow(
            graph,
            w,
            ResourceSchedulePolicy.model_validate(data),
            scenario,
        )
