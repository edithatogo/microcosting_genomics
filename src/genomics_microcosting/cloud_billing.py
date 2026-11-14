# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Read normalized cloud bills and allocate signed costs without telemetry.

This project profile is not a provider export standard. Normalization, economic
nonoverlap and workload assignment require separate qualification. Source hashes
and matching context establish identity, not invoice authenticity.
"""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from genomics_microcosting.parameter_provenance import (
    Digest,
    NonEmpty,
)

AMOUNT_SEMANTICS = "signed additive billed/effective rows; no duplicated adjustments"


MAX_DECIMAL_LENGTH = 128


def _decimal(value: str) -> Fraction:
    if (
        len(value) > MAX_DECIMAL_LENGTH
        or re.fullmatch(
            r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,18})?",
            value,
        )
        is None
    ):
        msg = "Cloud value must be a bounded finite decimal string"
        raise ValueError(msg)
    return Fraction(Decimal(value))


class _CloudModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class _BillHeader(_CloudModel):
    format_version: Literal["cloud-bill-json-v1"]
    provider: NonEmpty
    billing_account_id: NonEmpty
    invoice_id: NonEmpty
    exporter_version: NonEmpty
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    billing_start: AwareDatetime
    billing_end: AwareDatetime
    amount_semantics: Literal[
        "signed additive billed/effective rows; no duplicated adjustments"
    ]

    @model_validator(mode="after")
    def ordered_period(self) -> Self:
        """Require a nonempty billing interval with timezone offsets."""
        if self.billing_start >= self.billing_end:
            msg = "Cloud billing period is empty or reversed"
            raise ValueError(msg)
        return self


class CloudBillContext(_BillHeader):
    """Bind independent source, model and parameter identities."""

    source_sha256: Digest
    baseline_sha256: Digest
    parameter_set_id: NonEmpty
    process_graph_sha256: Digest


class CloudBillLine(_CloudModel):
    """Preserve raw charge dimensions and separately reported cost bases."""

    line_id: NonEmpty
    kind: Literal[
        "usage",
        "discount",
        "credit",
        "commitment_purchase",
        "commitment_adjustment",
        "tax",
        "fee",
        "refund",
    ]
    region: NonEmpty | None
    service: NonEmpty
    instance: NonEmpty | None
    resource_id: NonEmpty | None
    commitment_id: NonEmpty | None
    charge_start: AwareDatetime | None
    charge_end: AwareDatetime | None
    billed_quantity: NonEmpty | None
    billed_unit: NonEmpty | None
    billed_amount: NonEmpty
    effective_amount: NonEmpty | None
    description: NonEmpty

    @model_validator(mode="after")
    def check_values(self) -> Self:
        """Reject incomplete dimensions and amounts violating this profile."""
        if (self.charge_start is None) != (self.charge_end is None) or (
            self.charge_start is not None
            and self.charge_end is not None
            and self.charge_start >= self.charge_end
        ):
            msg = "Cloud charge period is incomplete, empty or reversed"
            raise ValueError(msg)
        if (self.billed_quantity is None) != (self.billed_unit is None):
            msg = "Cloud billed quantity/unit pair is incomplete"
            raise ValueError(msg)
        if self.billed_quantity is not None:
            _decimal(self.billed_quantity)
        for text in (self.billed_amount, self.effective_amount):
            if text is None:
                continue
            value = _decimal(text)
            if (self.kind in ("discount", "credit", "refund") and value > 0) or (
                self.kind in ("usage", "commitment_purchase", "fee") and value < 0
            ):
                msg = "Cloud amount sign violates the normalized charge kind"
                raise ValueError(msg)
        return self


class CloudBillSnapshot(_BillHeader):
    """An immutable export retaining unknown effective costs."""

    invoice_billed_total: NonEmpty
    invoice_effective_total: NonEmpty | None
    lines: tuple[CloudBillLine, ...]

    @model_validator(mode="after")
    def check_lines(self) -> Self:
        """Check invoice amounts and unique physical export row identities."""
        _decimal(self.invoice_billed_total)
        if self.invoice_effective_total is not None:
            _decimal(self.invoice_effective_total)
        if len({line.line_id for line in self.lines}) != len(self.lines):
            msg = "Duplicate cloud bill line identity"
            raise ValueError(msg)
        return self


class CloudShare(_CloudModel):
    """One explicitly asserted workload fraction of one bill row."""

    workload_id: NonEmpty
    share: NonEmpty

    @model_validator(mode="after")
    def check_fraction(self) -> Self:
        """Reject invalid or negative fractions without rounding."""
        if not 0 <= _decimal(self.share) <= 1:
            msg = "Cloud allocation share lies outside zero to one"
            raise ValueError(msg)
        return self


class CloudLineAllocation(_CloudModel):
    """Explicit empty shares mean the row is wholly unallocated."""

    line_id: NonEmpty
    shares: tuple[CloudShare, ...]

    @model_validator(mode="after")
    def check_shares(self) -> Self:
        """Reject duplicate workloads and allocation beyond the full row."""
        if (
            len({s.workload_id for s in self.shares}) != len(self.shares)
            or sum((_decimal(s.share) for s in self.shares), Fraction(0)) > 1
        ):
            msg = "Cloud allocation shares overlap or repeat a workload"
            raise ValueError(msg)
        return self


class BillAllocation(_CloudModel):
    """Select tax presentation and a full explicit row allocation recipe."""

    function_version: Literal["cloud-allocation-v1"]
    workload_id: NonEmpty
    tax_basis: Literal["inclusive", "exclusive"]
    lines: tuple[CloudLineAllocation, ...]


@dataclass(frozen=True)
class CloudBasisResult:
    """Keep invoice reconciliation separate from tax-selected allocation."""

    modeled_total: Fraction | None
    tax_total: Fraction | None
    selected_total: Fraction | None
    target_cost: Fraction | None
    other_cost: Fraction | None
    unallocated_cost: Fraction | None
    bill_residual: Fraction | None


@dataclass(frozen=True)
class CloudBillResult:
    """Retain both cost bases, source dimensions and missing effective rows."""

    input_sha256: str
    context: CloudBillContext
    lines: tuple[CloudBillLine, ...]
    billed: CloudBasisResult
    effective: CloudBasisResult
    unknown_effective_line_ids: tuple[str, ...]


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate cloud bill JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def read_cloud_bill(
    payload: bytes,
    context: CloudBillContext,
) -> CloudBillSnapshot:
    """Check raw bytes and declared header identity without authenticating them.

    Args:
        payload: Exact bytes of an explicitly normalized project-profile export.
        context: Independent expected source/header and model identities.

    Returns:
        Immutable raw amounts, dimensions and nullable observations.

    Raises:
        ValueError: Hash, format, declared context or profile validation fails.

    """
    context = CloudBillContext.model_validate(context.model_dump())
    if sha256(payload).hexdigest() != context.source_sha256:
        msg = "Cloud bill source hash mismatch"
        raise ValueError(msg)
    record = CloudBillSnapshot.model_validate(
        json.loads(payload, object_pairs_hook=_unique_fields),
    )
    if any(
        getattr(record, field) != getattr(context, field)
        for field in _BillHeader.model_fields
    ):
        msg = "Cloud bill context mismatch"
        raise ValueError(msg)
    return record


def _sum_known(values: list[Fraction | None]) -> Fraction | None:
    total = Fraction(0)
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _portion(value: Fraction | None, share: Fraction) -> Fraction | None:
    if share == 0:
        return Fraction(0)
    return None if value is None else value * share


def _calculate_basis(
    record: CloudBillSnapshot,
    allocation: BillAllocation,
    basis: Literal["billed", "effective"],
) -> CloudBasisResult:
    recipes = {line.line_id: line for line in allocation.lines}
    values: list[Fraction | None] = []
    taxes: list[Fraction | None] = []
    selected: list[Fraction | None] = []
    target: list[Fraction | None] = []
    other: list[Fraction | None] = []
    unallocated: list[Fraction | None] = []
    for line in record.lines:
        text = line.billed_amount if basis == "billed" else line.effective_amount
        value = None if text is None else _decimal(text)
        values.append(value)
        if line.kind == "tax":
            taxes.append(value)
            if allocation.tax_basis == "exclusive":
                continue
        selected.append(value)
        shares = recipes[line.line_id].shares
        own = sum(
            (
                _decimal(s.share)
                for s in shares
                if s.workload_id == allocation.workload_id
            ),
            Fraction(0),
        )
        rest = sum(
            (
                _decimal(s.share)
                for s in shares
                if s.workload_id != allocation.workload_id
            ),
            Fraction(0),
        )
        target.append(_portion(value, own))
        other.append(_portion(value, rest))
        unallocated.append(_portion(value, 1 - own - rest))
    total = _sum_known(values)
    bill = (
        record.invoice_billed_total
        if basis == "billed"
        else record.invoice_effective_total
    )
    residual = None if bill is None or total is None else _decimal(bill) - total
    return CloudBasisResult(
        total,
        _sum_known(taxes),
        _sum_known(selected),
        _sum_known(target),
        _sum_known(other),
        _sum_known(unallocated),
        residual,
    )


def allocate_cloud_bill(
    payload: bytes,
    context: CloudBillContext,
    allocation: BillAllocation,
) -> CloudBillResult:
    """Allocate signed billed/effective rows exactly without deriving usage.

    Args:
        payload: Exact normalized bill bytes; never a telemetry file.
        context: Expected source and independent process/parameter identities.
        allocation: Complete row coverage and explicit workload shares.

    Returns:
        Both cost bases, tax-selected allocation and full invoice residuals.

    Raises:
        ValueError: Source, identity, amount or complete allocation checks fail.

    """
    context = CloudBillContext.model_validate(context.model_dump())
    allocation = BillAllocation.model_validate(allocation.model_dump())
    record = read_cloud_bill(payload, context)
    identifiers = {line.line_id for line in record.lines}
    selected = {line.line_id for line in allocation.lines}
    if selected != identifiers or len(selected) != len(allocation.lines):
        msg = "Cloud allocation coverage must match every line exactly once"
        raise ValueError(msg)
    identity = context.model_dump(mode="json")
    identity["allocation"] = allocation.model_dump(mode="json")
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return CloudBillResult(
        digest,
        context,
        record.lines,
        _calculate_basis(record, allocation, "billed"),
        _calculate_basis(record, allocation, "effective"),
        tuple(line.line_id for line in record.lines if line.effective_amount is None),
    )
