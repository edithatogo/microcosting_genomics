# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Cross-stage rework preserves causal inputs and resource consumption."""

import json
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from typing import Any
lazy from pathlib import Path

import pytest

from genomics_microcosting.workflow_cost import (
    WorkflowReleaseGrid,
    calculate_workflow_cost,
    enumerate_workflow_releases,
)
from genomics_microcosting.workflow_schedule import (
    ReworkScenario,
    WorkflowScenario,
    schedule_workflow,
    schedule_workflow_rework,
)
from tests import checks
from tests.test_inventory_ledger import restock
from tests.test_workflow_cost import cost_inputs
from tests.test_workflow_schedule import workflow_inputs


def rework_data() -> dict[str, Any]:
    """Script one downstream failure that requires new upstream work."""
    _, _, _, original = workflow_inputs()
    data = original.model_dump(mode="json")
    data["format_version"] = "workflow-rework-v1"
    for op in data["operations"]:
        for member in op["members"]:
            member["input_operation_ids"] = list(op["dependencies"])
            member["rework_trigger_operation_id"] = None
    data["operations"][2]["members"][0]["outcome"] = "failed"
    for stage, inputs, trigger, dependencies in [
        ("prepare", [], "interpretc1", ["preparec1", "interpretc1"]),
        ("interpret", ["reprepare"], None, ["interpretc1", "reprepare"]),
    ]:
        data["operations"].append(
            {
                "operation_id": "re" + stage,
                "stage_id": stage,
                "members": [
                    {
                        "case_id": "c1",
                        "ordinal": 2,
                        "outcome": "passed",
                        "input_operation_ids": inputs,
                        "rework_trigger_operation_id": trigger,
                    },
                ],
                "release_seconds": "0",
                "dependencies": dependencies,
            },
        )
    return data


def test_cross_stage_rework_retains_all_work() -> None:
    """Failed interpretation triggers preparation then interpretation again."""
    graph, workload, policy, _ = workflow_inputs()
    scenario = ReworkScenario.model_validate(rework_data())
    result = schedule_workflow_rework(graph, workload, policy, scenario)
    times = {r.operation_id: (r.start_seconds, r.complete_seconds) for r in result.runs}
    checks.require_equal(times["reprepare"], (6, 10))
    checks.require_equal(times["reinterpret"], (10, 12))
    checks.require_equal(len(result.runs), 6)
    checks.require_equal(sum(r.control_slots for r in result.runs), 3)
    checks.require_equal(result.resources[0].allocated_unit_seconds, Fraction(9))
    checks.require_equal(result.resources[1].allocated_unit_seconds, Fraction(9))
    checks.require_equal(result.cases[0].complete_seconds, Fraction(12))
    checks.require_equal(result.feasibility, "infeasible")
    checks.require_equal(
        schedule_workflow_rework(graph, workload, policy, scenario),
        result,
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing_trigger",
        "wrong_case",
        "passed_trigger",
        "stale_final",
        "missing_input",
        "unknown_input",
        "wrong_dependencies",
        "ordinal_gap",
    ],
)
def test_rework_rejects_invalid_causality(fault: str) -> None:
    """Reject unsupported repeats, missing inputs and stale final outputs."""
    graph, workload, policy, _ = workflow_inputs()
    data = rework_data()
    repeat = data["operations"][4]
    final = data["operations"][5]
    if fault == "missing_trigger":
        repeat["members"][0]["rework_trigger_operation_id"] = None
    elif fault == "wrong_case":
        repeat["members"][0]["rework_trigger_operation_id"] = "interpretc2"
    elif fault == "passed_trigger":
        data["operations"][2]["members"][0]["outcome"] = "passed"
    elif fault == "stale_final":
        final["members"][0]["input_operation_ids"] = ["preparec1"]
        final["dependencies"] = ["interpretc1", "preparec1"]
    elif fault == "missing_input":
        final["members"][0]["input_operation_ids"] = []
    elif fault == "unknown_input":
        final["members"][0]["input_operation_ids"] = ["absent"]
    elif fault == "wrong_dependencies":
        repeat["dependencies"] = ["preparec1"]
    else:
        repeat["members"][0]["ordinal"] = 3
    with pytest.raises(
        ValueError,
        match=r"rework|Rework|attempt|extra_forbidden|causally linked",
    ):
        schedule_workflow_rework(
            graph,
            workload,
            policy,
            ReworkScenario.model_validate(data),
        )


def test_pending_rework_does_not_complete_using_old_pass() -> None:
    """Earlier successful versions cannot complete a pending final revision."""
    graph, workload, policy, _ = workflow_inputs()
    data = rework_data()
    data["operations"][4]["release_seconds"] = "20"
    result = schedule_workflow_rework(
        graph,
        workload,
        policy,
        ReworkScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "unserved")
    checks.require_equal(result.cases[0].complete_seconds, None)
    checks.require_equal(
        set(result.unserved_operation_ids),
        {"reprepare", "reinterpret"},
    )


def test_v1_remains_separate() -> None:
    """The original scheduler still rejects repetitions of passed work."""
    graph, workload, policy, original = workflow_inputs()
    checks.require_equal(
        schedule_workflow(graph, workload, policy, original),
        schedule_workflow(graph, workload, policy, original),
    )
    with pytest.raises(
        ValueError,
        match=r"rework|Rework|attempt|extra_forbidden|causally linked",
    ):
        schedule_workflow(
            graph,
            workload,
            policy,
            WorkflowScenario.model_validate(rework_data()),
        )


def test_no_rework_preserves_schedule_but_binds_new_contract() -> None:
    """Explicit input provenance changes identity without changing resource use."""
    graph, workload, policy, old = workflow_inputs()
    data = rework_data()
    data["operations"] = data["operations"][:4]
    data["operations"][2]["members"][0]["outcome"] = "passed"
    current = schedule_workflow_rework(
        graph,
        workload,
        policy,
        ReworkScenario.model_validate(data),
    )
    prior = schedule_workflow(graph, workload, policy, old)
    checks.require_equal(current.runs, prior.runs)
    checks.require_equal(current.reservations, prior.reservations)
    checks.require_equal(current.cases, prior.cases)
    checks.require_equal(current.resources, prior.resources)
    if current.input_sha256 == prior.input_sha256:
        pytest.fail("Rework provenance must enter the selected input digest")


@pytest.mark.parametrize("limit", [1, 4])
def test_operation_bound_leaves_final_versions_unserved(limit: int) -> None:
    """Truncation keeps all pending versions explicit without free completion."""
    graph, workload, policy, _ = workflow_inputs()
    result = schedule_workflow_rework(
        graph,
        workload,
        policy.model_copy(update={"max_operations": limit}),
        ReworkScenario.model_validate(rework_data()),
    )
    checks.require_equal(result.termination_reason, "operation_bound")
    checks.require_equal(result.cases[0].state, "unserved")
    checks.require_equal(result.feasibility, "infeasible")


def test_cancellation_keeps_started_failed_resources() -> None:
    """Cancelled rework consumes no new controls but keeps prior service."""
    graph, workload, policy, _ = workflow_inputs()
    data = rework_data()
    data["cancellations"] = [{"case_id": "c1", "at_seconds": "5"}]
    result = schedule_workflow_rework(
        graph,
        workload,
        policy,
        ReworkScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].state, "cancelled")
    checks.require_equal(
        {"reprepare", "reinterpret"} <= set(result.skipped_operation_ids),
        expected=True,
    )
    checks.require_equal(sum(r.control_slots for r in result.runs), 2)
    checks.require_equal(
        next(
            r.complete_seconds for r in result.runs if r.operation_id == "interpretc1"
        ),
        Fraction(6),
    )


def test_repeat_limit_cannot_be_relaxed_by_rework() -> None:
    """A source-fixed maximum attempt count applies to cross-stage repeats."""
    graph, workload, policy, _ = workflow_inputs()
    data = json.loads(graph)
    data["stages"][0]["max_attempts_per_case"] = 1
    graph = json.dumps(data).encode()
    digest = sha256(graph).hexdigest()
    with pytest.raises(ValueError, match="repeat bound"):
        schedule_workflow_rework(
            graph,
            workload.model_copy(update={"process_graph_sha256": digest}),
            policy.model_copy(update={"process_graph_sha256": digest}),
            ReworkScenario.model_validate(rework_data()),
        )


def test_rework_cost_recomputes_materials_resources_and_release_grid(
    tmp_path: Path,
) -> None:
    """Repeated service is priced once per execution with full source checks."""
    inputs = cost_inputs(tmp_path)
    workflow = replace(
        inputs.inventory.workflow,
        scenario=ReworkScenario.model_validate(rework_data()),
    )
    inventory = replace(inputs.inventory, workflow=workflow)
    stock = json.loads(inventory.stock_payload)
    stock["packs"].append({**stock["packs"][1], "pack_id": "C"})
    inputs = replace(inputs, inventory=restock(inventory, stock))
    result = calculate_workflow_cost(inputs)
    checks.require_equal(result.allocated_resource_value, Fraction(27))
    checks.require_equal(result.selected_material_cost, Fraction(16))
    checks.require_equal(result.total_selected_cost, Fraction(48))
    checks.require_equal(result.service_coverage, "all_requested_tests")
    checks.require_equal(result.material.inventory.material_status, "fulfilled")
    grid = WorkflowReleaseGrid.model_validate(
        {
            "search_id": "rework-releases",
            "assumption_basis": "Synthetic fixed rework choices",
            "max_points": 2,
            "axes": [{"operation_id": "reprepare", "values": ["0", "20"]}],
        },
    )
    search = enumerate_workflow_releases(inputs, grid)
    checks.require_equal(len(search.points), 2)
    checks.require_equal(search.points[0].cost.total_selected_cost, Fraction(48))
    checks.require_equal(
        search.points[1].cost.service_coverage,
        "partial_requested_tests",
    )


def test_transitive_failure_repeats_two_upstream_stages() -> None:
    """A third-stage failure requires both upstream versions to be renewed."""
    graph, workload, policy, _ = workflow_inputs()
    process = json.loads(graph)
    process["stages"].append(
        {
            **process["stages"][1],
            "stage_id": "confirm",
            "predecessors": ["interpret"],
        },
    )
    graph = json.dumps(process).encode()
    digest = sha256(graph).hexdigest()
    workload = workload.model_copy(
        update={
            "process_graph_sha256": digest,
            "cases": workload.cases[:1],
        },
    )
    policy = policy.model_copy(
        update={
            "process_graph_sha256": digest,
            "turnaround_limit_seconds": "20",
            "timings": (
                *policy.timings,
                policy.timings[1].model_copy(update={"stage_id": "confirm"}),
            ),
        },
    )
    data = rework_data()
    data["operations"] = [
        op for op in data["operations"] if op["members"][0]["case_id"] == "c1"
    ]
    data["operations"][1]["members"][0]["outcome"] = "passed"
    for op in data["operations"][2:]:
        op["members"][0]["rework_trigger_operation_id"] = "confirm1"
        op["dependencies"].append("confirm1")
    for ordinal, source, outcome, dependencies in [
        (1, "interpretc1", "failed", ["interpretc1"]),
        (2, "reinterpret", "passed", ["confirm1", "reinterpret"]),
    ]:
        data["operations"].append(
            {
                "operation_id": "confirm" + str(ordinal),
                "stage_id": "confirm",
                "release_seconds": "0",
                "dependencies": dependencies,
                "members": [
                    {
                        "case_id": "c1",
                        "ordinal": ordinal,
                        "outcome": outcome,
                        "input_operation_ids": [source],
                        "rework_trigger_operation_id": None,
                    },
                ],
            },
        )
    # The prepare trigger changed; remove its original direct-failure edge.
    data["operations"][2]["dependencies"].remove("interpretc1")
    result = schedule_workflow_rework(
        graph,
        workload,
        policy,
        ReworkScenario.model_validate(data),
    )
    checks.require_equal(result.cases[0].complete_seconds, Fraction(16))
    checks.require_equal(result.resources[0].allocated_unit_seconds, Fraction(10))
    checks.require_equal(len(result.runs), 6)
    checks.require_equal(result.feasibility, "feasible")


def test_rework_material_shortage_suppresses_whole_workload_cost(
    tmp_path: Path,
) -> None:
    """Posthoc stock shortage retains resource use and incomplete service."""
    inputs = cost_inputs(tmp_path)
    workflow = replace(
        inputs.inventory.workflow,
        scenario=ReworkScenario.model_validate(rework_data()),
    )
    inputs = replace(inputs, inventory=replace(inputs.inventory, workflow=workflow))
    result = calculate_workflow_cost(inputs)
    checks.require_equal(result.allocated_resource_value, Fraction(27))
    checks.require_equal(result.material.inventory.material_status, "unfilled")
    checks.require_equal(result.service_coverage, "partial_requested_tests")
    if result.reportable_cost is None:
        pytest.fail("Workflow result omitted its reportable-cost metadata")
    checks.require_equal(
        result.reportable_cost.service_scope,
        "partial_modeled_workload",
    )
