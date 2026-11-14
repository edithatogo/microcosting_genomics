# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Versioned compute arithmetic over explicitly sourced quantities and rates."""

import json
import re
from contextlib import ExitStack
from dataclasses import dataclass
from decimal import Decimal, Inexact, InvalidOperation, localcontext
from hashlib import sha256
from io import BytesIO
from typing import Literal, Self
lazy from datetime import date
lazy from pathlib import Path

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, model_validator
lazy from openpyxl.workbook import Workbook

from genomics_microcosting.native_usage import NativeUsageContext, read_native_usage
from genomics_microcosting.provenance_ledger import (
    QualificationLedger,
    SourceValidity,
    verify_qualified_period,
)
lazy from genomics_microcosting.parameter_provenance import NonEmpty

Basis = Literal["measured", "requested", "allocated", "billed"]


class ComputeMeter(BaseModel):
    """Declare one quantity/rate pair and its explicit workload allocation."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    meter_id: NonEmpty
    quantity_parameter_id: NonEmpty
    rate_parameter_id: NonEmpty
    allocation_parameter_id: NonEmpty
    unit: Literal["core_s", "device_s", "byte_s", "bytes"]
    usage_basis: Basis
    price_basis: Basis

    @model_validator(mode="after")
    def same_basis(self) -> Self:
        """Reject inferred conversion between measurement and charging bases."""
        if self.usage_basis != self.price_basis:
            msg = "Usage and price basis differ"
            raise ValueError(msg)
        return self


class ComputePricing(BaseModel):
    """Freeze a declared metered linear cost function independently of batching."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    function_version: Literal["compute-cost-v1"]
    workload_id: NonEmpty
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    meters: tuple[ComputeMeter, ...] = Field(min_length=1)
    bill_parameter_id: NonEmpty | None

    @model_validator(mode="after")
    def unique_meters(self) -> Self:
        """Reject duplicated declared meters before computing their sum."""
        if len({m.meter_id for m in self.meters}) != len(self.meters):
            msg = "Duplicate compute meter identity"
            raise ValueError(msg)
        if len({m.quantity_parameter_id for m in self.meters}) != len(self.meters):
            msg = "Duplicate compute quantity would count usage twice"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class ComputeCostContext:
    """Supply retained numeric evidence and explicit source validity."""

    ledger: QualificationLedger
    snapshots: dict[str, Path]
    validity: tuple[SourceValidity, ...]
    costing_date: date
    native_usage: tuple[NativeUsageContext, ...] = ()


@dataclass(frozen=True)
class ComputeCostResult:
    """Reconcile modeled cost, explicit allocation and optional bill residual."""

    input_sha256: str
    modeled_total: Decimal
    allocated_cost: Decimal
    unallocated_cost: Decimal
    bill_residual: Decimal | None


class CoreHourMeter(BaseModel):
    """Select sourced core-hours without converting or relabeling seconds."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    meter_id: NonEmpty
    quantity_parameter_id: NonEmpty
    rate_parameter_id: NonEmpty
    allocation_parameter_id: NonEmpty
    unit: Literal["core_h"]
    usage_basis: Basis
    price_basis: Basis

    @model_validator(mode="after")
    def same_basis(self) -> Self:
        """Require the observation and rate to share the declared basis."""
        if self.usage_basis != self.price_basis:
            msg = "Usage and price basis differ"
            raise ValueError(msg)
        return self


class CoreHourPricing(BaseModel):
    """Keep hourly capacity economics outside the frozen seconds contract."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    function_version: Literal["compute-core-hour-cost-v1"]
    workload_id: NonEmpty
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    meters: tuple[CoreHourMeter, ...] = Field(min_length=1)
    bill_parameter_id: NonEmpty | None

    @model_validator(mode="after")
    def unique_meters(self) -> Self:
        """Reject duplicate meters and reused quantity parameters."""
        if len({m.meter_id for m in self.meters}) != len(self.meters):
            msg = "Duplicate compute meter identity"
            raise ValueError(msg)
        if len({m.quantity_parameter_id for m in self.meters}) != len(self.meters):
            msg = "Duplicate compute quantity would count usage twice"
            raise ValueError(msg)
        return self


def _workbook_number(book: Workbook, locator: str) -> Decimal:
    match = re.fullmatch(r"WB([0-9]{2}):([A-Z]{1,3}[1-9][0-9]*)", locator)
    if match is None or not 1 <= int(match.group(1)) <= len(book.worksheets):
        msg = "Compute baseline workbook locator unsupported"
        raise ValueError(msg)
    value = book.worksheets[int(match.group(1)) - 1][match.group(2)].value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "Compute baseline workbook observation is not numeric"
        raise TypeError(msg)
    return Decimal(str(value))


def _text_number(payload: bytes, locator: str) -> Decimal:
    match = re.fullmatch(r"line ([1-9][0-9]*)", locator)
    try:
        lines = payload.decode("utf-8").splitlines()
        if match is None or int(match.group(1)) > len(lines):
            msg = "Compute numeric source locator unsupported"
            raise ValueError(msg)
        return Decimal(lines[int(match.group(1)) - 1].strip())
    except (UnicodeDecodeError, InvalidOperation) as exc:
        msg = "Compute source must be a supported numeric UTF-8 line"
        raise ValueError(msg) from exc


def _native_profiles(context: ComputeCostContext) -> dict[str, NativeUsageContext]:
    checked = tuple(
        NativeUsageContext.model_validate(p.model_dump()) for p in context.native_usage
    )
    profiles = {p.source_sha256: p for p in checked}
    sources = {
        q.source.sha256
        for q in context.ledger.qualifications
        if q.source.locator.startswith("wait4:")
    }
    executions = {(p.run_id, p.task_id, p.attempt) for p in checked}
    if (
        profiles.keys() != sources
        or len(profiles) != len(checked)
        or len(executions) != len(checked)
    ):
        msg = "Native observation profile coverage is missing or duplicated"
        raise ValueError(msg)
    return profiles


def verify_numeric_source_values(
    context: ComputeCostContext,
) -> dict[str, tuple[Decimal, str]]:
    """Verify dated identity-valued numeric sources without inferring units."""
    ledger = QualificationLedger.model_validate(context.ledger.model_dump())
    ids = tuple(p.parameter_id for p in ledger.parameter_set.parameters)
    verify_qualified_period(
        ledger,
        context.snapshots,
        context.validity,
        required_ids=ids,
        costing_date=context.costing_date,
    )
    result: dict[str, tuple[Decimal, str]] = {}
    profiles = _native_profiles(context)
    with ExitStack() as resources:
        baseline: Workbook | None = None
        for record in ledger.qualifications:
            parameter = record.parameter
            payload = context.snapshots[record.source.source_id].read_bytes()
            if sha256(payload).hexdigest() != record.source.sha256:
                msg = "Compute source hash mismatch"
                raise ValueError(msg)
            if parameter.source_locator != record.source.locator:
                msg = "Parameter source locator differs from registered observation"
                raise ValueError(msg)
            if record.source.locator.startswith("wait4:"):
                observation = read_native_usage(payload, profiles[record.source.sha256])
                native_values = {
                    "wait4:user_cpu_seconds": observation.user_cpu_seconds,
                    "wait4:system_cpu_seconds": observation.system_cpu_seconds,
                }
                if (
                    record.source.locator not in native_values
                    or parameter.unit != "core_s"
                ):
                    msg = "Native CPU source locator or unit is unsupported"
                    raise ValueError(msg)
                value = native_values[record.source.locator]
            elif record.source.sha256 == ledger.parameter_set.workbook_sha256:
                if baseline is None:
                    baseline = load_workbook(
                        BytesIO(payload),
                        data_only=True,
                        read_only=True,
                    )
                    resources.callback(baseline.close)
                value = _workbook_number(baseline, record.source.locator)
            else:
                value = _text_number(payload, record.source.locator)
            try:
                raw = Decimal(parameter.raw_value or "NaN")
                derived = Decimal(parameter.derived_value or "NaN")
            except InvalidOperation as exc:
                msg = "Compute raw/derived value is not numeric"
                raise ValueError(msg) from exc
            if not value.is_finite() or value != raw or value != derived:
                msg = "Compute numeric source value or identity transformation differs"
                raise ValueError(msg)
            result[parameter.parameter_id] = (value, parameter.unit)
    return result


def _value(
    values: dict[str, tuple[Decimal, str]],
    identifier: str,
    unit: str,
) -> Decimal:
    value, actual_unit = values[identifier]
    if actual_unit != unit:
        msg = "Compute parameter unit differs from selected meter"
        raise ValueError(msg)
    return value


def calculate_compute_cost(
    pricing: ComputePricing,
    context: ComputeCostContext,
) -> ComputeCostResult:
    """Price declared inputs with exact units and no missing-to-zero conversions."""
    pricing = ComputePricing.model_validate(pricing.model_dump())
    return _calculate_metered_cost(pricing, context)


def calculate_core_hour_cost(
    pricing: CoreHourPricing,
    context: ComputeCostContext,
) -> ComputeCostResult:
    """Price explicitly sourced core-hours under a separate function version.

    Args:
        pricing: Selected hourly meters and economic declarations.
        context: Retained numeric sources and dated qualification assertions.

    Returns:
        Exact finite-decimal cost/allocation and optional signed bill residual.

    Raises:
        ValueError: Sources, units, scope or declared bases do not match.
        ArithmeticError: An operation exceeds the finite precision contract.
        OSError: An explicitly selected source cannot be read.

    """
    pricing = CoreHourPricing.model_validate(pricing.model_dump())
    return _calculate_metered_cost(pricing, context)


def _calculate_metered_cost(
    pricing: ComputePricing | CoreHourPricing,
    context: ComputeCostContext,
) -> ComputeCostResult:
    values = verify_numeric_source_values(context)
    required = {
        p
        for m in pricing.meters
        for p in (
            m.quantity_parameter_id,
            m.rate_parameter_id,
            m.allocation_parameter_id,
        )
    }
    if pricing.bill_parameter_id is not None:
        required.add(pricing.bill_parameter_id)
    if required != values.keys():
        msg = "Compute pricing input coverage differs from ledger"
        raise ValueError(msg)
    quantities = {q.parameter.parameter_id: q for q in context.ledger.qualifications}
    native_counters: set[tuple[str, str]] = set()
    with localcontext() as decimal_context:
        decimal_context.prec = 50
        decimal_context.traps[Inexact] = True
        total = Decimal(0)
        allocated = Decimal(0)
        for meter in pricing.meters:
            observed = quantities[meter.quantity_parameter_id].source
            if observed.locator.startswith("wait4:"):
                if meter.usage_basis != "measured":
                    msg = "Native CPU counters require measured usage and price basis"
                    raise ValueError(msg)
                counter_identity = (observed.sha256, observed.locator)
                if counter_identity in native_counters:
                    msg = "Native CPU counter would be priced twice under aliases"
                    raise ValueError(msg)
                native_counters.add(counter_identity)
            quantity = _value(values, meter.quantity_parameter_id, meter.unit)
            rate = _value(
                values,
                meter.rate_parameter_id,
                f"{pricing.currency}/{meter.unit}",
            )
            share = _value(values, meter.allocation_parameter_id, "fraction")
            if quantity < 0 or rate < 0 or not 0 <= share <= 1:
                msg = "Compute quantity, rate or allocation is outside valid bounds"
                raise ValueError(msg)
            cost = quantity * rate
            total += cost
            allocated += cost * share
        bill = (
            None
            if pricing.bill_parameter_id is None
            else _value(values, pricing.bill_parameter_id, pricing.currency)
        )
        residual = None if bill is None else bill - total
        unallocated = total - allocated
    identity: dict[str, object] = {
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    if context.native_usage:
        identity["native_usage"] = [
            p.model_dump(mode="json") for p in context.native_usage
        ]
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return ComputeCostResult(digest, total, allocated, unallocated, residual)
