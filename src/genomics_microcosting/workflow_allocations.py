# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Add declared requested-case resource allocations without inventing runtime.

Source and component checks validate declarations, not economic completeness,
physical resource independence or actual consumption by served/failed cases.
"""

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Annotated, Literal, Self
lazy from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.cost_denominators import (
    ReportableCostSummary,
    summarize_reportable_cost,
)
from genomics_microcosting.workflow_cost import (
    WorkflowCost,
    WorkflowCostInputs,
    calculate_workflow_cost,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import Digest, NonEmpty

MAX_ROWS = 10_000
MAX_NUMERIC_DIGITS = 128
ResourceUnit = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class AllocationResource(_Model):
    """Declare a resource rate, component boundary and requested-case scope."""

    resource_id: NonEmpty
    resource_unit: ResourceUnit
    rate_parameter_id: NonEmpty
    case_ids: tuple[NonEmpty, ...] = Field(max_length=MAX_ROWS)
    component_ids: tuple[NonEmpty, ...] = Field(min_length=1, max_length=256)


class AllocationQuantity(_Model):
    """One sourced resource numerator per whole requested-test denominator."""

    resource_id: NonEmpty
    case_id: NonEmpty
    numerator_parameter_id: NonEmpty
    denominator_parameter_id: NonEmpty


class RequestedAllocationPricing(_Model):
    """Select fractional allocations independently of physical stock or time."""

    format_version: Literal["requested-allocations-v1"]
    workload_sha256: Digest
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    resources: tuple[AllocationResource, ...] = Field(max_length=256)
    quantities: tuple[AllocationQuantity, ...] = Field(max_length=MAX_ROWS)
    assumption_basis: NonEmpty
    scope_limit: NonEmpty
    allocation_basis: Literal["declared_requested_cases"]

    @model_validator(mode="after")
    def exact_declared_coverage(self) -> Self:
        """Reject repeated resources/components or missing/extra case pairs."""
        ids = [r.resource_id for r in self.resources]
        components = [c for r in self.resources for c in r.component_ids]
        if len(set(ids)) != len(ids) or len(set(components)) != len(components):
            msg = "Duplicate allocation resource or component identity"
            raise ValueError(msg)
        if any(len(set(r.case_ids)) != len(r.case_ids) for r in self.resources):
            msg = "Duplicate allocation case identity"
            raise ValueError(msg)
        if sum(len(r.case_ids) for r in self.resources) > MAX_ROWS:
            msg = "Allocation case scope exceeds row bound"
            raise ValueError(msg)
        expected = {(r.resource_id, c) for r in self.resources for c in r.case_ids}
        actual = [(q.resource_id, q.case_id) for q in self.quantities]
        if len(set(actual)) != len(actual) or set(actual) != expected:
            msg = "Allocation quantities must cover declared case pairs exactly"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class WorkflowAllocationInputs:
    """Keep original workflow inputs and the extra source context."""

    workflow: WorkflowCostInputs
    pricing: RequestedAllocationPricing
    context: ComputeCostContext


@dataclass(frozen=True)
class AllocationCostLine:
    """Retain numerator, denominator, exact quantity and selected cost."""

    binding: AllocationQuantity
    resource_unit: str
    numerator: Fraction
    denominator: Fraction
    quantity: Fraction
    unit_rate: Fraction
    selected_cost: Fraction


@dataclass(frozen=True)
class AllocatedWorkflowCost:
    """Keep allocations separate from runtime and base service rules."""

    input_sha256: str
    base_cost: WorkflowCost
    pricing: RequestedAllocationPricing
    lines: tuple[AllocationCostLine, ...]
    selected_allocation_cost: Fraction
    total_selected_cost: Fraction
    unit_cost_per_requested_test: Fraction | None
    reportable_cost: ReportableCostSummary
    eligible_under_base_service_rules: bool
    allocation_basis: Literal["declared_requested_cases"]
    cost_scope: Literal["declared_components_only"]
    allocation_physical_feasibility: Literal["not_assessed"]
    full_workload_cost: None = None


def allocation_workload_sha256(workload: Workload) -> str:
    """Hash a revalidated complete workload without altering its identifiers.

    Args:
        workload: Explicit declared cases, graph, parameter version and horizon.

    Returns:
        Canonical workload digest required by allocation selection.

    Raises:
        ValueError: Workload declarations fail their existing contract.

    """
    checked = Workload.model_validate(workload.model_dump())
    return sha256(
        json.dumps(checked.model_dump(mode="json"), sort_keys=True).encode(),
    ).hexdigest()


def _value(
    values: dict[str, tuple[Decimal, str]],
    parameter_id: str,
    unit: str,
) -> Fraction:
    if parameter_id not in values or values[parameter_id][1] != unit:
        msg = "Allocation parameter missing or unit mismatch"
        raise ValueError(msg)
    value = values[parameter_id][0]
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or value < 0
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_NUMERIC_DIGITS
        or len(parts.digits) > MAX_NUMERIC_DIGITS
    ):
        msg = "Allocation value exceeds nonnegative finite numeric profile"
        raise ValueError(msg)
    return Fraction(value)


def allocation_parameter_value(
    values: dict[str, tuple[Decimal, str]],
    parameter_id: str,
    unit: str,
) -> Fraction:
    """Check a bounded unit-bound scalar; source verification is separate."""
    return _value(values, parameter_id, unit)


def calculate_allocated_workflow_cost(
    inputs: WorkflowAllocationInputs,
) -> AllocatedWorkflowCost:
    """Recompute old workflow cost and add source-checked allocations.

    Args:
        inputs: Requested-case allocation selection and both cost layers.

    Returns:
        Conditional declared cost; allocations do not alter the schedule.

    Raises:
        ValueError: Identity, source, unit, frame or component checks fail.
        OSError: An explicitly selected source cannot be read.

    """
    pricing = RequestedAllocationPricing.model_validate(inputs.pricing)
    workload = Workload.model_validate(
        inputs.workflow.inventory.workflow.workload,
    )
    if allocation_workload_sha256(workload) != pricing.workload_sha256:
        msg = "Allocation workload identity mismatch"
        raise ValueError(msg)
    known = {c.case_id for c in workload.cases}
    if any(c not in known for r in pricing.resources for c in r.case_ids):
        msg = "Allocation references unknown requested case"
        raise ValueError(msg)
    base = calculate_workflow_cost(inputs.workflow)
    ledger = inputs.context.ledger.parameter_set
    if (
        (pricing.currency, pricing.price_year, pricing.tax_basis)
        != (
            base.pricing.currency,
            base.pricing.price_year,
            base.pricing.tax_basis,
        )
        or inputs.context.costing_date != inputs.workflow.resource_context.costing_date
        or ledger.workbook_sha256 != base.material.inventory.stock.baseline_sha256
        or ledger.version_id != workload.parameter_version_id
    ):
        msg = "Allocation source economic frame or baseline/version mismatch"
        raise ValueError(msg)
    existing = {c for a in base.boundary.assignments for c in a.component_ids}
    if any(c in existing for r in pricing.resources for c in r.component_ids):
        msg = "Allocation overlaps existing workflow component"
        raise ValueError(msg)
    values = verify_numeric_source_values(inputs.context)
    resources = {r.resource_id: r for r in pricing.resources}
    rates = {
        r.resource_id: _value(
            values,
            r.rate_parameter_id,
            f"{pricing.currency}/{r.resource_unit}",
        )
        for r in pricing.resources
    }
    lines: list[AllocationCostLine] = []
    for binding in pricing.quantities:
        resource = resources[binding.resource_id]
        numerator = _value(
            values,
            binding.numerator_parameter_id,
            resource.resource_unit,
        )
        denominator = _value(
            values,
            binding.denominator_parameter_id,
            "declared_requested_test",
        )
        if denominator <= 0 or denominator.denominator != 1:
            msg = "Allocation denominator requires positive whole requested tests"
            raise ValueError(msg)
        quantity = numerator / denominator
        rate = rates[binding.resource_id]
        lines.append(
            AllocationCostLine(
                binding,
                resource.resource_unit,
                numerator,
                denominator,
                quantity,
                rate,
                quantity * rate,
            ),
        )
    selected = sum((line.selected_cost for line in lines), Fraction(0))
    total = base.total_selected_cost + selected
    count = len(workload.cases)
    if base.reportable_cost is None:
        msg = "Recomputed base service metadata missing"
        raise ValueError(msg)
    identity = {
        "base": base.input_sha256,
        "pricing": pricing.model_dump(mode="json"),
        "ledger": inputs.context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in inputs.context.validity],
        "costing_date": inputs.context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return AllocatedWorkflowCost(
        digest,
        base,
        pricing,
        tuple(lines),
        selected,
        total,
        total / count
        if count and base.service_coverage == "all_requested_tests"
        else None,
        summarize_reportable_cost(
            workload,
            total,
            service_scope=base.reportable_cost.service_scope,
        ),
        base.eligible_for_comparison,
        "declared_requested_cases",
        "declared_components_only",
        "not_assessed",
    )
