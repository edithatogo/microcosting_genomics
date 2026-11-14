# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Contract tests for source-bound, explicit comparative costing."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from pydantic import AnyHttpUrl, ValidationError

from genomics_microcosting.parameter_provenance import (
    ComparisonResult,
    CostObservation,
    Evidence,
    EvidenceComparison,
    compare_costs,
)
from tests.checks import require_equal

if TYPE_CHECKING:
    from pathlib import Path


def evidence(snapshot: Path) -> Evidence:
    """Create a synthetic source-bound evidence record."""
    return Evidence(
        source_id="synthetic-source",
        source_url=AnyHttpUrl("https://example.org/source"),
        snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        locator="table 1, row A",
        edition="v1",
        retrieved=date(2026, 11, 6),
        evidence_class="measured",
        geography="AU",
        perspective="provider",
        limitations="synthetic test only",
        exact_support="table 1 row A",
        effective_date=date(2026, 1, 1),
        qualification="qualified",
    )


def test_explicit_source_bound_comparison(tmp_path: Path) -> None:
    """Compare selected values without mutating either record."""
    snapshot = tmp_path / "source.bin"
    snapshot.write_bytes(b"Synthetic observation table")
    source = evidence(snapshot)
    workbook = tmp_path / "baseline.xlsm"
    workbook.write_bytes(b"synthetic workbook")
    workbook_hash = hashlib.sha256(workbook.read_bytes()).hexdigest()
    baseline_source = evidence(workbook).model_copy(
        update={"source_id": "workbook", "source_url": None},
    )
    baseline = CostObservation(
        observation_id="baseline",
        amount=Decimal(100),
        currency="AUD",
        price_year=2026,
        denominator="test",
        tax_basis="inclusive",
        evidence=baseline_source,
    )
    candidate = CostObservation(
        observation_id="candidate",
        amount=Decimal(80),
        currency="AUD",
        price_year=2026,
        denominator="test",
        tax_basis="inclusive",
        evidence=source,
    )
    comparison = EvidenceComparison(
        baseline=baseline,
        candidate=candidate,
        baseline_workbook_sha256=workbook_hash,
        scenario_id="scenario-1",
        process_relationship="changed_process_counterfactual",
    )
    result = compare_costs(
        comparison,
        {source.source_id: snapshot, baseline_source.source_id: workbook},
        workbook,
    )
    require_equal(result.delta, Decimal(-20))
    for invalid in (Decimal(0), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValueError, match=r"delta differs|finite number"):
            ComparisonResult.model_validate(result.model_dump() | {"delta": invalid})

    require_equal(result.baseline, baseline)
    require_equal(result.candidate, candidate)
    require_equal(result.process_relationship, "changed_process_counterfactual")
    for unresolved in ("unknown", "not stated", ""):
        with pytest.raises(ValidationError):
            EvidenceComparison.model_validate(
                comparison.model_dump()
                | {
                    "baseline": baseline.model_dump() | {"tax_basis": unresolved},
                    "candidate": candidate.model_dump() | {"tax_basis": unresolved},
                },
            )
    forged = comparison.model_copy(
        update={"candidate": candidate.model_copy(update={"currency": "USD"})},
    )
    with pytest.raises(ValidationError):
        compare_costs(
            forged,
            {source.source_id: snapshot, baseline_source.source_id: workbook},
            workbook,
        )
    unqualified = candidate.model_copy(
        update={"evidence": source.model_copy(update={"qualification": "unresolved"})},
    )
    with pytest.raises(ValidationError):
        compare_costs(
            comparison.model_copy(update={"candidate": unqualified}),
            {source.source_id: snapshot, baseline_source.source_id: workbook},
            workbook,
        )
    with pytest.raises(ValueError, match="snapshot"):
        compare_costs(comparison, {baseline_source.source_id: workbook}, workbook)
    workbook.write_bytes(b"tampered workbook")
    with pytest.raises(ValueError, match="workbook"):
        compare_costs(
            comparison,
            {source.source_id: snapshot, baseline_source.source_id: workbook},
            workbook,
        )
    workbook.write_bytes(b"synthetic workbook")
    snapshot.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="snapshot"):
        compare_costs(
            comparison,
            {source.source_id: snapshot, baseline_source.source_id: workbook},
            workbook,
        )


def test_unqualified_and_incompatible_data_fail_closed(tmp_path: Path) -> None:
    """Reject missing evidence and incompatible price bases."""
    snapshot = tmp_path / "source.bin"
    snapshot.write_bytes(b"test")
    source = evidence(snapshot)
    workbook = tmp_path / "baseline.xlsm"
    workbook.write_bytes(b"synthetic workbook")
    workbook_hash = hashlib.sha256(workbook.read_bytes()).hexdigest()
    baseline_source = evidence(workbook).model_copy(
        update={"source_id": "workbook", "source_url": None},
    )
    baseline = CostObservation(
        observation_id="baseline",
        amount=Decimal(1),
        currency="AUD",
        price_year=2026,
        denominator="test",
        tax_basis="inclusive",
        evidence=baseline_source,
    )
    candidate = CostObservation(
        observation_id="candidate",
        amount=Decimal(1),
        currency="USD",
        price_year=2026,
        denominator="test",
        tax_basis="inclusive",
        evidence=source,
    )
    with pytest.raises(ValidationError):
        EvidenceComparison(
            baseline=baseline,
            candidate=candidate,
            baseline_workbook_sha256=workbook_hash,
            scenario_id="s",
            process_relationship="changed_process_counterfactual",
        )
    with pytest.raises(ValidationError):
        CostObservation(
            observation_id="bad",
            amount=Decimal("NaN"),
            currency="AUD",
            price_year=2026,
            denominator="test",
            tax_basis="inclusive",
            evidence=source,
        )
    with pytest.raises(ValidationError):
        Evidence.model_validate(
            {**source.model_dump(), "qualification": "unresolved", "locator": ""},
        )


def test_source_cost_preserves_workbook_precision(tmp_path: Path) -> None:
    """Retain a workbook's full cached numeric value without rounding it."""
    snapshot = tmp_path / "source.bin"
    snapshot.write_bytes(b"synthetic")
    observation = CostObservation(
        observation_id="baseline",
        amount=Decimal("145.34173233368602"),
        currency="AUD",
        price_year=2023,
        denominator="test",
        tax_basis="unknown",
        evidence=evidence(snapshot),
    )
    require_equal(observation.amount, Decimal("145.34173233368602"))
