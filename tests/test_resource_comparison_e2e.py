# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify the complete synthetic resource/source bridge with real validators."""

import hashlib
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
lazy from pathlib import Path

import pytest
from openpyxl import Workbook

from genomics_microcosting.parameter_provenance import (
    CostObservation,
    Evidence,
    EvidenceComparison,
)
from genomics_microcosting.provenance_ledger import (
    InputManifest,
    InputRequirement,
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from genomics_microcosting.resource_accounting import (
    BaselineDisposition,
    DraftParameterBindings,
    DraftResourceComparison,
    ResourceLine,
    ResourceParameterBinding,
)
from genomics_microcosting.resource_comparison import (
    DerivedResourceRequest,
    ResourceComparisonRequest,
    compare_derived_resource_draft,
    compare_source_checked_resource_draft,
)
from genomics_microcosting.scenario_comparison import (
    ComparisonSources,
    QualificationContext,
)
from genomics_microcosting.uncertainty_provenance import (
    BoundValue,
    EvidenceDeclaration,
    UncertaintyLedger,
    UncertaintyRecord,
)
from tests import checks


def _write_workbook(workbook: Path) -> str:
    """Create and identify the synthetic baseline."""
    book = Workbook()
    for i in range(1, 17):
        book.create_sheet(f"sheet{i}")
    for cell, value in (
        ("A1", 2),
        ("A2", 3),
        ("A3", 1),
        ("A4", 4),
        ("A5", 2),
        ("A6", 3),
        ("A7", 5),
        ("A8", 1),
        ("A9", 3),
        ("N5", 6),
    ):
        book.worksheets[16][cell] = value
    book.save(workbook)
    return hashlib.sha256(workbook.read_bytes()).hexdigest()


def test_source_checked_resource_draft_real_validators(tmp_path: Path) -> None:
    """Synthetic source bytes and dates are verified and tampering fails closed."""
    workbook = tmp_path / "baseline.xlsx"
    digest = _write_workbook(workbook)
    snapshot = tmp_path / "candidate.txt"
    snapshot.write_text("candidate cost 8 AUD per sample", encoding="utf-8")
    candidate_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    catalogue = {
        "format_version": "1.0.0",
        "workbook_sha256": digest,
        "process_source_rows_sha256": "b" * 64,
        "sources": [
            {
                "source_id": "SRC1",
                "title": "Synthetic",
                "url": "https://example.org/source",
                "snapshot_url": "https://example.org/source",
                "locator": "line 1",
                "edition": "v1",
                "accessed": "2026-11-06",
                "evidence_class": "primary_study",
                "source_snapshot_sha256": candidate_digest,
                "limitation": "synthetic",
            },
            {
                "source_id": "param-p2",
                "title": "Synthetic price source",
                "url": "https://example.org/price",
                "snapshot_url": "https://example.org/price",
                "locator": "WB17:A5",
                "edition": "v1",
                "accessed": "2026-11-06",
                "evidence_class": "primary_study",
                "source_snapshot_sha256": digest,
                "limitation": "synthetic",
            },
        ],
        "candidates": [
            {
                "candidate_id": "C1",
                "label": "Synthetic",
                "source_ids": ["SRC1", "param-p2"],
                "baseline_locations": ["WB17:N5"],
                "process_relationship": "changed_process",
                "evidence_state": "qualified_for_comparison",
                "unknowns": ["synthetic limitations"],
                "qualified_baseline_locations": ["WB17:N5"],
                "required_baseline_parameter_ids": ["q"],
                "qualification_summary": "synthetic only",
            },
        ],
        "scenarios": [
            {
                "scenario_id": "S1",
                "candidate_id": "C1",
                "kind": "changed_process_counterfactual",
                "baseline_identity": digest,
                "limitations": ["synthetic only"],
            },
        ],
    }
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(catalogue), encoding="utf-8")
    common = {
        "edition": "v1",
        "retrieved": date(2026, 11, 6),
        "evidence_class": "measured",
        "geography": "AU",
        "perspective": "provider",
        "limitations": "synthetic",
        "effective_date": date(2026, 1, 1),
        "qualification": "qualified",
    }
    base_evidence = Evidence.model_validate(
        common
        | {
            "source_id": "WB",
            "source_url": None,
            "snapshot_sha256": digest,
            "locator": "WB17:N5",
            "exact_support": "WB17:N5",
        },
    )
    candidate_evidence = Evidence.model_validate(
        common
        | {
            "source_id": "SRC1",
            "source_url": "https://example.org/source",
            "snapshot_sha256": candidate_digest,
            "locator": "line 1",
            "exact_support": "candidate cost 8 AUD per sample",
        },
    )

    def obs(name: str, amount: int, evidence: Evidence) -> CostObservation:
        return CostObservation(
            observation_id=name,
            amount=Decimal(amount),
            currency="AUD",
            price_year=2026,
            denominator="sample",
            tax_basis="inclusive",
            evidence=evidence,
        )

    comparison = EvidenceComparison(
        baseline=obs("base", 6, base_evidence),
        candidate=obs("candidate", 8, candidate_evidence),
        baseline_workbook_sha256=digest,
        scenario_id="S1",
        process_relationship="changed_process_counterfactual",
    )
    specs = (
        ("q", "2", "item/sample", "A1"),
        ("p", "3", "AUD/item", "A2"),
        ("a", "1", "fraction", "A3"),
        ("q2", "4", "item/sample", "A4"),
        ("p2", "2", "AUD/item", "A5"),
        ("t", "6", "AUD/sample", "N5"),
    )
    parameters = tuple(
        Parameter(
            parameter_id=n,
            raw_value=v,
            derived_value=v,
            unit=u,
            source_sha256=digest,
            source_locator=f"WB17:{cell}",
            transformation="identity",
            uncertainty="synthetic",
            status="observed",
        )
        for n, v, u, cell in specs
    )
    parameter_set = ParameterSet(
        version_id="v1",
        workbook_sha256=digest,
        parameters=parameters,
    )
    records = tuple(
        SourceRecord(
            source_id=f"param-{p.parameter_id}",
            sha256=digest,
            edition="v1",
            locator=p.source_locator,
            limitations="synthetic",
        )
        for p in parameters
    )
    qualifications = tuple(
        ParameterQualification(
            parameter=p,
            source=s,
            exact_support="synthetic",
            dimensional_basis="synthetic",
            applicability="synthetic",
            qualification="qualified",
            blockers=(),
        )
        for p, s in zip(parameters, records, strict=True)
    )
    ledger = QualificationLedger(
        parameter_set=parameter_set,
        qualifications=qualifications,
    )
    items = tuple(
        InputRequirement(
            input_id=p.parameter_id,
            resource_id="kit",
            role="synthetic",
            parameter=p,
            qualification=q,
            blockers=(),
        )
        for p, q in zip(parameters, qualifications, strict=True)
    )
    manifest = InputManifest(
        version_id="m1",
        candidate_id="C1",
        workbook_sha256=digest,
        scope="synthetic",
        required_ids=tuple(p.parameter_id for p in parameters),
        inputs=items,
    )
    sources = (
        *records,
        SourceRecord(
            source_id="WB",
            sha256=digest,
            edition="v1",
            locator="WB17:N5",
            limitations="synthetic",
        ),
        SourceRecord(
            source_id="SRC1",
            sha256=candidate_digest,
            edition="v1",
            locator="line 1",
            limitations="synthetic",
        ),
    )
    validity = tuple(
        SourceValidity(
            source=s,
            retrieved=date(2026, 11, 6),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
            date_basis="synthetic",
        )
        for s in sources
    )
    uncertainty = UncertaintyLedger(
        parameter_set=parameter_set,
        records=tuple(
            _uncertainty_record(p, s) for p, s in zip(parameters, records, strict=True)
        ),
    )
    snapshots = {
        s.source_id: (snapshot if s.source_id == "SRC1" else workbook) for s in sources
    }
    context = QualificationContext(
        ledger=ledger,
        validity=validity,
        costing_date=date(2026, 6, 1),
        manifest=manifest,
        uncertainty=uncertainty,
    )
    line = ResourceLine(
        resource_id="kit",
        quantity=Decimal(2),
        quantity_unit="item",
        unit_cost=Decimal(3),
        cost_denominator_unit="item",
        currency="AUD",
        allocation=Decimal(1),
    )
    alternative = ResourceLine(
        resource_id="new-kit",
        quantity=Decimal(4),
        quantity_unit="item",
        unit_cost=Decimal(2),
        cost_denominator_unit="item",
        currency="AUD",
        allocation=Decimal(1),
    )
    disposition = BaselineDisposition(
        baseline_resource_id="kit",
        action="replaced",
        candidate_resource_ids=("new-kit",),
        residual_treatment="none",
        stranded_resource_ids=(),
    )
    draft = DraftResourceComparison(
        baseline=(line,),
        candidate=(alternative,),
        dispositions=(disposition,),
        added_candidate_ids=(),
        baseline_total=Decimal(6),
        functional_unit="sample",
        currency="AUD",
    )
    binding = ResourceParameterBinding(
        arm="baseline",
        resource_id="kit",
        quantity_parameter_id="q",
        unit_cost_parameter_id="p",
        allocation_parameter_id="a",
    )
    bindings = DraftParameterBindings(
        parameter_version_id="v1",
        baseline_total_parameter_id="t",
        lines=(
            binding,
            ResourceParameterBinding(
                arm="candidate",
                resource_id="new-kit",
                quantity_parameter_id="q2",
                unit_cost_parameter_id="p2",
                allocation_parameter_id="a",
            ),
        ),
    )
    request = ResourceComparisonRequest(
        catalogue_path=path,
        scenario_id="S1",
        comparison=comparison,
        sources=ComparisonSources(snapshots, workbook, parameter_set),
        qualification=context,
        draft=draft,
        bindings=bindings,
    )
    checks.require_equal(
        compare_source_checked_resource_draft(request).comparison.delta,
        Decimal(2),
    )
    _check_derived_without_observation(request, snapshot)
    forged_line = alternative.model_copy(update={"quantity": Decimal(3)})
    forged_draft = draft.model_copy(update={"candidate": (forged_line,)})
    with pytest.raises(ValueError, match="value or unit"):
        compare_source_checked_resource_draft(replace(request, draft=forged_draft))
    outside_period = replace(
        request,
        qualification=replace(context, costing_date=date(2027, 1, 1)),
    )
    with pytest.raises(ValueError, match="does not cover"):
        compare_source_checked_resource_draft(outside_period)
    snapshot.write_text("candidate cost 7 AUD per sample", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        compare_source_checked_resource_draft(request)


def _uncertainty_record(p: Parameter, source: SourceRecord) -> UncertaintyRecord:
    """Create synthetic source-bound input bounds."""
    if p.raw_value is None:
        pytest.fail("A synthetic parameter must declare its source value")
    bound = BoundValue(
        value=Decimal(p.raw_value),
        locator=p.source_locator,
        absence_reason=None,
    )
    if p.parameter_id == "q2":
        low = BoundValue(value=Decimal(3), locator="WB17:A6", absence_reason=None)
        high = BoundValue(value=Decimal(5), locator="WB17:A7", absence_reason=None)
    elif p.parameter_id == "p2":
        low = BoundValue(value=Decimal(1), locator="WB17:A8", absence_reason=None)
        high = BoundValue(value=Decimal(3), locator="WB17:A9", absence_reason=None)
    else:
        low = high = bound
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic only",
        source=source,
    )
    return UncertaintyRecord(
        measure_id=p.parameter_id,
        unit=p.unit,
        source=source,
        lower=low,
        midpoint=bound,
        upper=high,
        interpretation="reported_range",
        interpretation_evidence=declared,
        distribution=declared,
        dependence=declared,
    )


def _check_derived_without_observation(
    request: ResourceComparisonRequest,
    snapshot: Path,
) -> None:
    derived_request = DerivedResourceRequest(
        catalogue_path=request.catalogue_path,
        scenario_id=request.scenario_id,
        baseline=request.comparison.baseline,
        sources=request.sources,
        qualification=request.qualification,
        draft=request.draft,
        bindings=request.bindings,
        candidate_price_year=2026,
        candidate_tax_basis="inclusive",
    )
    snapshot.unlink()
    try:
        derived = compare_derived_resource_draft(derived_request)
        checks.require_equal(
            (derived.candidate_total, derived.delta),
            (Decimal(8), Decimal(2)),
        )
        checks.require_equal(derived.baseline_bounds, (Decimal(6), Decimal(6)))
        checks.require_equal(derived.candidate_bounds, (Decimal(3), Decimal(15)))
        checks.require_equal(derived.delta_bounds, (Decimal(-3), Decimal(9)))
        with pytest.raises(ValueError, match="cost basis"):
            compare_derived_resource_draft(
                replace(derived_request, candidate_tax_basis="unknown"),
            )
        ledger = request.qualification.ledger
        other_set = ledger.parameter_set.model_copy(
            update={"workbook_sha256": "c" * 64},
        )
        other_ledger = ledger.model_copy(update={"parameter_set": other_set})
        other_context = replace(request.qualification, ledger=other_ledger)
        with pytest.raises(ValueError, match="workbook identities differ"):
            compare_derived_resource_draft(
                replace(derived_request, qualification=other_context),
            )
        original = request.catalogue_path.read_text(encoding="utf-8")
        altered = json.loads(original)
        altered["candidates"][0]["source_ids"] = ["SRC1"]
        request.catalogue_path.write_text(json.dumps(altered), encoding="utf-8")
        try:
            with pytest.raises(ValueError, match="price source is absent"):
                compare_derived_resource_draft(derived_request)
            altered["candidates"][0]["evidence_state"] = "research_lead"
            request.catalogue_path.write_text(json.dumps(altered), encoding="utf-8")
            with pytest.raises(ValueError, match="not qualified"):
                compare_derived_resource_draft(derived_request)
        finally:
            request.catalogue_path.write_text(original, encoding="utf-8")
    finally:
        snapshot.write_text("candidate cost 8 AUD per sample", encoding="utf-8")
