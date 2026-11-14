# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Import explicit sample-use allocations into unchanged requested costing.

Derived numeric snapshots are temporary computation products, not independent
source evidence. Original sources and the complete derivation remain hash-bound.
"""

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
lazy from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from genomics_microcosting.workflow_allocations import (
    MAX_ROWS,
    AllocatedWorkflowCost,
    AllocationResource,
    RequestedAllocationPricing,
    WorkflowAllocationInputs,
    allocation_workload_sha256,
    calculate_allocated_workflow_cost,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import Digest, NonEmpty
lazy from genomics_microcosting.workflow_cost import WorkflowCostInputs
lazy from genomics_microcosting.workload_contract import WorkloadCase

MAX_DIGITS = 128
MAX_INTEGER_BITS = 426


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class SampleResource(AllocationResource):
    """Bind a source numerator, whole sample denominator and resource rate."""

    numerator_parameter_id: NonEmpty
    sample_denominator_parameter_id: NonEmpty


class SampleUse(_Model):
    """Identify a processing use separately from its specimen."""

    use_id: NonEmpty
    specimen_id: NonEmpty


class SampleShare(_Model):
    """Explicitly attribute one sample use across requested cases."""

    use_id: NonEmpty
    case_id: NonEmpty
    numerator: int = Field(strict=True, gt=0, le=10**18)
    denominator: int = Field(strict=True, gt=0, le=10**18)


class SampleAllocationPricing(_Model):
    """Freeze proposed entity attribution and source sample quantities."""

    format_version: Literal["sample-allocation-import-v1"]
    workload_sha256: Digest
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    derivation_date: date
    resources: tuple[SampleResource, ...] = Field(max_length=256)
    sample_uses: tuple[SampleUse, ...] = Field(max_length=MAX_ROWS)
    shares: tuple[SampleShare, ...] = Field(max_length=MAX_ROWS)
    assumption_basis: NonEmpty
    scope_limit: NonEmpty


@dataclass(frozen=True)
class SampleWorkflowInputs:
    """Retain original workflow, source context and explicit sample mapping."""

    workflow: WorkflowCostInputs
    pricing: SampleAllocationPricing
    context: ComputeCostContext


def _selected_cases(
    workload: Workload,
    pricing: SampleAllocationPricing,
) -> dict[str, WorkloadCase]:
    selected = {c for r in pricing.resources for c in r.case_ids}
    cases = {c.case_id: c for c in workload.cases if c.case_id in selected}
    if cases.keys() != selected:
        msg = "Sample mapping references unknown requested case"
        raise ValueError(msg)
    if any(c.specimen_ids is None for c in cases.values()):
        msg = "Unknown specimen relationships in selected sample scope"
        raise ValueError(msg)
    return cases


def _factors(
    workload: Workload,
    pricing: SampleAllocationPricing,
) -> dict[str, Fraction]:
    cases = _selected_cases(workload, pricing)
    uses = {u.use_id: u.specimen_id for u in pricing.sample_uses}
    if len(uses) != len(pricing.sample_uses):
        msg = "Duplicate sample-use identity"
        raise ValueError(msg)
    totals = dict.fromkeys(uses, Fraction(0))
    factors = dict.fromkeys(cases, Fraction(0))
    seen: set[tuple[str, str]] = set()
    covered: set[tuple[str, str]] = set()
    for share in pricing.shares:
        pair = (share.use_id, share.case_id)
        if pair in seen:
            msg = "Duplicate sample-case share"
            raise ValueError(msg)
        seen.add(pair)
        if share.use_id not in uses or share.case_id not in cases:
            msg = "Sample share references unknown use or selected case"
            raise ValueError(msg)
        specimen = uses[share.use_id]
        if specimen not in (cases[share.case_id].specimen_ids or ()):
            msg = "Sample specimen outside requested case"
            raise ValueError(msg)
        value = Fraction(share.numerator, share.denominator)
        totals[share.use_id] += value
        factors[share.case_id] += value
        if totals[share.use_id] > 1:
            msg = "Sample shares must conserve one use"
            raise ValueError(msg)
        for total in (totals[share.use_id], factors[share.case_id]):
            _bounded_integer(total.numerator)
            _bounded_integer(total.denominator)
        covered.add((share.case_id, specimen))
    if any(total != 1 for total in totals.values()):
        msg = "Sample shares must conserve one use"
        raise ValueError(msg)
    expected = {(c.case_id, s) for c in cases.values() for s in (c.specimen_ids or ())}
    if covered != expected:
        msg = "Requested specimen attribution is incomplete"
        raise ValueError(msg)
    return factors


def _bounded_integer(value: int) -> str:
    if value.bit_length() > MAX_INTEGER_BITS or len(str(value)) > MAX_DIGITS:
        msg = "Derived sample quantity exceeds numeric profile"
        raise ValueError(msg)
    return str(value)


def _derive(
    inputs: SampleWorkflowInputs,
    pricing: SampleAllocationPricing,
    factors: dict[str, Fraction],
    directory: Path,
) -> WorkflowAllocationInputs:
    values = verify_numeric_source_values(inputs.context)
    lineage = sha256(
        json.dumps(
            {
                "pricing": pricing.model_dump(mode="json"),
                "ledger": inputs.context.ledger.model_dump(mode="json"),
                "validity": [
                    v.model_dump(mode="json") for v in inputs.context.validity
                ],
                "costing_date": inputs.context.costing_date.isoformat(),
                "native_usage": [
                    p.model_dump(mode="json") for p in inputs.context.native_usage
                ],
            },
            sort_keys=True,
        ).encode(),
    ).hexdigest()
    parameters = list(inputs.context.ledger.parameter_set.parameters)
    qualifications = list(inputs.context.ledger.qualifications)
    periods = list(inputs.context.validity)
    snapshots = dict(inputs.context.snapshots)
    used_ids = {p.parameter_id for p in parameters} | set(snapshots)
    quantities: list[dict[str, str]] = []
    for resource in pricing.resources:
        source_values: list[Fraction] = []
        for pid, unit in (
            (resource.numerator_parameter_id, resource.resource_unit),
            (resource.sample_denominator_parameter_id, "source_sample"),
        ):
            if pid not in values or values[pid][1] != unit:
                msg = "Sample parameter missing or unit mismatch"
                raise ValueError(msg)
            value = values[pid][0]
            parts = value.as_tuple()
            if (
                value < 0
                or not isinstance(parts.exponent, int)
                or abs(parts.exponent) > MAX_DIGITS
                or len(parts.digits) > MAX_DIGITS
            ):
                msg = "Sample value exceeds nonnegative numeric profile"
                raise ValueError(msg)
            source_values.append(Fraction(value))
        numerator, denominator = source_values
        if denominator <= 0 or denominator.denominator != 1:
            msg = "Sample denominator requires positive whole samples"
            raise ValueError(msg)
        for case in resource.case_ids:
            quantity = numerator * factors[case] / denominator
            ids: list[str] = []
            for value, unit in (
                (quantity.numerator, resource.resource_unit),
                (quantity.denominator, "declared_requested_test"),
            ):
                raw = _bounded_integer(value)
                pid = f"sample-derived:{lineage}:{len(quantities)}:{len(ids)}"
                if pid in used_ids:
                    msg = "Derived sample parameter/source identity collision"
                    raise ValueError(msg)
                used_ids.add(pid)
                path = directory / f"{len(quantities)}-{len(ids)}.txt"
                path.write_text(raw + "\n", encoding="utf-8")
                source = SourceRecord(
                    source_id=pid,
                    sha256=sha256(path.read_bytes()).hexdigest(),
                    edition="sample-allocation-import-v1",
                    locator="line 1",
                    limitations=f"Computed sample attribution {lineage}; "
                    "not independent evidence or physical consumption",
                )
                parameter = Parameter(
                    parameter_id=pid,
                    raw_value=raw,
                    derived_value=raw,
                    unit=unit,
                    source_sha256=source.sha256,
                    source_locator="line 1",
                    transformation="identity",
                    uncertainty="Conditional exact source/sample attribution",
                    status="derived",
                )
                parameters.append(parameter)
                qualifications.append(
                    ParameterQualification(
                        parameter=parameter,
                        source=source,
                        exact_support=raw,
                        dimensional_basis=unit,
                        applicability=f"Computed rational quantity {lineage}",
                        qualification="qualified",
                        blockers=(),
                    ),
                )
                periods.append(
                    SourceValidity(
                        source=source,
                        retrieved=pricing.derivation_date,
                        effective_from=inputs.context.costing_date,
                        effective_until=inputs.context.costing_date,
                        applicability_kind="observation",
                        date_basis=("Computed at original qualified costing date"),
                    ),
                )
                snapshots[pid] = path
                ids.append(pid)
            quantities.append(
                {
                    "resource_id": resource.resource_id,
                    "case_id": case,
                    "numerator_parameter_id": ids[0],
                    "denominator_parameter_id": ids[1],
                },
            )
    original = inputs.context.ledger.parameter_set
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id=original.version_id,
                workbook_sha256=original.workbook_sha256,
                parameters=tuple(parameters),
            ),
            qualifications=tuple(qualifications),
        ),
        snapshots,
        tuple(periods),
        inputs.context.costing_date,
        inputs.context.native_usage,
    )
    requested = RequestedAllocationPricing.model_validate(
        {
            "format_version": "requested-allocations-v1",
            "workload_sha256": pricing.workload_sha256,
            "currency": pricing.currency,
            "price_year": pricing.price_year,
            "tax_basis": pricing.tax_basis,
            "resources": [
                r.model_dump(
                    exclude={
                        "numerator_parameter_id",
                        "sample_denominator_parameter_id",
                    },
                )
                for r in pricing.resources
            ],
            "quantities": quantities,
            "assumption_basis": (f"{pricing.assumption_basis}; derivation {lineage}"),
            "scope_limit": pricing.scope_limit,
            "allocation_basis": "declared_requested_cases",
        },
    )
    return WorkflowAllocationInputs(inputs.workflow, requested, context)


def calculate_sample_allocated_workflow_cost(
    inputs: SampleWorkflowInputs,
) -> AllocatedWorkflowCost:
    """Verify sample derivation and invoke unchanged requested allocation cost.

    Args:
        inputs: Original workflow, source ratios/rates and explicit use shares.

    Returns:
        Existing cost result with a hash-bound sample derivation identity.

    Raises:
        ValueError: Mapping, quantity, source, component or frame is invalid.
        OSError: A selected source or temporary numeric snapshot cannot open.

    """
    pricing = SampleAllocationPricing.model_validate(
        inputs.pricing.model_dump(),
    )
    workload = Workload.model_validate(
        inputs.workflow.inventory.workflow.workload.model_dump(),
    )
    if allocation_workload_sha256(workload) != pricing.workload_sha256:
        msg = "Sample allocation workload identity mismatch"
        raise ValueError(msg)
    if sum(len(r.case_ids) for r in pricing.resources) > MAX_ROWS:
        msg = "Sample allocation case scope exceeds row bound"
        raise ValueError(msg)
    if any(v.retrieved > pricing.derivation_date for v in inputs.context.validity):
        msg = "Sample derivation predates retained source retrieval"
        raise ValueError(msg)
    factors = _factors(workload, pricing)
    with TemporaryDirectory(prefix="sample-allocations-") as temporary:
        derived = _derive(inputs, pricing, factors, Path(temporary))
        return calculate_allocated_workflow_cost(derived)
