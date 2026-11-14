# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Fail-closed research cost comparison with explicit source identities.

Evidence qualification is an explicit assertion by the caller, not a claim that
this module has independently verified the truth or transferability of a source.
"""

from decimal import localcontext
from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Literal, Self
lazy from datetime import date
lazy from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from pathlib import Path

NonEmpty = Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Evidence(BaseModel):
    """Record a source and its explicitly asserted qualification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonEmpty
    source_url: AnyHttpUrl | None
    snapshot_sha256: Digest
    locator: NonEmpty
    edition: NonEmpty
    retrieved: date
    evidence_class: Literal["measured", "published", "manufacturer"]
    geography: NonEmpty
    perspective: NonEmpty
    limitations: NonEmpty
    exact_support: NonEmpty
    effective_date: date
    qualification: Literal["qualified", "unresolved"]


class CostObservation(BaseModel):
    """Retain one directly sourced amount without implicit conversion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: NonEmpty
    amount: Decimal = Field(ge=0, allow_inf_nan=False, max_digits=32, decimal_places=16)
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    price_year: int = Field(ge=1900, le=9999)
    denominator: NonEmpty
    tax_basis: NonEmpty
    evidence: Evidence


class EvidenceComparison(BaseModel):
    """Select source observations and a separately identified counterfactual."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline: CostObservation
    candidate: CostObservation
    baseline_workbook_sha256: Digest
    scenario_id: NonEmpty
    process_relationship: Literal["changed_process_counterfactual"]

    @model_validator(mode="after")
    def check_compatibility(self) -> Self:
        """Reject incompatible or unresolved source records."""
        left, right = self.baseline, self.candidate
        if left.evidence.snapshot_sha256 != self.baseline_workbook_sha256:
            message = "Baseline observation must cite the selected workbook"
            raise ValueError(message)
        if left.observation_id == right.observation_id:
            message = "Baseline and candidate need distinct identities"
            raise ValueError(message)
        if left.tax_basis not in {"inclusive", "exclusive"} or right.tax_basis not in {
            "inclusive",
            "exclusive",
        }:
            message = "Comparison requires a resolved, supported tax basis"
            raise ValueError(message)
        if (left.currency, left.price_year, left.denominator, left.tax_basis) != (
            right.currency,
            right.price_year,
            right.denominator,
            right.tax_basis,
        ):
            message = "Incompatible currency, price year or denominator"
            raise ValueError(message)
        if (left.evidence.geography, left.evidence.perspective) != (
            right.evidence.geography,
            right.evidence.perspective,
        ):
            message = "Incompatible geography or costing perspective"
            raise ValueError(message)
        if any(x.evidence.qualification != "qualified" for x in (left, right)):
            message = "Unqualified evidence cannot produce a comparison"
            raise ValueError(message)
        return self


class ComparisonResult(BaseModel):
    """Keep both original records and the derived difference together."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline: CostObservation
    candidate: CostObservation
    baseline_workbook_sha256: Digest
    scenario_id: NonEmpty
    process_relationship: Literal["changed_process_counterfactual"]
    delta: Decimal

    @model_validator(mode="after")
    def consistent_difference(self) -> Self:
        """Reject nonfinite or forged differences between retained amounts."""
        with localcontext() as context:
            context.prec = 50
            expected = self.candidate.amount - self.baseline.amount
        if not self.delta.is_finite() or self.delta != expected:
            message = "Result delta differs from retained observation amounts"
            raise ValueError(message)
        return self


def compare_costs(
    comparison: EvidenceComparison,
    snapshots: dict[str, Path],
    workbook: Path,
) -> ComparisonResult:
    """Verify source bytes then calculate a difference between matched bases."""
    comparison = EvidenceComparison.model_validate(comparison.model_dump())
    if (
        not workbook.is_file()
        or sha256(workbook.read_bytes()).hexdigest()
        != comparison.baseline_workbook_sha256
    ):
        message = "Baseline workbook hash mismatch"
        raise ValueError(message)
    for observation in (comparison.baseline, comparison.candidate):
        source = observation.evidence
        path = snapshots.get(source.source_id)
        if path is None or not path.is_file():
            message = "Required source snapshot missing"
            raise ValueError(message)
        if sha256(path.read_bytes()).hexdigest() != source.snapshot_sha256:
            message = "Source snapshot hash mismatch"
            raise ValueError(message)
    with localcontext() as context:
        context.prec = 50
        difference = comparison.candidate.amount - comparison.baseline.amount
    return ComparisonResult(
        baseline=comparison.baseline,
        candidate=comparison.candidate,
        baseline_workbook_sha256=comparison.baseline_workbook_sha256,
        scenario_id=comparison.scenario_id,
        process_relationship=comparison.process_relationship,
        delta=difference,
    )
