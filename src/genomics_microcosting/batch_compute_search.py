# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Combine finite batch policies with explicitly bound compute evidence."""

import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256
from typing import Literal, Self, Unpack

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.batch_policy_search import (
    PolicyGrid,
    PolicyPoint,
    enumerate_batch_policies,
)
from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    ComputeCostResult,
    ComputePricing,
    CoreHourPricing,
    calculate_compute_cost,
    calculate_core_hour_cost,
)
from genomics_microcosting.static_batch_cost import BatchPricing
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.dynamic_batch import DynamicBatchPolicy
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class ComponentAssignment(BaseModel):
    """Name economic cost components belonging to one rate or compute meter."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    domain: Literal["batch", "compute"]
    input_id: NonEmpty
    component_ids: tuple[NonEmpty, ...] = Field(min_length=1)


class CostBoundary(BaseModel):
    """Declare assumed economic nonoverlap; labels do not establish its truth."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    assignments: tuple[ComponentAssignment, ...] = Field(min_length=1)
    assumption_basis: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"

    @model_validator(mode="after")
    def nonoverlap(self) -> Self:
        """Reject duplicate assignments and overlapping named cost components."""
        keys = {(a.domain, a.input_id) for a in self.assignments}
        components = [c for a in self.assignments for c in a.component_ids]
        if len(keys) != len(self.assignments) or len(set(components)) != len(
            components,
        ):
            msg = "Cost boundary overlap or duplicate assignment"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class ComputePolicyInput:
    """Supply independent compute inputs bound by the caller to an exact schedule."""

    pricing: ComputePricing | CoreHourPricing
    context: ComputeCostContext


@dataclass(frozen=True)
class CombinedPolicyPoint:
    """Preserve batch timing, compute reconciliation and missing-cost scope."""

    batch: PolicyPoint
    compute: ComputeCostResult | None
    total_cost: Decimal | None
    cost_state: Literal["priced", "missing_compute", "partial_batch"]


@dataclass(frozen=True)
class CombinedPolicySearch:
    """Keep the conditional frontier and completeness of the declared search."""

    input_sha256: str
    points: tuple[CombinedPolicyPoint, ...]
    pareto_indices: tuple[int, ...]
    state: Literal["priced", "incomplete_compute_data", "infeasible", "no_demand"]


def _compute_for_point(
    binding: ComputePolicyInput,
    workload: Workload,
    pricing: BatchPricing,
    context: ComputeCostContext,
    boundary: CostBoundary,
) -> ComputeCostResult:
    model = (
        CoreHourPricing
        if isinstance(binding.pricing, CoreHourPricing)
        else ComputePricing
    )
    selected = model.model_validate(binding.pricing.model_dump())
    if (
        selected.workload_id != workload.workload_id
        or selected.currency != pricing.currency
        or selected.price_year != pricing.price_year
        or selected.tax_basis != pricing.tax_basis
        or binding.context.costing_date != context.costing_date
        or binding.context.ledger.parameter_set.workbook_sha256
        != context.ledger.parameter_set.workbook_sha256
    ):
        msg = "Batch and compute workload or economic basis differ"
        raise ValueError(msg)
    meters = {a.input_id for a in boundary.assignments if a.domain == "compute"}
    if meters != {m.meter_id for m in selected.meters}:
        msg = "Compute boundary coverage differs from selected meters"
        raise ValueError(msg)
    if isinstance(selected, CoreHourPricing):
        return calculate_core_hour_cost(selected, binding.context)
    return calculate_compute_cost(selected, binding.context)


def _dominates(first: CombinedPolicyPoint, second: CombinedPolicyPoint) -> bool:
    cost, other = first.total_cost, second.total_cost
    tat = first.batch.worst_turnaround_seconds
    other_tat = second.batch.worst_turnaround_seconds
    if cost is None or other is None or tat is None or other_tat is None:
        return False
    return cost <= other and tat <= other_tat and (cost < other or tat < other_tat)


class ComputePolicyGrid(PolicyGrid):
    """Bind compute evidence by schedule digest for the policy search."""

    compute_inputs: dict[str, ComputePolicyInput]


def enumerate_compute_batch_policies(
    workload: Workload,
    base_policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
    boundary: CostBoundary,
    **grid: Unpack[ComputePolicyGrid],
) -> CombinedPolicySearch:
    """Recompute the finite grid and add allocated compute cost per exact schedule.

    Keys are schedule input digests from the batch-only enumeration. Missing
    bindings remain unknown; partial batch service cannot consume whole-workload
    compute inputs. The frontier is conditional on the available priced points.
    """
    compute_inputs = grid["compute_inputs"]
    workload = Workload.model_validate(workload.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    boundary = CostBoundary.model_validate(boundary.model_dump())
    batch_ids = {a.input_id for a in boundary.assignments if a.domain == "batch"}
    if batch_ids != {
        pricing.fixed_parameter_id,
        pricing.item_parameter_id,
        pricing.run_parameter_id,
        pricing.pack_parameter_id,
    }:
        msg = "Batch boundary coverage differs from selected rates"
        raise ValueError(msg)
    batch = enumerate_batch_policies(
        workload,
        base_policy,
        pricing,
        context,
        payload_limits=grid["payload_limits"],
        max_wait_seconds=grid["max_wait_seconds"],
    )
    schedules = {p.result.schedule.input_sha256 for p in batch.points}
    if not compute_inputs.keys() <= schedules:
        msg = "Compute binding references an unknown schedule"
        raise ValueError(msg)
    points: list[CombinedPolicyPoint] = []
    for point in batch.points:
        binding = compute_inputs.get(point.result.schedule.input_sha256)
        compute = None
        total = None
        state: Literal["priced", "missing_compute", "partial_batch"]
        if point.result.cost_state == "partial_workload":
            if binding is not None:
                msg = "Whole-workload compute input cannot price partial batch service"
                raise ValueError(msg)
            state = "partial_batch"
        elif binding is None:
            state = "missing_compute"
        else:
            compute = _compute_for_point(binding, workload, pricing, context, boundary)
            with localcontext() as arithmetic:
                arithmetic.prec = 50
                arithmetic.traps[Inexact] = True
                total = point.result.cost.total_cost + compute.allocated_cost
            state = "priced"
        points.append(CombinedPolicyPoint(point, compute, total, state))
    feasible = tuple(
        i
        for i, p in enumerate(points)
        if p.batch.result.schedule.feasibility == "feasible"
        and p.batch.worst_turnaround_seconds is not None
    )
    priced = tuple(i for i in feasible if points[i].total_cost is not None)
    frontier = tuple(
        i for i in priced if not any(_dominates(points[j], points[i]) for j in priced)
    )
    identity = {
        "format_version": "batch-compute-search-v1",
        "batch_search": batch.input_sha256,
        "boundary": boundary.model_dump(mode="json"),
        "compute_inputs": [
            p.compute.input_sha256 if p.compute else None for p in points
        ],
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return CombinedPolicySearch(
        digest,
        tuple(points),
        frontier,
        "no_demand"
        if not workload.cases
        else "infeasible"
        if not feasible
        else "incomplete_compute_data"
        if len(priced) != len(feasible)
        else "priced",
    )
