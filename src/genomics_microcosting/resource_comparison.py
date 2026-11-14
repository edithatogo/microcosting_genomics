# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Connect draft resource arithmetic to existing source-qualified observations.

This is provisional: no code can infer whether the declared resource scope,
clinical equivalence, fixed-cost treatment or uncertainty is complete.
"""

import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256
from typing import TYPE_CHECKING

from genomics_microcosting.alternative_research import (
    ResearchCandidate,
    ResearchCatalogue,
)
from genomics_microcosting.parameter_provenance import CostObservation
from genomics_microcosting.provenance_ledger import InputManifest
from genomics_microcosting.resource_accounting import (
    DraftParameterBindings,
    DraftResourceComparison,
)
from genomics_microcosting.scenario_comparison import (
    QualifiedComparisonResult,
    compare_qualified_scenario,
    verify_baseline_cell,
    verify_qualified_inputs,
)
from genomics_microcosting.t1_baseline_lineage import require_known_baseline_scope

if TYPE_CHECKING:
    from pathlib import Path

    from genomics_microcosting.parameter_provenance import EvidenceComparison
    from genomics_microcosting.scenario_comparison import (
        ComparisonSources,
        QualificationContext,
    )
    from genomics_microcosting.uncertainty_provenance import UncertaintyLedger


@dataclass(frozen=True)
class SourceCheckedResourceDraft:
    """Retain the source-checked observation and exact declared draft identities."""

    comparison: QualifiedComparisonResult
    resource_model_sha256: str
    parameter_bindings_sha256: str


@dataclass(frozen=True)
class ResourceComparisonRequest:
    """Identify all inputs to an explicitly selected draft comparison."""

    catalogue_path: Path
    scenario_id: str
    comparison: EvidenceComparison
    sources: ComparisonSources
    qualification: QualificationContext
    draft: DraftResourceComparison
    bindings: DraftParameterBindings


def _digest(model: DraftResourceComparison | DraftParameterBindings) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode()).hexdigest()


def compare_source_checked_resource_draft(
    request: ResourceComparisonRequest,
) -> SourceCheckedResourceDraft:
    """Reconcile declared resource arithmetic with source-checked observations.

    This binds parameter values and units to the checked manifest and requires
    declared uncertainty; it does not establish that the declared scope is whole.
    """
    draft = DraftResourceComparison.model_validate(request.draft.model_dump())
    bindings = DraftParameterBindings.model_validate(request.bindings.model_dump())
    qualification = request.qualification
    if qualification.manifest is None or qualification.uncertainty is None:
        msg = "Resource comparison requires a manifest and declared uncertainty"
        raise ValueError(msg)
    manifest = InputManifest.model_validate(qualification.manifest.model_dump())
    bindings.verify_values(draft, qualification.ledger.parameter_set)
    numeric_ids = {
        item.input_id for item in manifest.inputs if item.value_kind == "numeric"
    }
    ids = {bindings.baseline_total_parameter_id}
    for binding in bindings.lines:
        ids.update(
            (
                binding.quantity_parameter_id,
                binding.unit_cost_parameter_id,
                binding.allocation_parameter_id,
            ),
        )
    if not ids <= numeric_ids:
        msg = "Resource parameters must be numeric inputs in the required manifest"
        raise ValueError(msg)
    result = compare_qualified_scenario(
        request.catalogue_path,
        request.scenario_id,
        request.comparison,
        request.sources,
        qualification,
    )
    if result.uncertainty_status != "bounds_and_source_bytes_checked":
        msg = "Resource uncertainty source checks are incomplete"
        raise ValueError(msg)
    candidate_total, delta = draft.calculate_draft()
    baseline, candidate = result.baseline, result.candidate
    if (
        baseline.amount != draft.baseline_total
        or candidate.amount != candidate_total
        or result.delta != delta
        or baseline.currency != draft.currency
        or candidate.currency != draft.currency
        or baseline.denominator != draft.functional_unit
        or candidate.denominator != draft.functional_unit
    ):
        msg = "Resource totals or functional units differ from source observations"
        raise ValueError(msg)
    return SourceCheckedResourceDraft(result, _digest(draft), _digest(bindings))


@dataclass(frozen=True)
class DerivedResourceRequest:
    """Supply a baseline and declared candidate basis for a derived draft total."""

    catalogue_path: Path
    scenario_id: str
    baseline: CostObservation
    sources: ComparisonSources
    qualification: QualificationContext
    draft: DraftResourceComparison
    bindings: DraftParameterBindings
    candidate_price_year: int
    candidate_tax_basis: str


@dataclass(frozen=True)
class DerivedResourceDraft:
    """Keep a calculated total distinct from an externally observed total."""

    baseline: CostObservation
    candidate_total: Decimal
    delta: Decimal
    scenario_id: str
    catalogue_sha256: str
    qualification_sha256: str
    resource_model_sha256: str
    parameter_bindings_sha256: str
    baseline_bounds: tuple[Decimal, Decimal]
    candidate_bounds: tuple[Decimal, Decimal]
    delta_bounds: tuple[Decimal, Decimal]
    limitations: str = (
        "Ranges are conservative bounds, not probabilities; declared scope, "
        "dependence and scientific suitability are not independently established"
    )


def _check_derived_baseline(
    request: DerivedResourceRequest,
    baseline: CostObservation,
    draft: DraftResourceComparison,
    catalogue: ResearchCatalogue,
    candidate: ResearchCandidate,
) -> None:
    if (
        baseline.evidence.qualification != "qualified"
        or baseline.evidence.locator not in candidate.qualified_baseline_locations
    ):
        msg = "Baseline observation is unqualified or outside candidate scope"
        raise ValueError(msg)
    if (
        baseline.evidence.snapshot_sha256 != catalogue.workbook_sha256
        or sha256(request.sources.workbook.read_bytes()).hexdigest()
        != catalogue.workbook_sha256
    ):
        msg = "Baseline workbook identity differs"
        raise ValueError(msg)
    if (
        baseline.amount != draft.baseline_total
        or baseline.currency != draft.currency
        or baseline.denominator != draft.functional_unit
        or baseline.tax_basis not in {"inclusive", "exclusive"}
        or baseline.tax_basis != request.candidate_tax_basis
        or baseline.price_year != request.candidate_price_year
    ):
        msg = "Baseline and candidate cost basis differ or remain unresolved"
        raise ValueError(msg)
    require_known_baseline_scope(
        catalogue.workbook_sha256,
        baseline.evidence.locator,
        candidate.required_baseline_parameter_ids,
    )


def _check_candidate_prices(
    context: QualificationContext,
    draft: DraftResourceComparison,
    bindings: DraftParameterBindings,
    catalogue: ResearchCatalogue,
    candidate: ResearchCandidate,
) -> None:
    checked_sources = {
        q.parameter.parameter_id: q.source for q in context.ledger.qualifications
    }
    catalogue_sources = {
        s.source_id: s for s in catalogue.sources if s.source_id in candidate.source_ids
    }
    changed_ids = {
        x
        for d in draft.dispositions
        if d.action == "replaced"
        for x in d.candidate_resource_ids
    } | set(draft.added_candidate_ids)
    for binding in bindings.lines:
        if binding.arm == "candidate" and binding.resource_id in changed_ids:
            source = checked_sources[binding.unit_cost_parameter_id]
            registered = catalogue_sources.get(source.source_id)
            if registered is None or registered.source_snapshot_sha256 != source.sha256:
                msg = "Changed resource price source is absent from candidate catalogue"
                raise ValueError(msg)


def _resource_envelopes(
    bindings: DraftParameterBindings,
    uncertainty: UncertaintyLedger,
) -> tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal], tuple[Decimal, Decimal]]:
    """Compute conservative extrema over the declared nonnegative input bounds."""
    records = {record.measure_id: record for record in uncertainty.records}
    totals = {
        "baseline": [Decimal(0), Decimal(0)],
        "candidate": [Decimal(0), Decimal(0)],
    }
    with localcontext() as ctx:
        ctx.prec = 50
        ctx.traps[Inexact] = True
        for binding in bindings.lines:
            selected = (
                records[binding.quantity_parameter_id],
                records[binding.unit_cost_parameter_id],
                records[binding.allocation_parameter_id],
            )
            bounds = [(item.lower.value, item.upper.value) for item in selected]
            if any(low is None or high is None or low < 0 for low, high in bounds):
                msg = "Resource bounds are incomplete or negative"
                raise ValueError(msg)
            quantity, price, allocation = bounds
            qlow, qhigh = quantity
            plow, phigh = price
            alow, ahigh = allocation
            if (
                qlow is None
                or qhigh is None
                or plow is None
                or phigh is None
                or alow is None
                or ahigh is None
                or ahigh > 1
            ):
                msg = "Resource bounds or allocation range are invalid"
                raise ValueError(msg)
            totals[binding.arm][0] += qlow * plow * alow
            totals[binding.arm][1] += qhigh * phigh * ahigh
        baseline = (totals["baseline"][0], totals["baseline"][1])
        candidate = (totals["candidate"][0], totals["candidate"][1])
        delta = (candidate[0] - baseline[1], candidate[1] - baseline[0])
    return baseline, candidate, delta


def compare_derived_resource_draft(
    request: DerivedResourceRequest,
) -> DerivedResourceDraft:
    """Calculate from source-checked inputs without inventing an observed total."""
    draft = DraftResourceComparison.model_validate(request.draft.model_dump())
    bindings = DraftParameterBindings.model_validate(request.bindings.model_dump())
    baseline = CostObservation.model_validate(request.baseline.model_dump())
    context = request.qualification
    if context.manifest is None or context.uncertainty is None:
        msg = "Resource comparison requires a manifest and declared uncertainty"
        raise ValueError(msg)
    catalogue_bytes = request.catalogue_path.read_bytes()
    catalogue = ResearchCatalogue.model_validate_json(catalogue_bytes)
    if context.ledger.parameter_set.workbook_sha256 != catalogue.workbook_sha256:
        msg = "Parameter ledger and catalogue workbook identities differ"
        raise ValueError(msg)
    scenario = next(
        (s for s in catalogue.scenarios if s.scenario_id == request.scenario_id),
        None,
    )
    if scenario is None:
        raise KeyError(request.scenario_id)
    candidate = next(
        c for c in catalogue.candidates if c.candidate_id == scenario.candidate_id
    )
    if (
        candidate.evidence_state != "qualified_for_comparison"
        or scenario.kind != "changed_process_counterfactual"
        or candidate.process_relationship != "changed_process"
    ):
        msg = "Candidate or scenario is not qualified for comparison"
        raise ValueError(msg)
    _check_derived_baseline(request, baseline, draft, catalogue, candidate)
    manifest, uncertainty = verify_qualified_inputs(
        context,
        request.sources,
        candidate.candidate_id,
        candidate.required_baseline_parameter_ids,
    )
    if uncertainty is None:
        msg = "Resource uncertainty source checks are incomplete"
        raise ValueError(msg)
    bindings.verify_values(draft, context.ledger.parameter_set)
    numeric_ids = {i.input_id for i in manifest.inputs if i.value_kind == "numeric"}
    ids = {bindings.baseline_total_parameter_id}
    for item in bindings.lines:
        ids.update(
            (
                item.quantity_parameter_id,
                item.unit_cost_parameter_id,
                item.allocation_parameter_id,
            ),
        )
    if not ids <= numeric_ids:
        msg = "Resource parameters must be numeric inputs in the required manifest"
        raise ValueError(msg)
    periods = {p.source.source_id: p for p in context.validity}
    period = periods.get(baseline.evidence.source_id)
    if period is None or (
        period.source.sha256,
        period.source.edition,
        period.source.locator,
    ) != (
        baseline.evidence.snapshot_sha256,
        baseline.evidence.edition,
        baseline.evidence.locator,
    ):
        msg = "Baseline source validity missing or mismatched"
        raise ValueError(msg)
    period.require_applicable(context.costing_date)
    verify_baseline_cell(baseline, request.sources.workbook)
    _check_candidate_prices(context, draft, bindings, catalogue, candidate)
    total, delta = draft.calculate_draft()
    baseline_bounds, candidate_bounds, delta_bounds = _resource_envelopes(
        bindings,
        uncertainty,
    )
    if request.catalogue_path.read_bytes() != catalogue_bytes:
        msg = "Catalogue changed during resource comparison"
        raise ValueError(msg)
    identity = {
        "ledger": context.ledger.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "transforms": [t.model_dump(mode="json") for t in context.time_transforms],
        "currency_transforms": [
            t.model_dump(mode="json") for t in context.currency_transforms
        ],
        "uncertainty": uncertainty.model_dump(mode="json"),
        "costing_date": context.costing_date.isoformat(),
        "candidate_price_year": request.candidate_price_year,
        "candidate_tax_basis": request.candidate_tax_basis,
    }
    qualification_sha = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return DerivedResourceDraft(
        baseline,
        total,
        delta,
        request.scenario_id,
        sha256(catalogue_bytes).hexdigest(),
        qualification_sha,
        _digest(draft),
        _digest(bindings),
        baseline_bounds,
        candidate_bounds,
        delta_bounds,
    )
