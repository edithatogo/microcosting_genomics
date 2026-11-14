# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Declared workflow cost and finite release choices preserve economic scope."""

import json
from dataclasses import replace
from datetime import date
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import ComputeCostContext
from genomics_microcosting.inventory_ledger import (
    InventoryInputs,
    WorkflowInputs,
)
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from genomics_microcosting.workflow_cost import (
    ResourcePricing,
    WorkflowCostBoundary,
    WorkflowCostInputs,
    WorkflowReleaseGrid,
    calculate_workflow_cost,
    enumerate_workflow_releases,
)
from tests import checks
from tests.test_inventory_ledger import inventory_inputs, price_inputs, restock


def cost_inputs(tmp_path: Path, basis: str = "allocated") -> WorkflowCostInputs:
    """Provide synthetic resource, fixed and lot rates."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    materials = tmp_path / "materials"
    materials.mkdir()
    pricing, material_context = price_inputs(materials)
    inventory = inventory_inputs()
    params: list[Parameter] = []
    quals: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    snapshots: dict[str, Path] = {}
    for identifier, raw, unit in [
        ("staff", "1", f"AUD/staff-slots_s:{basis}"),
        ("instrument", "2", f"AUD/instrument-slots_s:{basis}"),
        ("fixed", "5", "AUD/horizon_s:20"),
    ]:
        path = tmp_path / (identifier + ".txt")
        path.write_text(raw + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        source = SourceRecord(
            source_id=identifier,
            sha256=digest,
            edition="synthetic",
            locator="line 1",
            limitations="Not a real rate",
        )
        parameter = Parameter(
            parameter_id=identifier,
            raw_value=raw,
            derived_value=raw,
            unit=unit,
            source_sha256=digest,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="reported",
        )
        params.append(parameter)
        quals.append(
            ParameterQualification(
                parameter=parameter,
                source=source,
                exact_support=raw,
                dimensional_basis=unit,
                applicability="synthetic",
                qualification="qualified",
                blockers=(),
            ),
        )
        validity.append(
            SourceValidity(
                source=source,
                retrieved=date(2026, 11, 7),
                effective_from=date(2026, 1, 1),
                effective_until=date(2026, 12, 31),
                date_basis="synthetic",
            ),
        )
        snapshots[identifier] = path
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id="v1",
                workbook_sha256="c" * 64,
                parameters=tuple(params),
            ),
            qualifications=tuple(quals),
        ),
        snapshots,
        tuple(validity),
        date(2026, 11, 7),
    )
    resource_pricing = ResourcePricing.model_validate(
        {
            "format_version": "workflow-resource-cost-v1",
            "currency": "AUD",
            "price_year": 2026,
            "tax_basis": "exclusive",
            "horizon_seconds": "20",
            "resource_rates": [
                {"resource_id": name, "parameter_id": name, "basis": basis}
                for name in ["staff", "instrument"]
            ],
            "fixed_costs": [{"fixed_id": "admin", "parameter_id": "fixed"}],
            "material_selection": "consumed",
            "assumption_basis": "Synthetic scope",
        },
    )
    boundary = WorkflowCostBoundary.model_validate(
        {
            "scope_limit": "Only declared resource/fixed/material components",
            "assumption_basis": "Synthetic disjoint scope; unqualified",
            "assignments": [
                {
                    "domain": domain,
                    "input_id": name,
                    "component_ids": [component],
                }
                for domain, name, component in [
                    ("resource", "staff", "staff-time"),
                    ("resource", "instrument", "equipment-time"),
                    ("fixed", "admin", "other-admin"),
                    ("material", "kit", "kit-stock"),
                ]
            ],
        },
    )
    return WorkflowCostInputs(
        inventory,
        pricing,
        material_context,
        resource_pricing,
        context,
        boundary,
    )


def test_allocated_time_material_consumption_and_fixed_cost_reconcile(
    tmp_path: Path,
) -> None:
    """Queue/idle time and remaining packs are not silently charged as usage."""
    inputs = cost_inputs(tmp_path)
    result = calculate_workflow_cost(inputs)
    checks.require_equal(result.allocated_resource_value, Fraction(18))
    checks.require_equal(result.selected_resource_cost, Fraction(18))
    checks.require_equal(result.idle_capacity_value, Fraction(42))
    checks.require_equal(result.selected_idle_cost, Fraction(0))
    checks.require_equal(result.fixed_cost, Fraction(5))
    checks.require_equal(result.selected_material_cost, Fraction(10))
    checks.require_equal(result.total_selected_cost, Fraction(33))
    checks.require_equal(result.unit_cost_per_requested_test, Fraction(33, 2))
    checks.require_equal(result.eligible_for_comparison, expected=True)
    checks.require_equal(result.cost_scope, "declared_components_only")
    checks.require_equal(calculate_workflow_cost(inputs), result)


def test_available_capacity_requires_its_own_price_basis(
    tmp_path: Path,
) -> None:
    """Include chosen idle commitments without duplicate charging."""
    inputs = cost_inputs(tmp_path, "available")
    result = calculate_workflow_cost(inputs)
    checks.require_equal(result.selected_resource_cost, Fraction(60))
    checks.require_equal(result.selected_idle_cost, Fraction(42))
    checks.require_equal(result.total_selected_cost, Fraction(75))
    broken = replace(
        inputs,
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "resource_rates": tuple(
                    r.model_copy(update={"basis": "allocated"})
                    for r in inputs.resource_pricing.resource_rates
                ),
            },
        ),
    )
    with pytest.raises(ValueError, match="unit"):
        calculate_workflow_cost(broken)


def test_expiry_loss_selection_is_explicit(tmp_path: Path) -> None:
    """Retain unselected loss and its explicit cost-selection basis."""
    inputs = cost_inputs(tmp_path)
    changed = replace(
        inputs,
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "material_selection": "consumed_and_all_loss",
            },
        ),
    )
    result = calculate_workflow_cost(changed)
    checks.require_equal(result.material.expired_stock_value, Fraction(10))
    checks.require_equal(result.selected_material_cost, Fraction(20))
    checks.require_equal(result.total_selected_cost, Fraction(43))


def test_missing_resources_overlap_and_economic_bases_reject(
    tmp_path: Path,
) -> None:
    """Require complete bindings and compatible price frames."""
    inputs = cost_inputs(tmp_path)
    missing = replace(
        inputs,
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "resource_rates": inputs.resource_pricing.resource_rates[:1],
            },
        ),
    )
    with pytest.raises(ValueError, match="coverage"):
        calculate_workflow_cost(missing)
    assignments = inputs.boundary.assignments
    overlap = inputs.boundary.model_copy(
        update={
            "assignments": (
                assignments[0].model_copy(
                    update={"component_ids": ("kit-stock",)},
                ),
                *assignments[1:],
            ),
        },
    )
    with pytest.raises(ValueError, match="overlap"):
        calculate_workflow_cost(replace(inputs, boundary=overlap))
    wrong = inputs.resource_pricing.model_copy(update={"currency": "USD"})
    with pytest.raises(ValueError, match="basis"):
        calculate_workflow_cost(replace(inputs, resource_pricing=wrong))


def tradeoff_inputs(tmp_path: Path) -> WorkflowCostInputs:
    """Create an explicit lot-price, expiry and timing tradeoff."""
    inputs = cost_inputs(tmp_path)
    stock = json.loads(inputs.inventory.stock_payload)
    stock["items"][0]["open_life_seconds"] = "100"
    stock["packs"][0].update({"lot_id": "B", "sealed_expiry_seconds": "4"})
    stock["packs"][1]["lot_id"] = "A"
    inventory = restock(inputs.inventory, stock)
    workflow = inventory.workflow
    policy = workflow.policy.model_copy(
        update={"turnaround_limit_seconds": "20"},
    )
    inventory = InventoryInputs(
        WorkflowInputs(
            workflow.graph_payload,
            workflow.workload,
            policy,
            workflow.scenario,
        ),
        inventory.stock_payload,
        inventory.plan,
    )
    return replace(inputs, inventory=inventory)


def release_grid() -> WorkflowReleaseGrid:
    """Vary only one declared operational release lower bound."""
    return WorkflowReleaseGrid.model_validate(
        {
            "search_id": "release-grid",
            "assumption_basis": "Synthetic finite choices",
            "axes": [{"operation_id": "preparec2", "values": ["0", "5"]}],
        },
    )


def test_finite_release_cost_tat_frontier_and_loss_sensitivity(
    tmp_path: Path,
) -> None:
    """Retain cost/TAT tradeoffs under a fixed loss selection."""
    inputs = tradeoff_inputs(tmp_path)
    result = enumerate_workflow_releases(inputs, release_grid())
    checks.require_equal(
        tuple(p.cost.total_selected_cost for p in result.points),
        (Fraction(35), Fraction(33)),
    )
    checks.require_equal(
        tuple(p.cost.worst_turnaround_seconds for p in result.points),
        (Fraction(9), Fraction(12)),
    )
    checks.require_equal(result.pareto_indices, (0, 1))
    changed = replace(
        inputs,
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "material_selection": "consumed_and_all_loss",
            },
        ),
    )
    loss = enumerate_workflow_releases(changed, release_grid())
    checks.require_equal(
        tuple(p.cost.total_selected_cost for p in loss.points),
        (Fraction(35), Fraction(39)),
    )
    checks.require_equal(loss.pareto_indices, (0,))
    checks.require_equal(
        enumerate_workflow_releases(inputs, release_grid()),
        result,
    )


def test_cheap_material_shortage_cannot_enter_frontier(tmp_path: Path) -> None:
    """A point must satisfy stock and TAT as well as resource scheduling."""
    inputs = cost_inputs(tmp_path)
    stock = json.loads(inputs.inventory.stock_payload)
    stock["packs"][1]["arrived_seconds"] = "5"
    inventory = restock(inputs.inventory, stock)
    workflow = inventory.workflow
    policy = workflow.policy.model_copy(
        update={"turnaround_limit_seconds": "20"},
    )
    inventory = InventoryInputs(
        WorkflowInputs(
            workflow.graph_payload,
            workflow.workload,
            policy,
            workflow.scenario,
        ),
        inventory.stock_payload,
        inventory.plan,
    )
    result = enumerate_workflow_releases(
        replace(inputs, inventory=inventory),
        release_grid(),
    )
    checks.require_equal(
        result.points[0].cost.eligible_for_comparison,
        expected=False,
    )
    checks.require_equal(
        result.points[0].cost.unit_cost_per_requested_test,
        None,
    )
    checks.require_equal(result.pareto_indices, (1,))


def test_zero_demand_retains_idle_commitment_and_undefined_unit_cost(
    tmp_path: Path,
) -> None:
    """No-demand comparisons retain fixed/idle amounts and have no frontier."""
    inputs = cost_inputs(tmp_path, "available")
    inv = inputs.inventory
    w = inv.workflow
    empty = InventoryInputs(
        WorkflowInputs(
            w.graph_payload,
            w.workload.model_copy(update={"cases": ()}),
            w.policy,
            w.scenario.model_copy(update={"operations": ()}),
        ),
        inv.stock_payload,
        inv.plan,
    )
    inputs = replace(inputs, inventory=empty)
    result = calculate_workflow_cost(inputs)
    checks.require_equal(result.total_selected_cost, Fraction(65))
    checks.require_equal(result.selected_idle_cost, Fraction(60))
    checks.require_equal(result.unit_cost_per_requested_test, None)
    checks.require_equal(result.service_coverage, "no_demand")
    grid = WorkflowReleaseGrid(
        search_id="empty",
        assumption_basis="No variation",
        axes=(),
    )
    search = enumerate_workflow_releases(inputs, grid)
    checks.require_equal(search.state, "no_demand")
    checks.require_equal(search.pareto_indices, ())


def test_cheaper_late_point_is_not_eligible_and_original_inputs_stay_fixed(
    tmp_path: Path,
) -> None:
    """A finite cost search cannot weaken its fixed turnaround requirement."""
    inputs = tradeoff_inputs(tmp_path)
    inv = inputs.inventory
    w = inv.workflow
    inventory = InventoryInputs(
        WorkflowInputs(
            w.graph_payload,
            w.workload,
            w.policy.model_copy(update={"turnaround_limit_seconds": "9"}),
            w.scenario,
        ),
        inv.stock_payload,
        inv.plan,
    )
    inputs = replace(inputs, inventory=inventory)
    before = inputs.inventory.workflow.scenario.model_dump()
    result = enumerate_workflow_releases(inputs, release_grid())
    checks.require_equal(result.pareto_indices, (0,))
    checks.require_equal(
        result.points[1].cost.eligible_for_comparison,
        expected=False,
    )
    checks.require_equal(
        inputs.inventory.workflow.scenario.model_dump(),
        before,
    )
    for point in result.points:
        schedule = point.cost.material.inventory.schedule
        checks.require_equal(
            schedule.process_graph_sha256,
            w.workload.process_graph_sha256,
        )
        checks.require_equal(
            schedule.parameter_version_id,
            w.workload.parameter_version_id,
        )
        checks.require_equal(sum(r.control_slots for r in schedule.runs), 2)
        checks.require_equal(point.cost.pricing.material_selection, "consumed")


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_axis",
        "duplicate_value",
        "unknown",
        "too_many",
        "beyond_horizon",
        "empty_value",
    ],
)
def test_invalid_release_grids_reject(tmp_path: Path, kind: str) -> None:
    """Grid shape and guard limits cannot relax original release constraints."""
    inputs = cost_inputs(tmp_path)
    data = release_grid().model_dump(mode="json")
    if kind == "duplicate_axis":
        data["axes"].append(data["axes"][0])
    elif kind == "duplicate_value":
        data["axes"][0]["values"] = ["0", "0.0"]
    elif kind == "unknown":
        data["axes"][0]["operation_id"] = "missing"
    elif kind == "too_many":
        data["max_points"] = 1
    elif kind == "beyond_horizon":
        data["axes"][0]["values"] = ["21"]
    else:
        data["axes"][0]["values"] = []
    with pytest.raises(ValueError, match=r"axis|values|bound|horizon|item"):
        enumerate_workflow_releases(
            inputs,
            WorkflowReleaseGrid.model_validate(data),
        )


def test_currency_date_horizon_and_source_identity_are_not_assumed(
    tmp_path: Path,
) -> None:
    """Semantic frame mismatches and altered rate bytes stop costing."""
    inputs = cost_inputs(tmp_path)
    wrong = replace(
        inputs,
        resource_pricing=inputs.resource_pricing.model_copy(
            update={
                "horizon_seconds": "21",
            },
        ),
    )
    with pytest.raises(ValueError, match="basis"):
        calculate_workflow_cost(wrong)
    wrong = replace(
        inputs,
        resource_context=replace(
            inputs.resource_context,
            costing_date=date(2026, 11, 6),
        ),
    )
    with pytest.raises(ValueError, match="basis"):
        calculate_workflow_cost(wrong)
    inputs.resource_context.snapshots["staff"].write_text(
        "2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hash"):
        calculate_workflow_cost(inputs)


def test_original_release_bounds_and_equal_frontier_points(
    tmp_path: Path,
) -> None:
    """Do not relax source release bounds or discard nondominated ties."""
    inputs = cost_inputs(tmp_path)
    data = release_grid().model_dump(mode="json")
    data["axes"][0]["values"] = ["0", "1"]
    result = enumerate_workflow_releases(
        inputs,
        WorkflowReleaseGrid.model_validate(data),
    )
    checks.require_equal(result.pareto_indices, (0, 1))
    inv = inputs.inventory
    w = inv.workflow
    scenario = w.scenario.model_copy(
        update={
            "operations": tuple(
                op.model_copy(update={"release_seconds": "3"})
                if op.operation_id == "preparec2"
                else op
                for op in w.scenario.operations
            ),
        },
    )
    changed = InventoryInputs(
        WorkflowInputs(w.graph_payload, w.workload, w.policy, scenario),
        inv.stock_payload,
        inv.plan,
    )
    with pytest.raises(ValueError, match="lower bound"):
        enumerate_workflow_releases(
            replace(inputs, inventory=changed),
            release_grid(),
        )
