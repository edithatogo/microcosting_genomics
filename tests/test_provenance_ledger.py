# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify immutable parameter version transitions."""

from hashlib import sha256
lazy from datetime import date
lazy from pathlib import Path

import pytest
from pydantic import ValidationError

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
    export_parameter_set,
    require_resolved_parameters,
    successor,
    verify_parameter_sources,
    verify_qualified_period,
)
from tests import checks


def test_successor_preserves_baseline_and_missing_parameters() -> None:
    """Changes preserve the original and carry unresolved records forward."""
    observed = Parameter(
        parameter_id="a",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="identity",
        uncertainty="unknown",
        status="observed",
    )
    missing = Parameter(
        parameter_id="b",
        raw_value=None,
        derived_value=None,
        unit="h",
        source_sha256="a" * 64,
        source_locator="A2",
        transformation="none",
        uncertainty="unknown",
        status="unresolved",
    )
    base = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(observed, missing),
    )
    updated = observed.model_copy(update={"derived_value": "3"})
    result = successor(base, (updated,), version_id="v2")
    checks.require_equal(base.parameters[0].derived_value, "2")
    checks.require_equal(result.parameters[1].status, "unresolved")
    with pytest.raises(ValueError, match="distinct"):
        successor(base, (updated,), version_id="v1")
    with pytest.raises(ValidationError, match="Unresolved"):
        Parameter.model_validate(missing.model_dump() | {"derived_value": "0"})


def test_required_scope_rejects_missing_unresolved_and_wrong_workbook() -> None:
    """Do not turn a source-recorded zero of uncertain meaning into a cost."""
    value = Parameter(
        parameter_id="cost:WB30:E47",
        raw_value="0",
        derived_value=None,
        unit="AUD/uL",
        source_sha256="a" * 64,
        source_locator="WB30:E47",
        transformation="unresolved economic interpretation",
        uncertainty="free, bundled or unpriced",
        status="unresolved",
    )
    parameters = ParameterSet(
        version_id="baseline-v1",
        workbook_sha256="a" * 64,
        parameters=(value,),
    )
    for scope, digest, message in (
        (("cost:WB30:E47",), "a" * 64, "unresolved"),
        (("missing",), "a" * 64, "missing"),
        (("cost:WB30:E47",), "b" * 64, "identity"),
        ((), "a" * 64, "scope"),
        (("cost:WB30:E47", "cost:WB30:E47"), "a" * 64, "scope"),
    ):
        with pytest.raises(ValueError, match=message):
            require_resolved_parameters(parameters, scope, digest)


def test_delta_rejects_membership_loss_and_retains_unresolved_change() -> None:
    """Version comparison cannot silently drop unknown baseline parameters."""
    unknown = Parameter(
        parameter_id="missing",
        raw_value=None,
        derived_value=None,
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="none",
        uncertainty="unknown",
        status="unresolved",
    )
    base = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(unknown,),
    )
    empty = ParameterSet(version_id="v2", workbook_sha256="a" * 64, parameters=())
    with pytest.raises(ValueError, match="membership"):
        VersionDelta(baseline=base, successor=empty, reason="invalid omission")
    updated = successor(
        base,
        (unknown.model_copy(update={"uncertainty": "bounded later"}),),
        version_id="v2",
    )
    delta = VersionDelta(
        baseline=base,
        successor=updated,
        reason="Document evidence gap",
    )
    checks.require_equal(len(delta.changes()), 1)
    checks.require_equal(delta.changes()[0].after.status, "unresolved")
    checks.require_equal(base.parameters[0].uncertainty, "unknown")


def test_version_delta_revalidates_copied_nested_parameters() -> None:
    """Unvalidated model copies cannot inject active unresolved values."""
    value = Parameter(
        parameter_id="a",
        raw_value=None,
        derived_value=None,
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="none",
        uncertainty="unknown",
        status="unresolved",
    )
    base = ParameterSet(version_id="v1", workbook_sha256="a" * 64, parameters=(value,))
    invalid = value.model_copy(update={"derived_value": "42"})
    forged = base.model_copy(update={"version_id": "v2", "parameters": (invalid,)})
    with pytest.raises(ValueError, match="Unresolved"):
        VersionDelta(baseline=base, successor=forged, reason="Invalid copied value")


def test_delta_read_methods_reject_copied_invalid_transition() -> None:
    """No read operation accepts a copy that bypassed transition validation."""
    value = Parameter(
        parameter_id="unknown",
        raw_value=None,
        derived_value=None,
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="none",
        uncertainty="unknown",
        status="unresolved",
    )
    base = ParameterSet(version_id="v1", workbook_sha256="a" * 64, parameters=(value,))
    target = successor(base, (), version_id="v2")
    valid = VersionDelta(baseline=base, successor=target, reason="carry forward")
    invalid = valid.model_copy(
        update={"successor": target.model_copy(update={"version_id": "v1"})},
    )
    for read in (invalid.changes, invalid.unchanged_ids, lambda: invalid.select("v1")):
        with pytest.raises(ValueError, match="versions must differ"):
            read()


def test_explicit_selection_rolls_back_without_losing_unknowns() -> None:
    """Rollback restores source-bound records and rejects unknown version names."""
    missing = Parameter(
        parameter_id="unknown",
        raw_value=None,
        derived_value=None,
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="none",
        uncertainty="unobserved",
        status="unresolved",
    )
    base = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(missing,),
    )
    updated = successor(base, (), version_id="v2")
    transition = VersionDelta(baseline=base, successor=updated, reason="Carry forward")
    checks.require_equal(transition.unchanged_ids(), ("unknown",))
    checks.require_equal(transition.changes(), ())
    checks.require_equal(transition.select("v1"), base)
    checks.require_equal(transition.select("v2"), updated)
    with pytest.raises(ValueError, match="absent"):
        transition.select("latest")
    with pytest.raises(ValueError, match="unresolved"):
        require_resolved_parameters(transition.select("v1"), ("unknown",), "a" * 64)


def test_source_manifest_requires_retained_exact_bytes(tmp_path: Path) -> None:
    """Source identity claims alone cannot qualify parameter provenance."""
    path = tmp_path / "source.txt"
    path.write_bytes(b"retained evidence")
    digest = sha256(path.read_bytes()).hexdigest()
    source = SourceRecord(
        source_id="s1",
        sha256=digest,
        edition="v1",
        locator="A1",
        limitations="synthetic",
    )
    parameter = Parameter(
        parameter_id="a",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256=digest,
        source_locator="A1",
        transformation="identity",
        uncertainty="unknown",
        status="observed",
    )
    parameters = ParameterSet(
        version_id="v1",
        workbook_sha256=digest,
        parameters=(parameter,),
    )
    verify_parameter_sources(parameters, (source,), {"s1": path})
    with pytest.raises(ValueError, match="missing"):
        verify_parameter_sources(parameters, (source,), {})
    with pytest.raises(ValueError, match="absent"):
        verify_parameter_sources(parameters, (), {})
    path.write_bytes(b"altered evidence")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_parameter_sources(parameters, (source,), {"s1": path})


def test_qualification_cannot_promote_unknown_zero() -> None:
    """Recorded zero with unknown economic meaning stays blocked explicitly."""
    parameter = Parameter(
        parameter_id="water",
        raw_value="0",
        derived_value=None,
        unit="AUD/uL",
        source_sha256="a" * 64,
        source_locator="WB30:E48",
        transformation="none",
        uncertainty="free or unpriced",
        status="unresolved",
    )
    source = SourceRecord(
        source_id="workbook",
        sha256="a" * 64,
        edition="2023",
        locator="WB30:E48",
        limitations="valuation unknown",
    )
    with pytest.raises(ValueError, match="Qualified"):
        ParameterQualification(
            parameter=parameter,
            source=source,
            exact_support="Source records zero",
            dimensional_basis="AUD/uL",
            applicability="historical model",
            qualification="qualified",
            blockers=(),
        )
    result = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="Source records zero",
        dimensional_basis="AUD/uL",
        applicability="historical model",
        qualification="unresolved",
        blockers=("Economic meaning absent",),
    )
    checks.require_equal(result.parameter.derived_value, None)


def test_qualification_rejects_mismatched_source_locator() -> None:
    """A genuine source hash cannot qualify support at a different location."""
    parameter = Parameter(
        parameter_id="located",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256="a" * 64,
        source_locator="WB01:A1",
        transformation="identity",
        uncertainty="unmeasured",
        status="observed",
    )
    source = SourceRecord(
        source_id="workbook",
        sha256="a" * 64,
        edition="v1",
        locator="WB01:B1",
        limitations="synthetic",
    )
    values = {
        "parameter": parameter,
        "source": source,
        "exact_support": "synthetic support",
        "dimensional_basis": "h",
        "applicability": "synthetic",
        "qualification": "unresolved",
        "blockers": ("Locator disagreement",),
    }
    unresolved = ParameterQualification.model_validate(values)
    with pytest.raises(ValueError, match="locators differ"):
        ParameterQualification.model_validate(
            unresolved.model_dump() | {"qualification": "qualified", "blockers": ()},
        )


def test_qualification_ledger_rejects_omission_and_stale_values() -> None:
    """Coverage must bind judgments to the exact selected parameter record."""
    parameter = Parameter(
        parameter_id="a",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="identity",
        uncertainty="unmeasured",
        status="observed",
    )
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="v1",
        locator="A1",
        limitations="synthetic",
    )
    qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="A1 contains 2",
        dimensional_basis="hours",
        applicability="synthetic",
        qualification="qualified",
        blockers=(),
    )
    parameters = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(parameter,),
    )
    with pytest.raises(ValueError, match="coverage"):
        QualificationLedger(parameter_set=parameters, qualifications=())
    stale = qualification.model_copy(
        update={"parameter": parameter.model_copy(update={"derived_value": "3"})},
    )
    with pytest.raises(ValueError, match="different parameter version"):
        QualificationLedger(parameter_set=parameters, qualifications=(stale,))
    ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(qualification,),
    )
    ledger.require_qualified(("a",))
    forged = ledger.model_copy(update={"qualifications": (stale,)})
    with pytest.raises(ValueError, match="different parameter version"):
        forged.require_qualified(("a",))
    with pytest.raises(ValueError, match="snapshot missing"):
        ledger.verify_required(("a",), {})
    with pytest.raises(ValueError, match="missing"):
        ledger.require_qualified(("other",))


def test_source_dates_reject_unknown_expired_and_inverted_periods() -> None:
    """Snapshot retrieval cannot establish economic validity dates."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="2023",
        locator="A1",
        limitations="synthetic",
    )
    unknown = SourceValidity(
        source=source,
        retrieved=date(2026, 11, 6),
        effective_from=None,
        effective_until=None,
        date_basis="not recorded",
    )
    with pytest.raises(ValueError, match="unresolved"):
        unknown.require_applicable(date(2023, 1, 1))
    with pytest.raises(ValueError, match="inverted"):
        SourceValidity(
            source=source,
            retrieved=date(2026, 11, 6),
            effective_from=date(2024, 1, 1),
            effective_until=date(2023, 1, 1),
            date_basis="invalid",
        )
    known = SourceValidity(
        source=source,
        retrieved=date(2026, 11, 6),
        effective_from=date(2023, 1, 1),
        effective_until=date(2023, 12, 31),
        date_basis="synthetic documented period",
    )
    known.require_applicable(date(2023, 12, 31))
    with pytest.raises(ValueError, match="does not cover"):
        known.require_applicable(date(2026, 11, 6))


def test_period_qualification_requires_matching_dated_evidence(tmp_path: Path) -> None:
    """Verified bytes and affirmative judgments cannot bypass costing dates."""
    path = tmp_path / "evidence"
    path.write_bytes(b"synthetic evidence")
    digest = sha256(path.read_bytes()).hexdigest()
    source = SourceRecord(
        source_id="s",
        sha256=digest,
        edition="v1",
        locator="A1",
        limitations="synthetic",
    )
    parameter = Parameter(
        parameter_id="a",
        raw_value="1",
        derived_value="1",
        unit="h",
        source_sha256=digest,
        source_locator="A1",
        transformation="identity",
        uncertainty="synthetic",
        status="observed",
    )
    parameters = ParameterSet(
        version_id="v1",
        workbook_sha256=digest,
        parameters=(parameter,),
    )
    qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="A1",
        dimensional_basis="hours",
        applicability="synthetic",
        qualification="qualified",
        blockers=(),
    )
    ledger = QualificationLedger(
        parameter_set=parameters,
        qualifications=(qualification,),
    )
    validity = SourceValidity(
        source=source,
        retrieved=date(2026, 11, 6),
        effective_from=date(2023, 1, 1),
        effective_until=date(2023, 12, 31),
        date_basis="synthetic period",
    )
    verify_qualified_period(
        ledger,
        {"s": path},
        (validity,),
        required_ids=("a",),
        costing_date=date(2023, 6, 1),
    )
    with pytest.raises(ValueError, match="validity missing"):
        verify_qualified_period(
            ledger,
            {"s": path},
            (),
            required_ids=("a",),
            costing_date=date(2023, 6, 1),
        )
    with pytest.raises(ValueError, match="does not cover"):
        verify_qualified_period(
            ledger,
            {"s": path},
            (validity,),
            required_ids=("a",),
            costing_date=date(2026, 6, 1),
        )


def test_observation_date_does_not_require_invented_expiry() -> None:
    """An evidenced historical observation supports only its explicit date."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="2023",
        locator="A1",
        limitations="synthetic",
    )
    evidence = SourceValidity(
        source=source,
        retrieved=date(2026, 11, 6),
        effective_from=date(2023, 9, 2),
        effective_until=None,
        date_basis="Explicit historical observation",
        applicability_kind="observation",
    )
    evidence.require_applicable(date(2023, 9, 2))
    forged = evidence.model_copy(update={"effective_until": date(2024, 1, 1)})
    with pytest.raises(ValueError, match="one date"):
        forged.require_applicable(date(2023, 9, 2))
    with pytest.raises(ValueError, match="does not cover"):
        evidence.require_applicable(date(2023, 9, 3))
    with pytest.raises(ValueError, match="one date"):
        SourceValidity.model_validate(
            evidence.model_dump() | {"effective_until": date(2024, 1, 1)},
        )


def test_reported_specifications_require_raw_source_values() -> None:
    """Manufacturer reports must retain evidence without claiming measurement."""
    fields = {
        "parameter_id": "kit-capacity",
        "raw_value": "96",
        "derived_value": "96",
        "unit": "nominal samples/kit",
        "source_sha256": "a" * 64,
        "source_locator": "manufacturer table",
        "transformation": "identity",
        "uncertainty": "nominal only",
        "status": "reported",
    }
    value = Parameter.model_validate(fields)
    checks.require_equal(value.status, "reported")
    with pytest.raises(ValueError, match="require source data"):
        Parameter.model_validate(fields | {"raw_value": None})


def test_parameter_exports_are_idempotent_and_never_replace(tmp_path: Path) -> None:
    """A new version cannot overwrite a previously retained baseline path."""
    baseline = ParameterSet(version_id="v1", workbook_sha256="a" * 64, parameters=())
    path = tmp_path / "baseline.json"
    digest = export_parameter_set(baseline, path)
    original = path.read_bytes()
    checks.require_equal(export_parameter_set(baseline, path), digest)
    with pytest.raises(FileExistsError, match="different content"):
        export_parameter_set(successor(baseline, (), version_id="v2"), path)
    checks.require_equal(path.read_bytes(), original)
    path.write_bytes(b"tampered export")
    with pytest.raises(FileExistsError, match="different content"):
        export_parameter_set(baseline, path)
    checks.require_equal(path.read_bytes(), b"tampered export")


def test_missing_evidence_inputs_need_no_fabricated_source_identity() -> None:
    """Unknown acquisition costs remain explicit records with no invented hash."""
    missing = InputRequirement(
        input_id="C02:kit-cost",
        resource_id="C02:kit",
        role="acquisition unit cost",
        parameter=None,
        qualification=None,
        blockers=("No local acquisition evidence",),
    )
    manifest = InputManifest(
        version_id="v1",
        candidate_id="C02",
        workbook_sha256="a" * 64,
        scope="synthetic kit requirement",
        required_ids=(missing.input_id,),
        inputs=(missing,),
    )
    checks.require_equal(manifest.inputs[0].parameter, None)
    checks.require_equal(manifest.blocked_input_ids(), (missing.input_id,))
    with pytest.raises(ValueError, match="1 blocked requirements"):
        manifest.require_ready()

    with pytest.raises(ValueError, match="explicit blockers"):
        InputRequirement.model_validate(missing.model_dump() | {"blockers": ()})
    with pytest.raises(ValueError, match="coverage"):
        InputManifest.model_validate(manifest.model_dump() | {"inputs": ()})
