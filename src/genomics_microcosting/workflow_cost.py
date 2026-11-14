# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Price declared workflow/material components and compare finite releases.

This conditional model does not prove economic nonoverlap, complete costs,
clinical feasibility or global optimality. Resource quantities are proposed
allocated/available capacity-time, never measured CPU or paid labour by default.
"""

import json
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from itertools import product
from math import prod
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.cost_denominators import (
    ReportableCostSummary,
    summarize_reportable_cost,
)
from genomics_microcosting.inventory_ledger import (
    InventoryInputs,
    InventoryPricing,
    InventoryValue,
    WorkflowInputs,
    value_inventory,
)
from genomics_microcosting.workflow_schedule import (
    ResourceUtilization,
    ReworkScenario,
    WorkflowScenario,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import NonEmpty

MAX_NUMERIC_DIGITS = 128
MAX_POINTS = 256
NonNegativeTime = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


def _number(value: Decimal) -> Fraction:
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_NUMERIC_DIGITS
        or len(parts.digits) > MAX_NUMERIC_DIGITS
    ):
        msg = "Workflow cost number exceeds finite profile bounds"
        raise ValueError(msg)
    return Fraction(value)


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class ResourceRateBinding(_Model):
    """Select an explicitly allocated or available capacity-time rate."""

    resource_id: NonEmpty
    parameter_id: NonEmpty
    basis: Literal["allocated", "available"]


class FixedCostBinding(_Model):
    """Identify a distinct fixed amount for this exact horizon."""

    fixed_id: NonEmpty
    parameter_id: NonEmpty


class ResourcePricing(_Model):
    """Freeze economic and material-loss selection before comparing releases."""

    format_version: Literal["workflow-resource-cost-v1"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    horizon_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    resource_rates: tuple[ResourceRateBinding, ...]
    fixed_costs: tuple[FixedCostBinding, ...]
    material_selection: Literal[
        "consumed",
        "consumed_and_discard",
        "consumed_and_all_loss",
    ]
    assumption_basis: NonEmpty


class WorkflowComponentAssignment(_Model):
    """Name economic components for each input."""

    domain: Literal["resource", "fixed", "material"]
    input_id: NonEmpty
    component_ids: tuple[NonEmpty, ...] = Field(min_length=1)


class WorkflowCostBoundary(_Model):
    """Check declared component identities, not their economic truth."""

    assignments: tuple[WorkflowComponentAssignment, ...]
    assumption_basis: NonEmpty
    scope_limit: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"

    @model_validator(mode="after")
    def nonoverlap(self) -> Self:
        """Reject repeated assignments or overlapping named components."""
        keys = {(a.domain, a.input_id) for a in self.assignments}
        components = [c for a in self.assignments for c in a.component_ids]
        if len(keys) != len(self.assignments) or len(components) != len(
            set(components),
        ):
            msg = "Workflow cost component overlap or duplicate assignment"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class WorkflowCostInputs:
    """Retain original stock/workflow and independent price evidence."""

    inventory: InventoryInputs
    material_pricing: InventoryPricing
    material_context: ComputeCostContext
    resource_pricing: ResourcePricing
    resource_context: ComputeCostContext
    boundary: WorkflowCostBoundary


@dataclass(frozen=True)
class ResourceCostLine:
    """Retain rate basis and idle/allocated decomposition for one pool."""

    resource_id: str
    capacity_unit: str
    parameter_id: str
    basis: Literal["allocated", "available"]
    rate: Fraction
    allocated_resource_value: Fraction
    idle_capacity_value: Fraction
    selected_cost: Fraction


@dataclass(frozen=True)
class WorkflowCost:
    """Keep conditional scope, costs and service eligibility separate."""

    input_sha256: str
    material: InventoryValue
    pricing: ResourcePricing
    boundary: WorkflowCostBoundary
    cost_scope: Literal["declared_components_only"]
    resource_lines: tuple[ResourceCostLine, ...]
    allocated_resource_value: Fraction
    idle_capacity_value: Fraction
    selected_idle_cost: Fraction
    selected_resource_cost: Fraction
    fixed_cost: Fraction
    selected_material_cost: Fraction
    total_selected_cost: Fraction
    unit_cost_per_requested_test: Fraction | None
    worst_turnaround_seconds: Fraction | None
    service_coverage: Literal[
        "all_requested_tests",
        "partial_requested_tests",
        "no_demand",
    ]
    eligible_for_comparison: bool
    reportable_cost: ReportableCostSummary | None = None


def _check_frame(
    inputs: WorkflowCostInputs,
    material: InventoryValue,
    pricing: ResourcePricing,
    boundary: WorkflowCostBoundary,
) -> None:
    context = inputs.resource_context
    schedule = material.inventory.schedule
    if (
        (pricing.currency, pricing.price_year, pricing.tax_basis)
        != (material.currency, material.price_year, material.tax_basis)
        or context.costing_date != inputs.material_context.costing_date
        or context.ledger.parameter_set.workbook_sha256
        != material.inventory.stock.baseline_sha256
        or context.ledger.parameter_set.version_id != schedule.parameter_version_id
        or _number(pricing.horizon_seconds)
        != _number(
            Workload.model_validate(
                inputs.inventory.workflow.workload,
            ).horizon_seconds,
        )
    ):
        msg = "Workflow material/resource economic basis mismatch"
        raise ValueError(msg)
    rate_ids = {r.resource_id for r in pricing.resource_rates}
    fixed_ids = {f.fixed_id for f in pricing.fixed_costs}
    fixed_parameters = {f.parameter_id for f in pricing.fixed_costs}
    if (
        rate_ids != {r.resource_id for r in schedule.resources}
        or len(rate_ids) != len(pricing.resource_rates)
        or len(fixed_ids) != len(pricing.fixed_costs)
        or len(fixed_parameters) != len(pricing.fixed_costs)
        or fixed_parameters & {r.parameter_id for r in pricing.resource_rates}
    ):
        msg = "Workflow resource/fixed cost coverage is incomplete or duplicated"
        raise ValueError(msg)
    expected = {("resource", r) for r in rate_ids} | {("fixed", f) for f in fixed_ids}
    expected |= {("material", i.item_id) for i in material.inventory.stock.items}
    if {(a.domain, a.input_id) for a in boundary.assignments} != expected:
        msg = "Workflow cost boundary coverage differs from declared components"
        raise ValueError(msg)


def _resource_line(
    resource: ResourceUtilization,
    binding: ResourceRateBinding,
    values: dict[str, tuple[Decimal, str]],
    currency: str,
) -> ResourceCostLine:
    raw, unit = values[binding.parameter_id]
    if raw < 0 or unit != f"{currency}/{resource.capacity_unit}_s:{binding.basis}":
        msg = "Workflow resource rate is negative or has incompatible units/basis"
        raise ValueError(msg)
    rate = _number(raw)
    used = resource.allocated_unit_seconds * rate
    idle = resource.idle_unit_seconds * rate
    return ResourceCostLine(
        resource.resource_id,
        resource.capacity_unit,
        binding.parameter_id,
        binding.basis,
        rate,
        used,
        idle,
        used + idle if binding.basis == "available" else used,
    )


def _selected_material(
    material: InventoryValue,
    pricing: ResourcePricing,
) -> Fraction:
    total = material.consumed_stock_value
    if pricing.material_selection in (
        "consumed_and_discard",
        "consumed_and_all_loss",
    ):
        total += material.discarded_stock_value
    if pricing.material_selection == "consumed_and_all_loss":
        total += material.expired_stock_value
    return total


def calculate_workflow_cost(inputs: WorkflowCostInputs) -> WorkflowCost:
    """Price declared capacity, fixed and material components.

    Args:
        inputs: Workflow/stock, both price contexts and named boundary.

    Returns:
        Exact selected cost, idle/loss values and conditional eligibility.

    Raises:
        ValueError: Source, basis, coverage or boundary checks fail.
        OSError: An explicitly selected rate source cannot be read.

    """
    pricing = ResourcePricing.model_validate(inputs.resource_pricing)
    boundary = WorkflowCostBoundary.model_validate(inputs.boundary)
    material = value_inventory(
        inputs.inventory,
        inputs.material_pricing,
        inputs.material_context,
    )
    _check_frame(inputs, material, pricing, boundary)
    values = verify_numeric_source_values(inputs.resource_context)
    required = {r.parameter_id for r in pricing.resource_rates}
    required |= {f.parameter_id for f in pricing.fixed_costs}
    if values.keys() != required:
        msg = "Workflow resource/fixed rate ledger coverage differs"
        raise ValueError(msg)
    resources = {r.resource_id: r for r in material.inventory.schedule.resources}
    lines = tuple(
        _resource_line(resources[b.resource_id], b, values, pricing.currency)
        for b in pricing.resource_rates
    )
    fixed = Fraction(0)
    period = _number(pricing.horizon_seconds)
    fixed_unit = f"{pricing.currency}/horizon_s:{period}"
    for binding in pricing.fixed_costs:
        raw, unit = values[binding.parameter_id]
        if raw < 0 or unit != fixed_unit:
            msg = "Workflow fixed cost unit or horizon differs"
            raise ValueError(msg)
        fixed += _number(raw)
    selected_resource = sum((r.selected_cost for r in lines), Fraction(0))
    selected_material = _selected_material(material, pricing)
    total = selected_resource + fixed + selected_material
    schedule = material.inventory.schedule
    count = len(schedule.cases)
    covered = (
        all(c.state == "completed" for c in schedule.cases)
        and material.inventory.material_status == "fulfilled"
    )
    coverage: Literal[
        "all_requested_tests",
        "partial_requested_tests",
        "no_demand",
    ] = (
        "no_demand"
        if count == 0
        else "all_requested_tests"
        if covered
        else "partial_requested_tests"
    )
    times = [
        c.turnaround_seconds for c in schedule.cases if c.turnaround_seconds is not None
    ]
    identity = {
        "material": material.input_sha256,
        "pricing": pricing.model_dump(mode="json"),
        "boundary": boundary.model_dump(mode="json"),
        "ledger": inputs.resource_context.ledger.model_dump(mode="json"),
        "validity": [
            v.model_dump(mode="json") for v in inputs.resource_context.validity
        ],
        "costing_date": inputs.resource_context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return WorkflowCost(
        digest,
        material,
        pricing,
        boundary,
        "declared_components_only",
        lines,
        sum((r.allocated_resource_value for r in lines), Fraction(0)),
        sum((r.idle_capacity_value for r in lines), Fraction(0)),
        sum(
            (r.idle_capacity_value for r in lines if r.basis == "available"),
            Fraction(0),
        ),
        selected_resource,
        fixed,
        selected_material,
        total,
        total / count if count and covered else None,
        max(times) if times else None,
        coverage,
        bool(count and covered and schedule.feasibility == "feasible"),
        summarize_reportable_cost(
            inputs.inventory.workflow.workload,
            total,
            service_scope=(
                "complete_modeled_workload" if covered else "partial_modeled_workload"
            ),
        ),
    )


class ReleaseAxis(_Model):
    """Declare release lower bounds for an existing operation."""

    operation_id: NonEmpty
    values: tuple[NonNegativeTime, ...] = Field(min_length=1, max_length=256)


class WorkflowReleaseGrid(_Model):
    """Vary declared releases under fixed quality/economic inputs."""

    search_id: NonEmpty
    assumption_basis: NonEmpty
    axes: tuple[ReleaseAxis, ...] = Field(max_length=32)
    max_points: int = Field(
        strict=True,
        gt=0,
        le=MAX_POINTS,
        default=MAX_POINTS,
    )
    evidence_state: Literal["assumed"] = "assumed"


@dataclass(frozen=True)
class WorkflowReleasePoint:
    """Keep each release choice and its complete conditional cost result."""

    release_values: tuple[tuple[str, Decimal], ...]
    cost: WorkflowCost


@dataclass(frozen=True)
class WorkflowReleaseResult:
    """Retain a frontier of fully served, feasible priced points."""

    input_sha256: str
    points: tuple[WorkflowReleasePoint, ...]
    pareto_indices: tuple[int, ...]
    state: Literal["feasible", "infeasible", "no_demand"]
    cost_scope: Literal["declared_components_only"]


def _dominates(first: WorkflowCost, other: WorkflowCost) -> bool:
    a, b = first.worst_turnaround_seconds, other.worst_turnaround_seconds
    if a is None or b is None:
        return False
    return (
        first.total_selected_cost <= other.total_selected_cost
        and a <= b
        and (first.total_selected_cost < other.total_selected_cost or a < b)
    )


def _selected_scenario(
    scenario: WorkflowScenario | ReworkScenario,
) -> WorkflowScenario | ReworkScenario:
    if isinstance(scenario, ReworkScenario):
        return ReworkScenario.model_validate(scenario)
    return WorkflowScenario.model_validate(scenario)


def _validate_grid(
    inputs: WorkflowCostInputs,
    grid: WorkflowReleaseGrid,
) -> None:
    scenario = _selected_scenario(inputs.inventory.workflow.scenario)
    operations = {o.operation_id: o for o in scenario.operations}
    if len({a.operation_id for a in grid.axes}) != len(grid.axes):
        msg = "Duplicate release axis"
        raise ValueError(msg)
    if prod(len(a.values) for a in grid.axes) > grid.max_points:
        msg = "Release grid exceeds explicit point bound"
        raise ValueError(msg)
    horizon = _number(
        Workload.model_validate(
            inputs.inventory.workflow.workload,
        ).horizon_seconds,
    )
    for axis in grid.axes:
        if axis.operation_id not in operations or len(set(axis.values)) != len(
            axis.values,
        ):
            msg = "Release axis has unknown operation or duplicate values"
            raise ValueError(msg)
        lower = _number(operations[axis.operation_id].release_seconds)
        if any(not lower <= _number(v) <= horizon for v in axis.values):
            msg = "Release choice violates original lower bound or horizon"
            raise ValueError(msg)


def _release_inputs(
    inputs: WorkflowCostInputs,
    choices: tuple[tuple[str, Decimal], ...],
) -> WorkflowCostInputs:
    workflow = inputs.inventory.workflow
    base = _selected_scenario(workflow.scenario)
    changes = dict(choices)
    identity = {
        "base": base.model_dump(mode="json"),
        "choices": [(key, str(value)) for key, value in choices],
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    scenario = base.model_copy(
        update={
            "scenario_id": f"{base.scenario_id}:release:{digest}",
            "operations": tuple(
                o.model_copy(
                    update={"release_seconds": changes[o.operation_id]},
                )
                if o.operation_id in changes
                else o
                for o in base.operations
            ),
        },
    )
    return replace(
        inputs,
        inventory=InventoryInputs(
            WorkflowInputs(
                workflow.graph_payload,
                workflow.workload,
                workflow.policy,
                scenario,
            ),
            inputs.inventory.stock_payload,
            inputs.inventory.plan,
        ),
    )


def enumerate_workflow_releases(
    inputs: WorkflowCostInputs,
    grid: WorkflowReleaseGrid,
) -> WorkflowReleaseResult:
    """Enumerate only the declared finite release grid under fixed constraints.

    Args:
        inputs: Frozen graph/demand/grouping/outcomes/stock and economic inputs.
        grid: Explicit release choices under unchanged constraints.

    Returns:
        All priced points and a conditional cost/turnaround Pareto frontier.

    Raises:
        ValueError: Grid, source, price, scope or original constraints fail.

    """
    grid = WorkflowReleaseGrid.model_validate(grid)
    _validate_grid(inputs, grid)
    points: list[WorkflowReleasePoint] = []
    for values in product(*(axis.values for axis in grid.axes)):
        choices = tuple(
            (axis.operation_id, value)
            for axis, value in zip(grid.axes, values, strict=True)
        )
        points.append(
            WorkflowReleasePoint(
                choices,
                calculate_workflow_cost(_release_inputs(inputs, choices)),
            ),
        )
    eligible = [i for i, p in enumerate(points) if p.cost.eligible_for_comparison]
    frontier = tuple(
        i
        for i in eligible
        if not any(
            _dominates(points[j].cost, points[i].cost) for j in eligible if i != j
        )
    )
    identity = {
        "base_scenario": _selected_scenario(
            inputs.inventory.workflow.scenario,
        ).model_dump(mode="json"),
        "grid": grid.model_dump(mode="json"),
        "points": [p.cost.input_sha256 for p in points],
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return WorkflowReleaseResult(
        digest,
        tuple(points),
        frontier,
        "no_demand"
        if all(p.cost.service_coverage == "no_demand" for p in points)
        else "feasible"
        if eligible
        else "infeasible",
        "declared_components_only",
    )
