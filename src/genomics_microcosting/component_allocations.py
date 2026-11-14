# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Price requested resource components without assuming scheduled service."""

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.workflow_allocations import (
    MAX_ROWS,
    AllocationCostLine,
    AllocationQuantity,
    AllocationResource,
    allocation_parameter_value,
)
lazy from genomics_microcosting.parameter_provenance import Digest, NonEmpty
lazy from genomics_microcosting.workload_contract import WorkloadCase


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class AllocationCohort(_Model):
    """Retain requested identities without inventing a graph or time horizon."""

    format_version: Literal["allocation-cohort-v1"]
    cohort_id: NonEmpty
    process_id: NonEmpty
    baseline_sha256: Digest
    parameter_version_id: NonEmpty
    source_workload_sha256: Digest | None
    cases: tuple[WorkloadCase, ...] = Field(max_length=MAX_ROWS)
    evidence_state: Literal["assumed", "reported"]
    assumption_basis: NonEmpty

    @model_validator(mode="after")
    def unique_requests(self) -> Self:
        """One record represents one separately identified requested test."""
        if len({c.case_id for c in self.cases}) != len(self.cases) or len(
            {c.requested_test_id for c in self.cases},
        ) != len(self.cases):
            msg = "Duplicate cohort case or requested test"
            raise ValueError(msg)
        return self


class ComponentAllocationPricing(_Model):
    """Select an explicit accounting frame and complete resource/case pairs."""

    format_version: Literal["component-allocation-cost-v1"]
    cohort_sha256: Digest
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    resources: tuple[AllocationResource, ...] = Field(max_length=256)
    quantities: tuple[AllocationQuantity, ...] = Field(max_length=MAX_ROWS)
    assumption_basis: NonEmpty
    scope_limit: NonEmpty

    @model_validator(mode="after")
    def exact_coverage(self) -> Self:
        """Reject repeated economic scope and incomplete or extra quantities."""
        ids = [r.resource_id for r in self.resources]
        components = [c for r in self.resources for c in r.component_ids]
        if len(set(ids)) != len(ids) or len(set(components)) != len(components):
            msg = "Duplicate component allocation resource or component"
            raise ValueError(msg)
        if any(len(set(r.case_ids)) != len(r.case_ids) for r in self.resources):
            msg = "Duplicate component allocation case"
            raise ValueError(msg)
        if sum(len(r.case_ids) for r in self.resources) > MAX_ROWS:
            msg = "Component allocation case scope exceeds row bound"
            raise ValueError(msg)
        expected = {(r.resource_id, c) for r in self.resources for c in r.case_ids}
        actual = [(q.resource_id, q.case_id) for q in self.quantities]
        if len(set(actual)) != len(actual) or set(actual) != expected:
            msg = "Component quantities must cover declared case pairs exactly"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class ComponentAllocationInputs:
    """Keep accounting cohort and original numeric evidence separate."""

    cohort: AllocationCohort
    pricing: ComponentAllocationPricing
    context: ComputeCostContext


@dataclass(frozen=True)
class ComponentAllocationCost:
    """A declared component quote with no operational or complete-cost claim."""

    input_sha256: str
    cohort_sha256: str
    pricing: ComponentAllocationPricing
    lines: tuple[AllocationCostLine, ...]
    case_component_costs: tuple[tuple[str, Fraction], ...]
    selected_component_cost: Fraction
    component_cost_per_declared_requested_test: Fraction | None
    cost_scope: Literal["declared_components_only"] = "declared_components_only"
    service_coverage: Literal["not_assessed"] = "not_assessed"
    physical_feasibility: Literal["not_assessed"] = "not_assessed"
    cost_per_reportable_result: None = None
    full_workload_cost: None = None


def component_cohort_sha256(cohort: AllocationCohort) -> str:
    """Bind every requested identity, known/unknown relation and declaration."""
    checked = AllocationCohort.model_validate(cohort)
    return sha256(
        json.dumps(checked.model_dump(mode="json"), sort_keys=True).encode(),
    ).hexdigest()


def price_component_allocations(
    inputs: ComponentAllocationInputs,
) -> ComponentAllocationCost:
    """Price source-checked quantities without constructing event or stock data.

    The caller justifies price year, tax and resource applicability. Source
    bytes, dates, units, baseline/version and numeric profiles are checked.
    Service, consumption and economic completeness remain unassessed.
    """
    cohort = AllocationCohort.model_validate(inputs.cohort)
    pricing = ComponentAllocationPricing.model_validate(inputs.pricing)
    cohort_sha = component_cohort_sha256(cohort)
    if cohort_sha != pricing.cohort_sha256:
        msg = "Component allocation cohort identity mismatch"
        raise ValueError(msg)
    ledger = inputs.context.ledger.parameter_set
    if (
        ledger.workbook_sha256 != cohort.baseline_sha256
        or ledger.version_id != cohort.parameter_version_id
    ):
        msg = "Component source baseline/version mismatch"
        raise ValueError(msg)
    cases = {c.case_id for c in cohort.cases}
    if any(c not in cases for r in pricing.resources for c in r.case_ids):
        msg = "Component allocation references unknown requested case"
        raise ValueError(msg)
    values = verify_numeric_source_values(inputs.context)
    resources = {r.resource_id: r for r in pricing.resources}
    rates = {
        r.resource_id: allocation_parameter_value(
            values,
            r.rate_parameter_id,
            f"{pricing.currency}/{r.resource_unit}",
        )
        for r in pricing.resources
    }
    lines: list[AllocationCostLine] = []
    totals = {c.case_id: Fraction(0) for c in cohort.cases}
    for binding in pricing.quantities:
        resource = resources[binding.resource_id]
        numerator = allocation_parameter_value(
            values,
            binding.numerator_parameter_id,
            resource.resource_unit,
        )
        denominator = allocation_parameter_value(
            values,
            binding.denominator_parameter_id,
            "declared_requested_test",
        )
        if denominator <= 0 or denominator.denominator != 1:
            msg = "Component denominator requires positive whole requested tests"
            raise ValueError(msg)
        rate = rates[binding.resource_id]
        quantity = numerator / denominator
        cost = quantity * rate
        lines.append(
            AllocationCostLine(
                binding,
                resource.resource_unit,
                numerator,
                denominator,
                quantity,
                rate,
                cost,
            ),
        )
        totals[binding.case_id] += cost
    total = sum(totals.values(), Fraction(0))
    identity = {
        "cohort": cohort.model_dump(mode="json"),
        "pricing": pricing.model_dump(mode="json"),
        "ledger": inputs.context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in inputs.context.validity],
        "costing_date": inputs.context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return ComponentAllocationCost(
        digest,
        cohort_sha,
        pricing,
        tuple(lines),
        tuple(totals.items()),
        total,
        total / len(cohort.cases) if cohort.cases else None,
    )
