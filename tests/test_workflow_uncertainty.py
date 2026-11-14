# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Joint workflow states retain correlated service, resources and stock costs."""

import json
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.workflow_cost import (
    ResourceRateBinding,
    WorkflowComponentAssignment,
    WorkflowCostInputs,
)
from genomics_microcosting.workflow_schedule import ResourcePool, StageTiming
from genomics_microcosting.workflow_uncertainty import simulate_workflow_uncertainty
from tests import checks
from tests.test_workflow_cost import cost_inputs
from tests.test_workflow_rework import rework_data


def recipe(
    tmp_path: Path,
    inputs: WorkflowCostInputs | None = None,
) -> Path:
    """Keep normal service and failed/reworked stock shortage in separate states."""
    if inputs is None:
        inputs = cost_inputs(tmp_path / "fixture")
    workflow = inputs.inventory.workflow
    state = {
        "state_id": "normal",
        "weight": 1,
        "arrivals": [
            {"case_id": c.case_id, "seconds": "0"} for c in workflow.workload.cases
        ],
        "timings": [t.model_dump(mode="json") for t in workflow.policy.timings],
        "calendars": [
            {
                "resource_id": r.resource_id,
                "windows": [w.model_dump(mode="json") for w in r.windows],
            }
            for r in workflow.policy.resources
        ],
        "scenario": workflow.scenario.model_dump(mode="json"),
        "stock": json.loads(inputs.inventory.stock_payload),
    }
    other = json.loads(json.dumps(state))
    other.update({"state_id": "rework", "weight": 3, "scenario": rework_data()})
    path = tmp_path / "ensemble.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "joint-workflow-ensemble-v1",
                "evidence_state": "assumed",
                "assumption_basis": "Synthetic joint states",
                "states": [state, other],
            },
        ),
        encoding="utf-8",
    )
    return path


def test_joint_rework_stock_and_resource_outcomes(tmp_path: Path) -> None:
    """A resource-complete modeled rework can still be material-incomplete."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    checks.require_equal(result.draw_indices, (1, 1, 1, 1, 1, 1, 1, 0))
    checks.require_equal(
        tuple(o.cost.total_selected_cost for o in result.outcomes),
        (Fraction(33), Fraction(42)),
    )
    checks.require_equal(result.full_service_probability, Fraction(1, 4))
    checks.require_equal(result.material_fulfilled_probability, Fraction(1, 4))
    checks.require_equal(result.eligible_probability, Fraction(1, 4))
    checks.require_equal(result.mean_complete_service_cost, None)
    staff = next(r for r in result.resources if r.resource_id == "staff")
    checks.require_equal(staff.mean_utilization, Fraction(33, 80))
    checks.require_equal(staff.pooled_utilization, Fraction(33, 80))
    checks.require_equal(
        simulate_workflow_uncertainty(path, inputs, seed=7, draws=8),
        result,
    )


def test_complete_late_service_cost_mean_is_descriptive(tmp_path: Path) -> None:
    """Late complete states retain cost without becoming eligible comparisons."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    state = data["states"][1]
    scenario = state["scenario"]
    operations = scenario["operations"]
    operations[0]["members"].append(operations[1]["members"][0])
    operations.pop(1)
    operations[2]["dependencies"] = ["preparec1"]
    operations[2]["members"][0]["input_operation_ids"] = ["preparec1"]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    checks.require_equal(result.full_service_probability, Fraction(1))
    checks.require_equal(result.eligible_probability, Fraction(1, 4))
    checks.require_equal(result.mean_complete_service_cost, Fraction(36))
    checks.require_equal(result.outcomes[1].cost.total_selected_cost, Fraction(37))


@pytest.mark.parametrize(
    "fault",
    [
        "arrivals",
        "resource",
        "role",
        "item",
        "pack",
        "observed",
        "duplicate",
    ],
)
def test_joint_states_cannot_change_fixed_scope(tmp_path: Path, fault: str) -> None:
    """Freeze economic pack/role/resource scope while varying declared timing."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    state = data["states"][0]
    if fault == "arrivals":
        state["arrivals"].pop()
    elif fault == "resource":
        state["calendars"][0]["resource_id"] = "other"
    elif fault == "role":
        state["timings"][0]["needs"][0]["units"] = 2
    elif fault == "item":
        state["stock"]["items"][0]["pack_capacity"] = 5
    elif fault == "pack":
        state["stock"]["packs"][0]["lot_id"] = "other"
    elif fault == "observed":
        state["stock"]["evidence_state"] = "observed"
    else:
        state["state_id"] = data["states"][1]["state_id"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"scope|coverage|assumed|Duplicate|capacity"):
        simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)


@pytest.mark.parametrize(("seed", "draws"), [(True, 4), (1, 0), (-1, 4)])
def test_joint_sampling_bounds(tmp_path: Path, seed: int, draws: int) -> None:
    """Reject invalid bounds rather than silently changing the simulation."""
    inputs = cost_inputs(tmp_path / "prices")
    with pytest.raises(ValueError, match="sampling"):
        simulate_workflow_uncertainty(recipe(tmp_path), inputs, seed=seed, draws=draws)


def test_baseline_stock_identity_is_verified_before_realization(tmp_path: Path) -> None:
    """Assumed state rehashing cannot hide tampering of its selected baseline."""
    inputs = cost_inputs(tmp_path / "prices")
    altered = replace(
        inputs,
        inventory=replace(
            inputs.inventory,
            stock_payload=inputs.inventory.stock_payload + b"\n",
        ),
    )
    with pytest.raises(ValueError, match="source hash"):
        simulate_workflow_uncertainty(recipe(tmp_path), altered, seed=7, draws=8)


def compute_inputs(tmp_path: Path) -> WorkflowCostInputs:
    """Add a synthetic allocated compute-slot rate without CPU-time inference."""
    inputs = cost_inputs(tmp_path)
    workflow = inputs.inventory.workflow
    graph = json.loads(workflow.graph_payload)
    graph["stages"][1]["predecessors"] = ["compute"]
    graph["stages"].append(
        {
            **graph["stages"][1],
            "stage_id": "compute",
            "predecessors": ["prepare"],
            "roles": [
                {
                    "role_id": "compute",
                    "kind": "compute",
                    "capacity_unit": "compute-slots",
                },
            ],
        },
    )
    payload = json.dumps(graph).encode()
    digest = sha256(payload).hexdigest()
    resource = ResourcePool.model_validate(
        {
            "resource_id": "compute",
            "kind": "compute",
            "capacity_unit": "compute-slots",
            "capacity": 1,
            "windows": [{"start_seconds": "0", "end_seconds": "20"}],
        },
    )
    timing = StageTiming.model_validate(
        {
            "stage_id": "compute",
            "duration_seconds": "2",
            "needs": [
                {
                    "role_id": "compute",
                    "resource_id": "compute",
                    "units": 1,
                    "offset_seconds": "0",
                    "duration_seconds": "2",
                },
            ],
        },
    )
    policy = workflow.policy.model_copy(
        update={
            "process_graph_sha256": digest,
            "turnaround_limit_seconds": "20",
            "resources": (*workflow.policy.resources, resource),
            "timings": (*workflow.policy.timings, timing),
        },
    )
    scenario = workflow.scenario.model_dump(mode="json")
    for op in scenario["operations"]:
        if op["stage_id"] == "interpret":
            op["dependencies"] = ["compute" + op["members"][0]["case_id"]]
    for case in ["c1", "c2"]:
        scenario["operations"].append(
            {
                "operation_id": "compute" + case,
                "stage_id": "compute",
                "members": [{"case_id": case, "ordinal": 1, "outcome": "passed"}],
                "dependencies": ["prepare" + case],
                "release_seconds": "0",
            },
        )
    workflow = replace(
        workflow,
        graph_payload=payload,
        workload=workflow.workload.model_copy(update={"process_graph_sha256": digest}),
        policy=policy,
        scenario=type(workflow.scenario).model_validate(scenario),
    )
    context = inputs.resource_context
    path = tmp_path / "compute.txt"
    path.write_text("3\n", encoding="utf-8")
    digest = sha256(path.read_bytes()).hexdigest()
    template = context.ledger.qualifications[0]
    unit = "AUD/compute-slots_s:allocated"
    parameter = template.parameter.model_copy(
        update={
            "parameter_id": "compute",
            "raw_value": "3",
            "derived_value": "3",
            "unit": unit,
            "source_sha256": digest,
        },
    )
    source = template.source.model_copy(
        update={
            "source_id": "compute",
            "sha256": digest,
        },
    )
    qualification = template.model_copy(
        update={
            "parameter": parameter,
            "source": source,
            "exact_support": "3",
            "dimensional_basis": unit,
        },
    )
    ledger = context.ledger.model_copy(
        update={
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "parameters": (*context.ledger.parameter_set.parameters, parameter),
                },
            ),
            "qualifications": (*context.ledger.qualifications, qualification),
        },
    )
    return replace(
        inputs,
        inventory=replace(
            inputs.inventory,
            workflow=workflow,
            plan=inputs.inventory.plan.model_copy(
                update={"process_graph_sha256": workflow.workload.process_graph_sha256},
            ),
        ),
        resource_context=replace(
            context,
            ledger=ledger,
            snapshots=context.snapshots | {"compute": path},
            validity=(
                *context.validity,
                context.validity[0].model_copy(update={"source": source}),
            ),
        ),
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "resource_rates": (
                    *inputs.resource_pricing.resource_rates,
                    ResourceRateBinding(
                        resource_id="compute",
                        parameter_id="compute",
                        basis="allocated",
                    ),
                ),
            },
        ),
        boundary=inputs.boundary.model_copy(
            update={
                "assignments": (
                    *inputs.boundary.assignments,
                    WorkflowComponentAssignment(
                        domain="resource",
                        input_id="compute",
                        component_ids=("compute-time",),
                    ),
                ),
            },
        ),
    )


def test_joint_compute_staff_equipment_costs_share_fixed_economics(
    tmp_path: Path,
) -> None:
    """A longer compute reservation changes cost and queues under one graph."""
    inputs = compute_inputs(tmp_path / "prices")
    path = recipe(tmp_path, inputs)
    data = json.loads(path.read_text())
    data["states"][1]["scenario"] = data["states"][0]["scenario"]
    timing = data["states"][1]["timings"][2]
    timing["duration_seconds"] = "6"
    timing["needs"][0]["duration_seconds"] = "6"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    checks.require_equal(
        tuple(o.cost.total_selected_cost for o in result.outcomes),
        (Fraction(45), Fraction(69)),
    )
    checks.require_equal(result.mean_complete_service_cost, Fraction(63))
    checks.require_equal(result.eligible_probability, Fraction(1))
    compute = next(r for r in result.resources if r.resource_id == "compute")
    checks.require_equal(compute.mean_utilization, Fraction(1, 2))
    checks.require_equal(compute.pooled_utilization, Fraction(1, 2))


def test_zero_available_capacity_is_not_zero_utilization(tmp_path: Path) -> None:
    """A zero-denominator state leaves mean utilization undefined."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["calendars"][0]["windows"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    staff = next(r for r in result.resources if r.resource_id == "staff")
    checks.require_equal(staff.mean_utilization, None)
    checks.require_equal(staff.pooled_utilization, Fraction(3, 10))
    checks.require_equal(result.outcomes[1].cost.total_selected_cost, Fraction(5))
    checks.require_equal(result.full_service_probability, Fraction(1, 4))


def test_mean_and_pooled_resource_utilization_have_distinct_denominators(
    tmp_path: Path,
) -> None:
    """State probabilities and weighted available capacity are different bases."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["calendars"][0]["windows"][0]["end_seconds"] = "10"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    staff = next(r for r in result.resources if r.resource_id == "staff")
    checks.require_equal(staff.mean_utilization, Fraction(3, 5))
    checks.require_equal(staff.pooled_utilization, Fraction(27, 50))


def test_overridden_baseline_calendar_still_enters_input_identity(
    tmp_path: Path,
) -> None:
    """Preserve original input identity even when every state overrides a field."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    first = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    workflow = inputs.inventory.workflow
    resource = workflow.policy.resources[0].model_copy(update={"windows": ()})
    policy = workflow.policy.model_copy(
        update={
            "resources": (resource, workflow.policy.resources[1]),
        },
    )
    changed = replace(
        inputs,
        inventory=replace(inputs.inventory, workflow=replace(workflow, policy=policy)),
    )
    other = simulate_workflow_uncertainty(path, changed, seed=7, draws=8)
    checks.require_equal(first.outcomes, other.outcomes)
    if first.input_sha256 == other.input_sha256:
        pytest.fail("Original baseline policy was omitted from the input identity")


def test_expired_stock_state_keeps_resource_use_and_fixed_cost(tmp_path: Path) -> None:
    """Joint stock loss cannot turn an incomplete cohort into a cheap comparison."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    for pack in data["states"][1]["stock"]["packs"]:
        pack["sealed_expiry_seconds"] = "0"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    cost = result.outcomes[1].cost
    checks.require_equal(cost.allocated_resource_value, Fraction(27))
    checks.require_equal(cost.total_selected_cost, Fraction(32))
    checks.require_equal(sum(p.expired_units for p in cost.material.inventory.packs), 8)
    checks.require_equal(result.mean_complete_service_cost, None)
    checks.require_equal(result.material_fulfilled_probability, Fraction(1, 4))


def test_late_arrival_state_retains_unserved_cases(tmp_path: Path) -> None:
    """Assumed arrival variation never reduces the fixed requested-test cohort."""
    inputs = cost_inputs(tmp_path / "prices")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["arrivals"][1]["seconds"] = "18"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_workflow_uncertainty(path, inputs, seed=7, draws=8)
    cases = result.outcomes[1].cost.material.inventory.schedule.cases
    checks.require_equal(tuple(c.case_id for c in cases), ("c1", "c2"))
    checks.require_equal(cases[1].state, "unserved")
    checks.require_equal(result.full_service_probability, Fraction(1, 4))
    checks.require_equal(result.mean_complete_service_cost, None)


def test_every_joint_state_uses_verified_price_sources(tmp_path: Path) -> None:
    """A finite scenario recipe cannot bypass the independent pricing ledger."""
    inputs = cost_inputs(tmp_path / "prices")
    inputs.resource_context.snapshots["staff"].write_text("9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        simulate_workflow_uncertainty(recipe(tmp_path), inputs, seed=7, draws=8)
