# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Allocate a priced reference period to declared native requested-time proxies.

This is conditional accounting, not measured CPU, a provider invoice, platform
or scheduling validation, or full workload cost. Exact execution links and unit
mapping remain explicit declarations; missing original fields stay unknown.
"""

import json
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    ComputeCostResult,
    CoreHourPricing,
    calculate_core_hour_cost,
)
from genomics_microcosting.execution_reconciliation import (
    ExecutionBinding,
    ExecutionReconciliation,
    ReconciledExecution,
    reconcile_executions,
)
lazy from genomics_microcosting.parameter_provenance import NonEmpty
lazy from genomics_microcosting.trace_registry import TraceExport

MAX_DIGITS = 128


def _bounded_decimal(value: Decimal) -> Decimal:
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_DIGITS
        or len(parts.digits) > MAX_DIGITS
    ):
        msg = "Reference capacity number exceeds finite profile bounds"
        raise ValueError(msg)
    return value


class ReferenceCapacityWindow(BaseModel):
    """Declare a hypothetical capacity period and economic unit mapping."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    format_version: Literal["trace-capacity-reference-v1"]
    reference_period_id: NonEmpty
    native_workload_id: NonEmpty
    reference_vcpus: int = Field(strict=True, gt=0, le=100_000)
    reference_memory_bytes: int = Field(strict=True, gt=0)
    horizon_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    reference_vcpus_per_native_slot: Decimal = Field(
        gt=0,
        allow_inf_nan=False,
    )
    mapping_assumption: NonEmpty
    bundle_allocation_assumption: NonEmpty
    scope_limit: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"

    @field_validator("horizon_seconds", "reference_vcpus_per_native_slot")
    @classmethod
    def finite_profile(cls, value: Decimal) -> Decimal:
        """Bound rational construction independently of Decimal context."""
        return _bounded_decimal(value)


@dataclass(frozen=True)
class TraceCapacityReferenceInputs:
    """Supply raw exports, explicit identities and independent price inputs."""

    exports: tuple[TraceExport, ...]
    bindings: tuple[ExecutionBinding, ...]
    window: ReferenceCapacityWindow
    pricing: CoreHourPricing
    price_context: ComputeCostContext


@dataclass(frozen=True)
class ExecutionCapacityReference:
    """Preserve original quantities without filling unknowns from cache."""

    execution_id: str
    original_status: str
    original_requested_cpus: int | None
    original_requested_memory_bytes: int | None
    realtime_ms: int | None
    requested_reference_vcpu_seconds: Fraction | None
    per_task_shape: Literal["within_declared_bounds", "unknown"]


@dataclass(frozen=True)
class TraceCapacityReference:
    """Retain exact reference-price conservation and incomplete scope."""

    input_sha256: str
    window: ReferenceCapacityWindow
    executions: ExecutionReconciliation
    period_cost: ComputeCostResult
    lines: tuple[ExecutionCapacityReference, ...]
    reference_available_vcpu_seconds: Fraction
    known_requested_reference_vcpu_seconds: Fraction
    missing_quantity_execution_ids: tuple[str, ...]
    requested_reference_vcpu_seconds: Fraction | None
    share: Fraction | None
    known_subtotal_reference_cost: Fraction
    selected_reference_cost: Fraction | None
    unallocated_reference_cost: Fraction | None
    quantity_state: Literal["complete", "incomplete"]
    per_task_shape: Literal["within_declared_bounds", "unknown"]
    cost_scope: Literal["reference_bundle_only"]
    temporal_feasibility: Literal["not_assessed"]
    actual_bill: None = None
    full_workload_cost: None = None


def _original_value(
    execution: ReconciledExecution,
    name: Literal["requested_cpus", "requested_memory_bytes"],
) -> int | None:
    known = {
        getattr(o.task, name)
        for o in execution.observations
        if o.binding.role == "execution" and getattr(o.task, name) is not None
    }
    # The existing reconciler rejects all known counter conflicts. Cache-only
    # values are deliberately absent from this set.
    return next(iter(known)) if known else None


def _execution_line(
    execution: ReconciledExecution,
    window: ReferenceCapacityWindow,
) -> ExecutionCapacityReference:
    cpus = _original_value(execution, "requested_cpus")
    memory = _original_value(execution, "requested_memory_bytes")
    mapped = (
        None
        if cpus is None
        else cpus * Fraction(window.reference_vcpus_per_native_slot)
    )
    if (mapped is not None and (mapped <= 0 or mapped > window.reference_vcpus)) or (
        memory is not None and memory > window.reference_memory_bytes
    ):
        msg = "Original request exceeds or invalidates reference task shape"
        raise ValueError(msg)
    quantity = (
        None
        if mapped is None or execution.realtime_ms is None
        else mapped * Fraction(execution.realtime_ms, 1000)
    )
    status = next(
        o.task.status for o in execution.observations if o.binding.role == "execution"
    )
    return ExecutionCapacityReference(
        execution.execution_id,
        status,
        cpus,
        memory,
        execution.realtime_ms,
        quantity,
        "unknown" if cpus is None or memory is None else "within_declared_bounds",
    )


def _price_period(
    inputs: TraceCapacityReferenceInputs,
    window: ReferenceCapacityWindow,
) -> tuple[CoreHourPricing, ComputeCostResult]:
    pricing = CoreHourPricing.model_validate(inputs.pricing)
    if (
        pricing.workload_id != window.reference_period_id
        or len(pricing.meters) != 1
        or pricing.bill_parameter_id is not None
        or pricing.meters[0].usage_basis != "requested"
        or pricing.meters[0].price_basis != "requested"
    ):
        msg = "Reference period needs one requested-basis bundle and no bill"
        raise ValueError(msg)
    cost = calculate_core_hour_cost(pricing, inputs.price_context)
    # The frozen function has verified every parameter/source/unit/date.
    parameters = {
        p.parameter_id: p for p in inputs.price_context.ledger.parameter_set.parameters
    }
    meter = pricing.meters[0]
    quantity = parameters[meter.quantity_parameter_id].derived_value
    selection = parameters[meter.allocation_parameter_id].derived_value
    expected = window.reference_vcpus * Fraction(window.horizon_seconds) / 3600
    if (
        quantity is None
        or selection is None
        or Fraction(_bounded_decimal(Decimal(quantity))) != expected
        or Fraction(Decimal(selection)) != 1
    ):
        msg = "Reference period quantity or whole-period selection differs"
        raise ValueError(msg)
    return pricing, cost


def allocate_trace_capacity_reference(
    inputs: TraceCapacityReferenceInputs,
) -> TraceCapacityReference:
    """Recompute an exact requested-time share of a priced reference period.

    Args:
        inputs: Exact trace bytes, execution declarations and reference inputs.

    Returns:
        Source-checked reference amount, rational shares and raw reconciliation.
        Missing original quantities keep whole allocation and residual unknown.

    Raises:
        ValueError: Source, identity, period, unit or capacity checks fail.
        ArithmeticError: The unchanged price function rejects inexact inputs.
        OSError: A selected independent numeric source cannot be read.

    """
    window = ReferenceCapacityWindow.model_validate(inputs.window)
    executions = reconcile_executions(inputs.exports, inputs.bindings)
    if not inputs.exports or any(
        e.context.workload_id != window.native_workload_id for e in inputs.exports
    ):
        msg = "Reference native workload context differs or is absent"
        raise ValueError(msg)
    pricing, cost = _price_period(inputs, window)
    lines = tuple(_execution_line(e, window) for e in executions.executions)
    available = window.reference_vcpus * Fraction(window.horizon_seconds)
    known = sum(
        (
            line.requested_reference_vcpu_seconds
            for line in lines
            if line.requested_reference_vcpu_seconds is not None
        ),
        Fraction(),
    )
    if known > available:
        msg = "Requested-time subtotal exceeds declared reference capacity"
        raise ValueError(msg)
    missing = tuple(
        line.execution_id
        for line in lines
        if line.requested_reference_vcpu_seconds is None
    )
    share = None if missing else known / available
    total = Fraction(_bounded_decimal(cost.modeled_total))
    selected = None if share is None else total * share
    identity = {
        "version": "trace-capacity-reference-v1",
        "window": window.model_dump(mode="json"),
        "execution_input": executions.input_sha256,
        "pricing": pricing.model_dump(mode="json"),
        "price_input": cost.input_sha256,
    }
    return TraceCapacityReference(
        sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
        window,
        executions,
        cost,
        lines,
        available,
        known,
        missing,
        None if missing else known,
        share,
        total * known / available,
        selected,
        None if selected is None else total - selected,
        "incomplete" if missing else "complete",
        "unknown"
        if any(line.per_task_shape == "unknown" for line in lines)
        else "within_declared_bounds",
        "reference_bundle_only",
        "not_assessed",
    )
