# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Validate evidence-blocked handoffs without qualifying candidate costs.

Catalogue matching proves identity and declared coverage only. It does not prove
retention of source bytes, semantic support, complete resource scope or local
applicability. The separate manifest reader checks retained manifest bytes and
declared counts, without verifying their evidence or completeness.
"""

from hashlib import sha256
from typing import TYPE_CHECKING, Literal, Self
lazy from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.alternative_research import (
    Digest,
    NonEmpty,
    ResearchCatalogue,
    WorkbookLocation,
)
from genomics_microcosting.provenance_ledger import InputManifest

if TYPE_CHECKING:
    from pathlib import Path


class DispositionSource(BaseModel):
    """Preserve exact source references, including unknown hashes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonEmpty
    locator: NonEmpty
    edition: NonEmpty
    snapshot_sha256: Digest | None


class ManifestReference(BaseModel):
    """Retain declared manifest metadata without claiming completeness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: NonEmpty
    sha256: Digest
    required_count: int = Field(gt=0, strict=True)
    blocked_count: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def check_counts(self) -> Self:
        """Reject impossible declared blocked counts."""
        if self.blocked_count > self.required_count:
            message = "Blocked count exceeds required count"
            raise ValueError(message)
        return self


class CandidateDisposition(BaseModel):
    """An evidence-blocked or rejected comparison; no costing permission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: NonEmpty
    scenario_id: NonEmpty
    label: NonEmpty
    disposition: Literal["blocked", "rejected"]
    interface_state: NonEmpty
    affected_output: NonEmpty
    baseline_anchors: tuple[WorkbookLocation, ...] = Field(min_length=1)
    source_records: tuple[DispositionSource, ...] = Field(min_length=1)
    candidate_blockers: tuple[NonEmpty, ...] = Field(min_length=1)
    required_input_manifest: ManifestReference | None
    additional_scope_gap: NonEmpty | None
    costing_available: Literal[False]

    @model_validator(mode="after")
    def check_scope(self) -> Self:
        """Require an explicit gap when the input manifest is absent."""
        if self.required_input_manifest is None and self.additional_scope_gap is None:
            message = "Absent manifest requires an explicit scope gap"
            raise ValueError(message)
        source_ids = [item.source_id for item in self.source_records]
        if len(source_ids) != len(set(source_ids)):
            message = "Duplicate disposition source"
            raise ValueError(message)
        if len(self.baseline_anchors) != len(set(self.baseline_anchors)):
            message = "Duplicate disposition baseline anchor"
            raise ValueError(message)
        return self


class DispositionAssessment(BaseModel):
    """A non-costing assessment retaining original open obligations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format_version: Literal["1.0.0"]
    assessment_date: date
    catalogue_sha256: Digest
    workbook_sha256: Digest
    scope: NonEmpty
    candidates: tuple[CandidateDisposition, ...] = Field(min_length=1)
    original_obligations: NonEmpty
    predecessor_dispositions_sha256: Digest | None = None
    review_correction: NonEmpty | None = None


def read_dispositions(
    path: Path,
    catalogue_path: Path,
) -> DispositionAssessment:
    """Read a full assessment bound to exact catalogue bytes and declarations.

    Args:
        path: Explicitly selected assessment JSON file.
        catalogue_path: Explicitly selected research catalogue JSON file.

    Returns:
        Immutable declarations; no costing or qualification state is changed.

    Raises:
        ValueError: Invalid scope, identity or source declarations.
        OSError: Either explicitly selected file cannot be read.

    """
    payload = catalogue_path.read_bytes()
    catalogue = ResearchCatalogue.model_validate_json(payload)
    assessment = DispositionAssessment.model_validate_json(path.read_bytes())
    if (
        assessment.catalogue_sha256 != sha256(payload).hexdigest()
        or assessment.workbook_sha256 != catalogue.workbook_sha256
    ):
        message = "Disposition catalogue or workbook identity mismatch"
        raise ValueError(message)
    records = {item.candidate_id: item for item in assessment.candidates}
    candidates = {item.candidate_id: item for item in catalogue.candidates}
    if (
        len(records) != len(assessment.candidates)
        or records.keys() != candidates.keys()
    ):
        message = "Disposition coverage requires every candidate exactly once"
        raise ValueError(message)
    scenarios = {item.scenario_id: item for item in catalogue.scenarios}
    sources = {item.source_id: item for item in catalogue.sources}
    for candidate_id, record in records.items():
        candidate = candidates[candidate_id]
        scenario = scenarios.get(record.scenario_id)
        if (
            scenario is None
            or scenario.candidate_id != candidate_id
            or record.label != candidate.label
            or set(record.baseline_anchors) != set(candidate.baseline_locations)
            or {item.source_id for item in record.source_records}
            != set(candidate.source_ids)
        ):
            message = "Disposition candidate/scenario/anchors/sources mismatch"
            raise ValueError(message)
        for reference in record.source_records:
            source = sources[reference.source_id]
            if (
                reference.locator != source.locator
                or reference.edition != source.edition
                or reference.snapshot_sha256 != source.source_snapshot_sha256
            ):
                message = "Disposition source context mismatch"
                raise ValueError(message)
    return assessment


def read_disposition_manifests(
    path: Path,
    catalogue_path: Path,
    manifests: dict[str, Path],
) -> tuple[InputManifest, ...]:
    """Verify all declared manifests against an exact catalogue assessment.

    Args:
        path: Explicitly selected blocked/rejected assessment JSON.
        catalogue_path: Explicitly selected catalogue JSON.
        manifests: Candidate-to-file mapping for every declared manifest.

    Returns:
        Validated manifests in assessment order, retaining unresolved inputs.
        Candidates with no declared manifest remain outside this readback scope.
        Counts describe declared coverage, not scientific completeness
        or costing permission. Source evidence and parameter applicability
        are not checked.

    Raises:
        ValueError: Missing/extra mappings, byte drift or inconsistent metadata.
        OSError: An explicitly selected file cannot be read.

    """
    assessment = read_dispositions(path, catalogue_path)
    declared = {
        item.candidate_id: item.required_input_manifest
        for item in assessment.candidates
        if item.required_input_manifest is not None
    }
    if manifests.keys() != declared.keys():
        message = "Manifest paths must match exactly the declared candidates"
        raise ValueError(message)
    checked: list[InputManifest] = []
    for candidate_id, reference in declared.items():
        payload = manifests[candidate_id].read_bytes()
        if sha256(payload).hexdigest() != reference.sha256:
            message = "Disposition manifest byte identity mismatch"
            raise ValueError(message)
        manifest = InputManifest.model_validate_json(payload)
        if (
            manifest.candidate_id != candidate_id
            or manifest.version_id != reference.version_id
            or manifest.workbook_sha256 != assessment.workbook_sha256
            or len(manifest.required_ids) != reference.required_count
            or len(manifest.blocked_input_ids()) != reference.blocked_count
        ):
            message = "Disposition manifest context or counts mismatch"
            raise ValueError(message)
        checked.append(manifest)
    return tuple(checked)
