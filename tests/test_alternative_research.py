# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Research alternatives must remain referenced, explicit and non-costing."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any
lazy from pathlib import Path

import pytest
from openpyxl import Workbook
from pydantic import AnyHttpUrl, ValidationError

from genomics_microcosting.alternative_research import preview_scenario
from genomics_microcosting.parameter_provenance import (
    CostObservation,
    Evidence,
    EvidenceComparison,
)
from genomics_microcosting.parameter_units import (
    CurrencyParameterTransform,
    TimeConversion,
    TimeParameterTransform,
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
    VersionDelta,
    successor,
)
from genomics_microcosting.scenario_comparison import (
    ComparisonSources,
    QualificationContext,
    QualifiedComparisonResult,
    compare_qualified_scenario,
    compare_selected_scenario,
    parameter_set_digest,
    reconcile_version_results,
    verify_external_parameter_values,
    verify_time_unit_sources,
)
from genomics_microcosting.t1_baseline_lineage import BASELINE_SHA256
from genomics_microcosting.uncertainty_provenance import (
    BoundValue,
    EvidenceDeclaration,
    UncertaintyLedger,
    UncertaintyRecord,
)
from tests.checks import require_equal


def test_external_parameter_requires_retained_numeric_support(tmp_path: Path) -> None:
    """Source hashes and a positive judgment alone cannot establish a value."""
    snapshot = tmp_path / "source.txt"
    snapshot.write_text("Kit capacity: 96 samples\nminutes\n", encoding="utf-8")
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    source = SourceRecord(
        source_id="s",
        sha256=digest,
        edition="v1",
        locator="line 1",
        limitations="synthetic",
    )
    parameter = Parameter(
        parameter_id="capacity",
        raw_value="96",
        derived_value="96",
        unit="samples",
        source_sha256=digest,
        source_locator="line 1",
        transformation="identity",
        uncertainty="not measured",
        status="reported",
    )
    qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="Kit capacity: 96 samples",
        dimensional_basis="samples",
        applicability="synthetic",
        qualification="qualified",
        blockers=(),
    )
    ledger = QualificationLedger(
        parameter_set=ParameterSet(
            version_id="v1",
            workbook_sha256="a" * 64,
            parameters=(parameter,),
        ),
        qualifications=(qualification,),
    )
    verify_external_parameter_values(ledger, ("capacity",), {"s": snapshot})
    time_parameter = parameter.model_copy(
        update={"derived_value": "5760", "unit": "s", "status": "derived"},
    )
    time_ledger = QualificationLedger(
        parameter_set=ledger.parameter_set.model_copy(
            update={"parameters": (time_parameter,)},
        ),
        qualifications=(
            qualification.model_copy(update={"parameter": time_parameter}),
        ),
    )
    time_transform = TimeParameterTransform(
        parameter=time_parameter,
        conversion=TimeConversion(
            raw_value=Decimal(96),
            source_unit="min",
            target_unit="s",
            source=source,
            unit_locator="line 2",
        ),
        rounding_policy="exact",
    )
    verify_time_unit_sources(time_ledger, (time_transform,), {"s": snapshot})
    bad_unit = time_transform.model_copy(
        update={
            "conversion": time_transform.conversion.model_copy(
                update={"unit_locator": "line 1"},
            ),
        },
    )
    with pytest.raises(ValueError, match="Time unit source locator"):
        verify_time_unit_sources(time_ledger, (bad_unit,), {"s": snapshot})
    unsupported = qualification.model_copy(
        update={"exact_support": "Kit capacity: 97 samples"},
    )
    changed = ledger.model_copy(update={"qualifications": (unsupported,)})
    with pytest.raises(ValueError, match="source support"):
        verify_external_parameter_values(changed, ("capacity",), {"s": snapshot})
    mismatch = parameter.model_copy(update={"raw_value": "9", "derived_value": "9"})
    changed_qualification = qualification.model_copy(update={"parameter": mismatch})
    changed = QualificationLedger(
        parameter_set=ledger.parameter_set.model_copy(
            update={"parameters": (mismatch,)},
        ),
        qualifications=(changed_qualification,),
    )
    with pytest.raises(ValueError, match="source support"):
        verify_external_parameter_values(changed, ("capacity",), {"s": snapshot})
    wrong_location = source.model_copy(update={"locator": "line 2"})
    wrong_parameter = parameter.model_copy(update={"source_locator": "line 2"})
    wrong_qualification = qualification.model_copy(
        update={"source": wrong_location, "parameter": wrong_parameter},
    )
    wrong_ledger = QualificationLedger(
        parameter_set=ledger.parameter_set.model_copy(
            update={"parameters": (wrong_parameter,)},
        ),
        qualifications=(wrong_qualification,),
    )
    with pytest.raises(ValueError, match="source support"):
        verify_external_parameter_values(wrong_ledger, ("capacity",), {"s": snapshot})
    wrong_source = source.model_copy(update={"locator": "page 1"})
    wrong_qualification = qualification.model_copy(update={"source": wrong_source})
    wrong_ledger = ledger.model_copy(update={"qualifications": (wrong_qualification,)})
    with pytest.raises(ValueError, match="locator"):
        verify_external_parameter_values(wrong_ledger, ("capacity",), {"s": snapshot})
    snapshot.write_text("Kit capacity: 97 samples\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_external_parameter_values(ledger, ("capacity",), {"s": snapshot})


@pytest.fixture
def catalogue() -> dict[str, Any]:
    """Provide a synthetic catalogue independent of private workbook data."""
    return {
        "format_version": "1.0.0",
        "workbook_sha256": "a" * 64,
        "process_source_rows_sha256": "b" * 64,
        "sources": [
            {
                "source_id": "SRC1",
                "title": "Source",
                "url": "https://example.org/source",
                "locator": "page 1",
                "edition": "v1",
                "accessed": "2026-11-06",
                "evidence_class": "primary_study",
                "source_snapshot_sha256": None,
                "limitation": "Research only",
            },
        ],
        "candidates": [
            {
                "candidate_id": "C1",
                "label": "Candidate",
                "source_ids": ["SRC1"],
                "baseline_locations": ["WB18:A12"],
                "process_relationship": "unknown",
                "evidence_state": "research_lead",
                "unknowns": ["local price"],
            },
        ],
        "scenarios": [
            {
                "scenario_id": "S1",
                "candidate_id": "C1",
                "kind": "conditional_substitution",
                "baseline_identity": "a" * 64,
                "limitations": ["research only"],
            },
        ],
    }


def write_catalogue(tmp_path: Path, data: dict[str, Any]) -> Path:
    """Write synthetic catalogue data."""
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_accreditation_evidence_does_not_enable_costing(
    tmp_path: Path,
    catalogue: dict[str, Any],
) -> None:
    """Accept accreditation evidence while keeping research leads non-costing."""
    catalogue["sources"][0]["evidence_class"] = "accreditation_body"
    result = preview_scenario(write_catalogue(tmp_path, catalogue), "S1")
    require_equal(int(result.costing_available), 0)
    require_equal(result.sources[0].evidence_class, "accreditation_body")


def test_preview_requires_selection_and_preserves_inputs(
    tmp_path: Path,
    catalogue: dict[str, Any],
) -> None:
    """Require explicit selection without modifying source inputs."""
    path = write_catalogue(tmp_path, catalogue)
    baseline = tmp_path / "baseline"
    baseline.write_text("unchanged", encoding="utf-8")
    original = path.read_bytes()
    result = preview_scenario(path, "S1")
    require_equal(int(result.costing_available), 0)
    require_equal(result.catalogue_sha256, hashlib.sha256(original).hexdigest())
    require_equal(result.sources[0].source_id, "SRC1")
    require_equal(int(bool(result.blockers)), 1)
    require_equal(path.read_bytes(), original)
    require_equal(baseline.read_text(encoding="utf-8"), "unchanged")
    with pytest.raises(KeyError):
        preview_scenario(path, "missing")
    with pytest.raises(ValidationError):
        result.costing_available = True  # type: ignore[misc]


@pytest.mark.parametrize(
    "change",
    [
        "source_url",
        "empty_locator",
        "missing_source",
        "missing_candidate",
        "duplicate",
        "baseline",
        "changed_process",
        "invented_price",
    ],
)
def test_invalid_provenance_or_scenario_is_rejected(
    tmp_path: Path,
    catalogue: dict[str, Any],
    change: str,
) -> None:
    """Reject missing support and unsafe scenario identities."""
    data = copy.deepcopy(catalogue)
    if change == "source_url":
        del data["sources"][0]["url"]
    elif change == "empty_locator":
        data["sources"][0]["locator"] = ""
    elif change == "missing_source":
        data["candidates"][0]["source_ids"] = ["missing"]
    elif change == "missing_candidate":
        data["scenarios"][0]["candidate_id"] = "missing"
    elif change == "duplicate":
        data["sources"].append(data["sources"][0])
    elif change == "baseline":
        data["scenarios"][0]["baseline_identity"] = "c" * 64
    elif change == "changed_process":
        data["candidates"][0]["process_relationship"] = "changed_process"
    else:
        data["candidates"][0]["unit_price"] = 0
    with pytest.raises(ValidationError):
        preview_scenario(write_catalogue(tmp_path, data), "S1")


def test_real_catalogue_cannot_price_unqualified_research_lead(
    tmp_path: Path,
    catalogue: dict[str, Any],
) -> None:
    """Selecting a research lead must not turn it into an active cost."""
    with pytest.raises(ValueError, match="qualified"):
        compare_selected_scenario(
            write_catalogue(tmp_path, catalogue),
            "S1",
            None,
            ComparisonSources({}, tmp_path / "missing", None),
        )


def test_selected_qualified_counterfactual_uses_evidence_and_workbook(
    tmp_path: Path,
    catalogue: dict[str, Any],
) -> None:
    """A synthetic qualified counterfactual binds source, scenario and workbook."""
    book = Workbook()
    for index in range(1, 17):
        book.create_sheet(f"sheet{index}")
    book.worksheets[16]["N4"] = "minutes"
    book.worksheets[16]["O4"] = "=0.95*100"
    book.worksheets[16]["M5"] = 90
    book.worksheets[16]["N5"] = 100
    book.worksheets[16]["O5"] = 110
    workbook = tmp_path / "baseline.xlsx"
    book.save(workbook)
    bookhash = hashlib.sha256(workbook.read_bytes()).hexdigest()
    snapshot = tmp_path / "source.txt"
    snapshot.write_text("candidate cost 80 AUD per test", encoding="utf-8")
    sourcehash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    catalogue["workbook_sha256"] = bookhash
    catalogue["sources"][0]["source_snapshot_sha256"] = sourcehash
    catalogue["sources"][0]["snapshot_url"] = "https://example.org/source"
    catalogue["candidates"][0]["evidence_state"] = "qualified_for_comparison"
    catalogue["candidates"][0]["process_relationship"] = "changed_process"
    catalogue["candidates"][0]["qualified_baseline_locations"] = ["WB17:N5"]
    catalogue["candidates"][0]["required_baseline_parameter_ids"] = ["input-1"]
    catalogue["candidates"][0]["qualification_summary"] = (
        "Synthetic qualification for contract test"
    )
    catalogue["scenarios"][0]["baseline_identity"] = bookhash
    catalogue["scenarios"][0]["kind"] = "changed_process_counterfactual"
    common = {
        "edition": "1",
        "retrieved": date(2026, 11, 6),
        "evidence_class": "measured",
        "geography": "AU",
        "perspective": "provider",
        "limitations": "synthetic only",
        "effective_date": date(2026, 1, 1),
        "qualification": "qualified",
    }
    base_source = Evidence.model_validate(
        dict(
            source_id="WB",
            source_url=None,
            snapshot_sha256=bookhash,
            locator="WB17:N5",
            exact_support="WB17:N5",
            **common,
        ),
    )
    candidate_source = Evidence.model_validate(
        dict(
            source_id="SRC1",
            source_url=AnyHttpUrl("https://example.org/source"),
            snapshot_sha256=sourcehash,
            locator="line 1",
            exact_support="candidate cost 80 AUD per test",
            **common,
        ),
    )

    def observation(identifier: str, amount: int, source: Evidence) -> CostObservation:
        return CostObservation(
            observation_id=identifier,
            amount=Decimal(amount),
            currency="AUD",
            price_year=2026,
            denominator="test",
            tax_basis="inclusive",
            evidence=source,
        )

    comparison = EvidenceComparison(
        baseline=observation("base", 100, base_source),
        candidate=observation("candidate", 80, candidate_source),
        baseline_workbook_sha256=bookhash,
        scenario_id="S1",
        process_relationship="changed_process_counterfactual",
    )
    path = write_catalogue(tmp_path, catalogue)
    parameter = Parameter(
        parameter_id="input-1",
        raw_value="0",
        derived_value=None,
        unit="AUD/unit",
        source_sha256=bookhash,
        source_locator="WB17:N5",
        transformation="identity",
        uncertainty="synthetic unresolved zero",
        status="unresolved",
    )
    parameters = ParameterSet(
        version_id="test-v1",
        workbook_sha256=bookhash,
        parameters=(parameter,),
    )
    with pytest.raises(ValueError, match="unresolved"):
        compare_selected_scenario(
            path,
            "S1",
            comparison,
            ComparisonSources({"WB": workbook, "SRC1": snapshot}, workbook, parameters),
        )
    resolved = Parameter.model_validate(
        parameter.model_dump()
        | {
            "derived_value": "0",
            "status": "observed",
            "uncertainty": "known zero in fixture",
        },
    )
    parameters = ParameterSet(
        version_id="test-v2",
        workbook_sha256=bookhash,
        parameters=(resolved,),
    )
    sources = ComparisonSources(
        {"WB": workbook, "SRC1": snapshot},
        workbook,
        parameters,
    )
    result = compare_selected_scenario(path, "S1", comparison, sources)
    require_equal(result.delta, Decimal(-20))
    _check_dated_comparison(path, comparison, sources)
    forged_source = resolved.model_copy(update={"source_sha256": "f" * 64})
    forged_parameters = ParameterSet(
        version_id="forged",
        workbook_sha256=bookhash,
        parameters=(forged_source,),
    )
    with pytest.raises(ValueError, match="parameter source snapshot"):
        compare_selected_scenario(
            path,
            "S1",
            comparison,
            ComparisonSources(
                {"WB": workbook, "SRC1": snapshot},
                workbook,
                forged_parameters,
            ),
        )
    wrong = comparison.model_copy(
        update={"baseline": observation("base", 99, base_source)},
    )
    with pytest.raises(ValueError, match=r"[Bb]aseline"):
        compare_selected_scenario(
            path,
            "S1",
            wrong,
            sources,
        )
    wrong_candidate = comparison.model_copy(
        update={"candidate": observation("candidate", 79, candidate_source)},
    )
    with pytest.raises(ValueError, match="source"):
        compare_selected_scenario(
            path,
            "S1",
            wrong_candidate,
            sources,
        )


def test_real_baseline_lineage_cannot_be_omitted(
    tmp_path: Path,
    catalogue: dict[str, Any],
) -> None:
    """A qualified claim cannot omit known zero-valued source dependencies."""
    # Scope rejection must precede any access to the private workbook.
    workbook = tmp_path / "intentionally-absent-baseline.xlsm"
    bookhash = BASELINE_SHA256
    snapshot = tmp_path / "source.txt"
    snapshot.write_text("candidate cost 80 AUD per test", encoding="utf-8")
    sourcehash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    catalogue["workbook_sha256"] = bookhash
    catalogue["sources"][0]["source_snapshot_sha256"] = sourcehash
    catalogue["sources"][0]["snapshot_url"] = "https://example.org/source"
    candidate = catalogue["candidates"][0]
    candidate.update(
        evidence_state="qualified_for_comparison",
        process_relationship="changed_process",
        qualified_baseline_locations=["WB17:N430"],
        required_baseline_parameter_ids=["unrelated"],
        qualification_summary="Synthetic claim for a regression test",
    )
    catalogue["scenarios"][0].update(
        baseline_identity=bookhash,
        kind="changed_process_counterfactual",
    )
    common = {
        "edition": "1",
        "retrieved": date(2026, 11, 6),
        "evidence_class": "measured",
        "geography": "AU",
        "perspective": "provider",
        "limitations": "synthetic",
        "effective_date": date(2023, 1, 1),
        "qualification": "qualified",
    }
    baseline_source = Evidence.model_validate(
        {
            **common,
            "source_id": "WB",
            "source_url": None,
            "snapshot_sha256": bookhash,
            "locator": "WB17:N430",
            "exact_support": "WB17:N430",
        },
    )
    candidate_source = Evidence.model_validate(
        {
            **common,
            "source_id": "SRC1",
            "source_url": "https://example.org/source",
            "snapshot_sha256": sourcehash,
            "locator": "line 1",
            "exact_support": "candidate cost 80 AUD per test",
        },
    )
    base = CostObservation(
        observation_id="baseline",
        amount=Decimal("145.34173233368602"),
        currency="AUD",
        price_year=2023,
        denominator="test",
        tax_basis="inclusive",
        evidence=baseline_source,
    )
    alternative = CostObservation(
        observation_id="alternative",
        amount=Decimal(80),
        currency="AUD",
        price_year=2023,
        denominator="test",
        tax_basis="inclusive",
        evidence=candidate_source,
    )
    comparison = EvidenceComparison(
        baseline=base,
        candidate=alternative,
        baseline_workbook_sha256=bookhash,
        scenario_id="S1",
        process_relationship="changed_process_counterfactual",
    )
    with pytest.raises(ValueError, match="omits known unresolved inputs"):
        compare_selected_scenario(
            write_catalogue(tmp_path, catalogue),
            "S1",
            comparison,
            ComparisonSources({"WB": workbook, "SRC1": snapshot}, workbook, None),
        )


def _check_dated_comparison(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
) -> None:
    """Exercise source-bound temporal acceptance and rejection end to end."""
    parameters = sources.baseline_parameters
    if parameters is None:
        raise AssertionError
    resolved = Parameter.model_validate(
        parameters.parameters[0].model_dump()
        | {"raw_value": "100", "derived_value": "100"},
    )
    parameters = ParameterSet(
        version_id="dated-fixture",
        workbook_sha256=parameters.workbook_sha256,
        parameters=(resolved,),
    )
    sources = ComparisonSources(sources.snapshots, sources.workbook, parameters)
    source_records = tuple(
        SourceRecord(
            source_id=e.source_id,
            sha256=e.snapshot_sha256,
            edition=e.edition,
            locator=e.locator,
            limitations=e.limitations,
        )
        for e in (comparison.baseline.evidence, comparison.candidate.evidence)
    )
    ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(
            ParameterQualification(
                parameter=resolved,
                source=source_records[0],
                exact_support="Synthetic known zero",
                dimensional_basis="synthetic unit",
                applicability="synthetic only",
                qualification="qualified",
                blockers=(),
            ),
        ),
    )
    periods = tuple(
        SourceValidity(
            source=source,
            retrieved=date(2026, 11, 6),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
            date_basis="synthetic period",
        )
        for source in source_records
    )
    context = _qualification_context(ledger, periods, date(2026, 6, 1))
    _check_formula_number_context(path, comparison, sources, context)
    _check_workbook_text_context(path, comparison, sources, context)
    _check_uncertainty_context(path, comparison, sources, context)
    _check_converted_parameter(path, comparison, sources, context)
    _check_currency_parameter(path, comparison, sources, context)
    _check_manifest_blocks(path, comparison, sources, context)
    for update, message in [
        ({"raw_value": "99"}, "raw value differs"),
        ({"derived_value": "99"}, "transformation missing"),
    ]:
        forged = resolved.model_copy(update=update)
        forged_set = parameters.model_copy(update={"parameters": (forged,)})
        forged_ledger = QualificationLedger(
            parameter_set=forged_set,
            qualifications=(
                ledger.qualifications[0].model_copy(update={"parameter": forged}),
            ),
        )
        with pytest.raises(ValueError, match=message):
            compare_qualified_scenario(
                path,
                "S1",
                comparison,
                ComparisonSources(sources.snapshots, sources.workbook, forged_set),
                _qualification_context(forged_ledger, periods, date(2026, 6, 1)),
            )

    with pytest.raises(KeyError, match="missing-scenario"):
        compare_qualified_scenario(
            path,
            "missing-scenario",
            comparison,
            sources,
            context,
        )

    require_equal(
        compare_qualified_scenario(path, "S1", comparison, sources, context).delta,
        Decimal(-20),
    )
    with pytest.raises(ValueError, match="does not cover"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            _qualification_context(ledger, periods, date(2027, 1, 1)),
        )
    with pytest.raises(ValueError, match="Observation source validity"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            _qualification_context(ledger, periods[:1], date(2026, 6, 1)),
        )


def _check_uncertainty_context(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Bind selected uncertainty to the same dated input scope."""
    q = context.ledger.qualifications[0]
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic only",
        source=q.source,
    )
    record = UncertaintyRecord(
        measure_id=q.parameter.parameter_id,
        unit=q.parameter.unit,
        source=q.source,
        lower=BoundValue(value=Decimal(90), locator="WB17:M5", absence_reason=None),
        midpoint=BoundValue(value=Decimal(100), locator="WB17:N5", absence_reason=None),
        upper=BoundValue(value=Decimal(110), locator="WB17:O5", absence_reason=None),
        interpretation="reported_range",
        interpretation_evidence=declared,
        distribution=declared,
        dependence=declared,
    )
    uncertainty = UncertaintyLedger(
        parameter_set=context.ledger.parameter_set,
        records=(record,),
    )
    absent = compare_qualified_scenario(path, "S1", comparison, sources, context)
    require_equal(absent.uncertainty_status, "not_assessed")
    result = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        sources,
        replace(context, uncertainty=uncertainty),
    )
    require_equal(result.uncertainty_status, "bounds_and_source_bytes_checked")
    with pytest.raises(ValueError, match="uncertainty status"):
        type(result).model_validate(result.model_dump() | {"uncertainty_sha256": None})
    next_set = successor(
        context.ledger.parameter_set,
        (),
        version_id="uncertainty-next",
    )
    transition = VersionDelta(
        baseline=context.ledger.parameter_set,
        successor=next_set,
        reason="synthetic carry-forward",
    )
    next_result = result.model_copy(
        update={
            "parameter_version_id": next_set.version_id,
            "parameter_set_sha256": parameter_set_digest(next_set),
        },
    )
    with pytest.raises(ValueError, match="Reconciliation of declared uncertainty"):
        reconcile_version_results(result, next_result, transition)
    forged = uncertainty.model_copy(
        update={
            "records": (
                record.model_copy(
                    update={
                        "upper": record.upper.model_copy(
                            update={"value": Decimal(111)},
                        ),
                    },
                ),
            ),
        },
    )
    with pytest.raises(ValueError, match="bound source"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            replace(context, uncertainty=forged),
        )
    other_version = uncertainty.model_copy(
        update={
            "parameter_set": uncertainty.parameter_set.model_copy(
                update={"version_id": "different-version"},
            ),
        },
    )
    with pytest.raises(ValueError, match="Uncertainty parameter version"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            replace(context, uncertainty=other_version),
        )
    other_source = q.source.model_copy(update={"source_id": "uncertainty-only"})
    other_declaration = declared.model_copy(update={"source": other_source})
    other_record = record.model_copy(
        update={
            "source": other_source,
            "interpretation_evidence": other_declaration,
            "distribution": other_declaration,
            "dependence": other_declaration,
        },
    )
    other_ledger = uncertainty.model_copy(update={"records": (other_record,)})
    extra_snapshots = ComparisonSources(
        sources.snapshots | {"uncertainty-only": sources.workbook},
        sources.workbook,
        sources.baseline_parameters,
    )
    with pytest.raises(ValueError, match="Uncertainty source validity"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            extra_snapshots,
            replace(context, uncertainty=other_ledger),
        )


def _check_formula_number_context(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Treat a formula number as an explicit token, not a cached result."""
    source = SourceRecord(
        source_id="WB-formula",
        sha256=context.ledger.parameter_set.workbook_sha256,
        edition="1",
        locator="WB17:O4",
        limitations="synthetic formula",
    )
    parameter = Parameter(
        parameter_id="formula-factor",
        raw_value="0.95",
        derived_value="0.95",
        unit="factor",
        source_sha256=source.sha256,
        source_locator=source.locator,
        transformation="identity",
        uncertainty="synthetic",
        status="observed",
    )
    qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="=0.95*100",
        dimensional_basis="factor",
        applicability="synthetic only",
        qualification="qualified",
        blockers=(),
    )
    parameters = context.ledger.parameter_set.model_copy(
        update={"parameters": (*context.ledger.parameter_set.parameters, parameter)},
    )
    ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(*context.ledger.qualifications, qualification),
    )
    periods = (
        *context.validity,
        SourceValidity(
            source=source,
            retrieved=date(2026, 11, 6),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
            date_basis="synthetic period",
        ),
    )
    selected = _qualification_context(ledger, periods, context.costing_date)
    manifest = selected.manifest
    if manifest is None:
        raise AssertionError
    formula_item = manifest.inputs[-1].model_copy(
        update={"value_kind": "workbook_formula_number", "formula_token_index": 1},
    )
    selected = replace(
        selected,
        manifest=manifest.model_copy(
            update={"inputs": (*manifest.inputs[:-1], formula_item)},
        ),
    )
    selected_sources = ComparisonSources(
        sources.snapshots | {source.source_id: sources.workbook},
        sources.workbook,
        parameters,
    )
    result = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        selected_sources,
        selected,
    )
    require_equal(result.model_version, "qualified-comparison-v7")
    require_equal(result.delta, Decimal(-20))
    legacy = QualifiedComparisonResult.model_validate(
        result.model_dump() | {"model_version": "qualified-comparison-v6"},
    )
    require_equal(legacy.model_version, "qualified-comparison-v6")
    for index in (2, 3, 9):
        wrong = formula_item.model_copy(update={"formula_token_index": index})
        with pytest.raises(ValueError, match="formula-number"):
            compare_qualified_scenario(
                path,
                "S1",
                comparison,
                selected_sources,
                replace(
                    selected,
                    manifest=manifest.model_copy(
                        update={"inputs": (*manifest.inputs[:-1], wrong)},
                    ),
                ),
            )
    with pytest.raises(ValueError, match="positive token index"):
        InputRequirement.model_validate(
            formula_item.model_dump() | {"formula_token_index": None},
        )
    with pytest.raises(ValueError, match="positive token index"):
        InputRequirement.model_validate(
            formula_item.model_dump() | {"value_kind": "numeric"},
        )
    for invalid in (0, True):
        with pytest.raises(ValueError, match=r"greater than or equal|valid integer"):
            InputRequirement.model_validate(
                formula_item.model_dump() | {"formula_token_index": invalid},
            )
    wrong_support = qualification.model_copy(update={"exact_support": "=0.95*101"})
    wrong_ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(*ledger.qualifications[:-1], wrong_support),
    )
    wrong_item = formula_item.model_copy(update={"qualification": wrong_support})
    with pytest.raises(ValueError, match="formula-number evidence differs"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            replace(
                selected,
                ledger=wrong_ledger,
                manifest=manifest.model_copy(
                    update={"inputs": (*manifest.inputs[:-1], wrong_item)},
                ),
            ),
        )


def _check_workbook_text_context(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Source text stays required and source-checked without becoming numeric."""
    source = SourceRecord(
        source_id="WB-text",
        sha256=context.ledger.parameter_set.workbook_sha256,
        edition="1",
        locator="WB17:N4",
        limitations="synthetic source text",
    )
    parameter = Parameter(
        parameter_id="source-text",
        raw_value="minutes",
        derived_value="minutes",
        unit="source text",
        source_sha256=source.sha256,
        source_locator=source.locator,
        transformation="identity",
        uncertainty="not a numeric measure",
        status="observed",
    )
    text_qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="minutes",
        dimensional_basis="source text",
        applicability="synthetic only",
        qualification="qualified",
        blockers=(),
    )
    parameters = context.ledger.parameter_set.model_copy(
        update={"parameters": (*context.ledger.parameter_set.parameters, parameter)},
    )
    ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(*context.ledger.qualifications, text_qualification),
    )
    periods = (
        *context.validity,
        SourceValidity(
            source=source,
            retrieved=date(2026, 11, 6),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
            date_basis="synthetic period",
        ),
    )
    selected = _qualification_context(ledger, periods, context.costing_date)
    manifest = selected.manifest
    if manifest is None:
        raise AssertionError
    text_item = manifest.inputs[-1].model_copy(update={"value_kind": "workbook_text"})
    selected = replace(
        selected,
        manifest=manifest.model_copy(
            update={"inputs": (*manifest.inputs[:-1], text_item)},
        ),
    )
    selected_sources = ComparisonSources(
        sources.snapshots | {source.source_id: sources.workbook},
        sources.workbook,
        parameters,
    )
    result = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        selected_sources,
        selected,
    )
    require_equal(result.model_version, "qualified-comparison-v7")
    require_equal(result.delta, Decimal(-20))
    legacy = QualifiedComparisonResult.model_validate(
        result.model_dump() | {"model_version": "qualified-comparison-v5"},
    )
    require_equal(legacy.model_version, "qualified-comparison-v5")
    numeric_source = context.ledger.qualifications[0].source
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic",
        source=numeric_source,
    )
    numeric_uncertainty = UncertaintyRecord(
        measure_id=context.ledger.qualifications[0].parameter.parameter_id,
        unit=context.ledger.qualifications[0].parameter.unit,
        source=numeric_source,
        lower=BoundValue(value=Decimal(90), locator="WB17:M5", absence_reason=None),
        midpoint=BoundValue(value=Decimal(100), locator="WB17:N5", absence_reason=None),
        upper=BoundValue(value=Decimal(110), locator="WB17:O5", absence_reason=None),
        interpretation="reported_range",
        interpretation_evidence=declared,
        distribution=declared,
        dependence=declared,
    )
    missing = BoundValue(value=None, locator=source.locator, absence_reason="text")
    unresolved = EvidenceDeclaration(state="unresolved", description=None, source=None)
    text_uncertainty = UncertaintyRecord(
        measure_id=parameter.parameter_id,
        unit=parameter.unit,
        source=source,
        lower=missing,
        midpoint=missing,
        upper=missing,
        interpretation="unresolved",
        interpretation_evidence=unresolved,
        distribution=unresolved,
        dependence=unresolved,
    )
    uncertainty = UncertaintyLedger(
        parameter_set=parameters,
        records=(numeric_uncertainty, text_uncertainty),
    )
    checked = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        selected_sources,
        replace(selected, uncertainty=uncertainty),
    )
    require_equal(checked.uncertainty_status, "bounds_and_source_bytes_checked")
    with pytest.raises(ValueError, match="source snapshot missing"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            ComparisonSources(sources.snapshots, sources.workbook, parameters),
            selected,
        )
    baseline_as_text = manifest.inputs[0].model_copy(
        update={"value_kind": "workbook_text"},
    )
    with pytest.raises(ValueError, match="manifest identity"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            replace(
                selected,
                manifest=manifest.model_copy(
                    update={"inputs": (baseline_as_text, manifest.inputs[-1])},
                ),
            ),
        )
    incorrect_kind = replace(selected, manifest=manifest)
    with pytest.raises(TypeError, match="cached value is not numeric"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            incorrect_kind,
        )
    wrong_parameter = parameter.model_copy(
        update={"raw_value": "hours", "derived_value": "hours"},
    )
    wrong_qualification = text_qualification.model_copy(
        update={"parameter": wrong_parameter, "exact_support": "hours"},
    )
    wrong_parameters = parameters.model_copy(
        update={"parameters": (*parameters.parameters[:-1], wrong_parameter)},
    )
    wrong_ledger = QualificationLedger(
        parameter_set=wrong_parameters,
        qualifications=(*ledger.qualifications[:-1], wrong_qualification),
    )
    wrong_manifest = selected.manifest
    if wrong_manifest is None:
        raise AssertionError
    wrong_item = text_item.model_copy(
        update={"parameter": wrong_parameter, "qualification": wrong_qualification},
    )
    with pytest.raises(ValueError, match="text evidence differs"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            ComparisonSources(
                selected_sources.snapshots,
                sources.workbook,
                wrong_parameters,
            ),
            replace(
                selected,
                ledger=wrong_ledger,
                manifest=wrong_manifest.model_copy(
                    update={"inputs": (*wrong_manifest.inputs[:-1], wrong_item)},
                ),
            ),
        )


def _check_currency_parameter(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Require the separate FX rate through the complete dated comparison path."""
    rate_file = path.parent / "synthetic-fx.txt"
    rate_file.write_text("FX rate: 1.5 AUD/USD\n", encoding="utf-8")
    rate_source = SourceRecord(
        source_id="FX",
        sha256=hashlib.sha256(rate_file.read_bytes()).hexdigest(),
        edition="synthetic",
        locator="line 1",
        limitations="synthetic",
    )
    rate = Parameter(
        parameter_id="fx",
        raw_value="1.5",
        derived_value="1.5",
        unit="AUD/USD",
        source_sha256=rate_source.sha256,
        source_locator="line 1",
        transformation="identity",
        uncertainty="synthetic",
        status="reported",
    )
    original = context.ledger.qualifications[0]
    price = Parameter.model_validate(
        original.parameter.model_dump()
        | {
            "derived_value": "150",
            "unit": "AUD/sample",
            "status": "derived",
            "transformation": "synthetic FX",
        },
    )
    parameter_set = context.ledger.parameter_set.model_copy(
        update={"parameters": (price, rate)},
    )
    rate_qualification = ParameterQualification(
        parameter=rate,
        source=rate_source,
        exact_support="FX rate: 1.5 AUD/USD",
        dimensional_basis="AUD/USD",
        applicability="synthetic",
        qualification="qualified",
        blockers=(),
    )
    ledger = QualificationLedger(
        parameter_set=parameter_set,
        qualifications=(
            original.model_copy(update={"parameter": price}),
            rate_qualification,
        ),
    )
    transform = CurrencyParameterTransform(
        parameter=price,
        rate_parameter=rate,
        source_currency="USD",
        target_currency="AUD",
        denominator="sample",
        price_year=2026,
        tax_basis="exclusive",
        rounding_policy="exact",
    )
    validity = (
        *context.validity,
        SourceValidity(
            source=rate_source,
            retrieved=date(2026, 11, 6),
            effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31),
            date_basis="synthetic",
        ),
    )
    selected = _qualification_context(
        ledger,
        validity,
        context.costing_date,
        currency_transforms=(transform,),
    )
    selected_sources = ComparisonSources(
        sources.snapshots | {"FX": rate_file},
        sources.workbook,
        parameter_set,
    )
    result = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        selected_sources,
        selected,
    )
    require_equal(result.model_version, "qualified-comparison-v7")
    with pytest.raises(ValueError, match="tax basis is unresolved"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            replace(
                selected,
                currency_transforms=(
                    transform.model_copy(update={"tax_basis": "unknown"}),
                ),
            ),
        )
    price_only = parameter_set.model_copy(update={"parameters": (price,)})
    incomplete = QualificationLedger(
        parameter_set=price_only,
        qualifications=(original.model_copy(update={"parameter": price}),),
    )
    with pytest.raises(ValueError, match="rate must be a required parameter"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            ComparisonSources(sources.snapshots, sources.workbook, price_only),
            _qualification_context(
                incomplete,
                context.validity,
                context.costing_date,
                currency_transforms=(transform,),
            ),
        )
    with pytest.raises(ValueError, match="transformation missing"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            _qualification_context(ledger, validity, context.costing_date),
        )
    with pytest.raises(ValueError, match="validity missing"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            _qualification_context(
                ledger,
                context.validity,
                context.costing_date,
                currency_transforms=(transform,),
            ),
        )


def _check_converted_parameter(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Exercise exact conversion binding through the dated comparison API."""
    original = context.ledger.qualifications[0]
    conversion = TimeConversion(
        raw_value=Decimal(100),
        source_unit="min",
        target_unit="s",
        source=original.source,
        unit_locator="WB17:N4",
    )
    parameter = Parameter.model_validate(
        original.parameter.model_dump()
        | {
            "derived_value": "6000",
            "unit": "s",
            "status": "derived",
            "transformation": "minutes to seconds; synthetic fixture",
        },
    )
    parameter_set = context.ledger.parameter_set.model_copy(
        update={"parameters": (parameter,)},
    )
    ledger = QualificationLedger(
        parameter_set=parameter_set,
        qualifications=(original.model_copy(update={"parameter": parameter}),),
    )
    transform = TimeParameterTransform(
        parameter=parameter,
        conversion=conversion,
        rounding_policy="exact",
    )
    selected_sources = ComparisonSources(
        sources.snapshots,
        sources.workbook,
        parameter_set,
    )
    selected = _qualification_context(
        ledger,
        context.validity,
        context.costing_date,
        (transform,),
    )
    result = compare_qualified_scenario(
        path,
        "S1",
        comparison,
        selected_sources,
        selected,
    )
    for locator in ("WB17:M5", "WB17:Z99", "unverified unit"):
        bad = transform.model_copy(
            update={
                "conversion": conversion.model_copy(update={"unit_locator": locator}),
            },
        )
        with pytest.raises(ValueError, match="Time unit source"):
            compare_qualified_scenario(
                path,
                "S1",
                comparison,
                selected_sources,
                replace(selected, time_transforms=(bad,)),
            )
    altered_source = conversion.source.model_copy(update={"source_id": "other"})
    bad_source = transform.model_copy(
        update={"conversion": conversion.model_copy(update={"source": altered_source})},
    )
    with pytest.raises(ValueError, match="differs from parameter qualification"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            replace(selected, time_transforms=(bad_source,)),
        )
    require_equal(result.delta, Decimal(-20))
    next_parameters = successor(parameter_set, (), version_id="next-fixture-version")
    transition = VersionDelta(
        baseline=parameter_set,
        successor=next_parameters,
        reason="Synthetic unchanged carry-forward",
    )
    later = result.model_copy(
        update={
            "parameter_version_id": next_parameters.version_id,
            "parameter_set_sha256": parameter_set_digest(next_parameters),
        },
    )
    reconciled = reconcile_version_results(result, later, transition)
    require_equal(reconciled.result_delta, Decimal(0))
    unrelated = parameter.model_copy(update={"derived_value": "5999"})
    forged_transition = VersionDelta(
        baseline=parameter_set.model_copy(update={"parameters": (unrelated,)}),
        successor=next_parameters.model_copy(update={"parameters": (unrelated,)}),
        reason="Different parameter records with the same version labels",
    )
    with pytest.raises(ValueError, match="parameter content"):
        reconcile_version_results(result, later, forged_transition)
    historical = result.model_copy(
        update={
            "model_version": "qualified-comparison-v3",
            "parameter_set_sha256": None,
            "uncertainty_status": None,
            "uncertainty_sha256": None,
        },
    )
    with pytest.raises(ValueError, match="parameter content"):
        reconcile_version_results(historical, later, transition)
    with pytest.raises(ValueError, match="identities"):
        reconcile_version_results(result, result, transition)
    with pytest.raises(ValueError, match="incompatible"):
        reconcile_version_results(
            result,
            later.model_copy(update={"costing_date": date(2027, 1, 1)}),
            transition,
        )
    with pytest.raises(ValueError, match="incompatible"):
        reconcile_version_results(
            result,
            later.model_copy(update={"catalogue_sha256": "f" * 64}),
            transition,
        )
    if selected.manifest is None:
        raise AssertionError
    require_equal(result.manifest_version_id, selected.manifest.version_id)
    with pytest.raises(ValueError, match="incompatible"):
        reconcile_version_results(
            result,
            later.model_copy(update={"input_scope_sha256": "f" * 64}),
            transition,
        )
    require_equal(result.parameter_version_id, parameter_set.version_id)
    require_equal(result.costing_date, context.costing_date)
    require_equal(
        result.catalogue_sha256,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    require_equal(len(result.qualification_sha256), 64)
    with pytest.raises(ValueError, match="transformation missing"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            selected_sources,
            _qualification_context(ledger, context.validity, context.costing_date),
        )


def _qualification_context(
    ledger: QualificationLedger,
    validity: tuple[SourceValidity, ...],
    costing_date: date,
    transforms: tuple[TimeParameterTransform, ...] = (),
    currency_transforms: tuple[CurrencyParameterTransform, ...] = (),
) -> QualificationContext:
    """Bind synthetic required inputs without leaving coverage implicit."""
    items = tuple(
        InputRequirement(
            input_id=q.parameter.parameter_id,
            resource_id="synthetic-resource",
            role="synthetic input",
            parameter=q.parameter,
            qualification=q,
            blockers=(),
        )
        for q in ledger.qualifications
    )
    manifest = InputManifest(
        version_id="synthetic-manifest-v1",
        candidate_id="C1",
        workbook_sha256=ledger.parameter_set.workbook_sha256,
        scope="synthetic fixture",
        required_ids=tuple(i.input_id for i in items),
        inputs=items,
    )
    return QualificationContext(
        ledger,
        validity,
        costing_date,
        transforms,
        manifest,
        currency_transforms,
    )


def _check_manifest_blocks(
    path: Path,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    context: QualificationContext,
) -> None:
    """Reject absent manifests and unresolved requirements before costing."""
    with pytest.raises(ValueError, match="manifest is missing"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            QualificationContext(
                context.ledger,
                context.validity,
                context.costing_date,
            ),
        )
    manifest = context.manifest
    if manifest is None:
        raise AssertionError
    blocked = manifest.inputs[0].model_copy(
        update={"blockers": ("Acquisition cost unresolved",)},
    )
    changed = manifest.model_copy(update={"inputs": (blocked,)})
    with pytest.raises(ValueError, match="blocked"):
        compare_qualified_scenario(
            path,
            "S1",
            comparison,
            sources,
            QualificationContext(
                context.ledger,
                context.validity,
                context.costing_date,
                (),
                changed,
            ),
        )
