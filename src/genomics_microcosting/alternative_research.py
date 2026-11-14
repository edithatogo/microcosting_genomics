# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Validate and preview evidence-only alternatives without activating costs."""

from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Literal, Self
lazy from datetime import date

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from pathlib import Path

NonEmpty = Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
WorkbookLocation = Annotated[
    str,
    Field(pattern=r"^WB\d{2}:[A-Z]{1,3}\d+(?::[A-Z]{1,3}\d+)?$"),
]


class ResearchSource(BaseModel):
    """Identify an evidence lead; absent source snapshots stay explicit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonEmpty
    title: NonEmpty
    url: AnyHttpUrl
    locator: NonEmpty
    edition: NonEmpty
    accessed: date
    evidence_class: Literal[
        "primary_study",
        "manufacturer",
        "service_provider",
        "accreditation_body",  # Independent accreditation status evidence.
    ]
    source_snapshot_sha256: Digest | None
    snapshot_url: AnyHttpUrl | None = None
    limitation: NonEmpty


class ResearchCandidate(BaseModel):
    """Describe an unqualified candidate without embedding price assumptions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: NonEmpty
    label: NonEmpty
    source_ids: tuple[NonEmpty, ...] = Field(min_length=1)
    baseline_locations: tuple[WorkbookLocation, ...] = Field(min_length=1)
    process_relationship: Literal["unknown", "changed_process"]
    evidence_state: Literal["research_lead", "qualified_for_comparison"]
    unknowns: tuple[NonEmpty, ...] = Field(min_length=1)
    qualified_baseline_locations: tuple[WorkbookLocation, ...] = ()
    required_baseline_parameter_ids: tuple[NonEmpty, ...] = ()
    qualification_summary: NonEmpty | None = None

    @model_validator(mode="after")
    def check_qualification(self) -> Self:
        """Require an explicit scope and rationale for claimed qualification."""
        if self.evidence_state == "qualified_for_comparison" and (
            not self.qualified_baseline_locations
            or not self.required_baseline_parameter_ids
            or self.qualification_summary is None
        ):
            message = "Qualified candidate requires a baseline scope and rationale"
            raise ValueError(message)
        if len(set(self.required_baseline_parameter_ids)) != len(
            self.required_baseline_parameter_ids,
        ):
            message = "Duplicate required baseline parameter"
            raise ValueError(message)
        return self


class ResearchScenario(BaseModel):
    """An explicitly selected research comparison, not an active costing run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: NonEmpty
    candidate_id: NonEmpty
    kind: Literal["conditional_substitution", "changed_process_counterfactual"]
    baseline_identity: Digest
    limitations: tuple[NonEmpty, ...] = Field(min_length=1)


class ResearchCatalogue(BaseModel):
    """An immutable reference set with checked internal source identities."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format_version: Literal["1.0.0"]
    workbook_sha256: Digest
    process_source_rows_sha256: Digest
    sources: tuple[ResearchSource, ...] = Field(min_length=1)
    candidates: tuple[ResearchCandidate, ...] = Field(min_length=1)
    scenarios: tuple[ResearchScenario, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_links(self) -> Self:
        """Reject dangling sources, duplicate IDs and implicit baseline changes."""
        source_ids = {source.source_id for source in self.sources}
        candidates = {
            candidate.candidate_id: candidate for candidate in self.candidates
        }
        scenario_ids = {scenario.scenario_id for scenario in self.scenarios}
        if (
            len(source_ids) != len(self.sources)
            or len(candidates) != len(self.candidates)
            or len(scenario_ids) != len(self.scenarios)
        ):
            message = "Duplicate source, candidate or scenario identity"
            raise ValueError(message)
        for candidate in self.candidates:
            if not set(candidate.source_ids) <= source_ids:
                message = "Candidate references an unknown source"
                raise ValueError(message)
        for scenario in self.scenarios:
            candidate = candidates.get(scenario.candidate_id)
            if candidate is None or scenario.baseline_identity != self.workbook_sha256:
                message = "Scenario references an unknown candidate or baseline"
                raise ValueError(message)
            if (
                scenario.kind == "conditional_substitution"
                and candidate.process_relationship == "changed_process"
            ):
                message = "Changed process cannot be a same-process substitution"
                raise ValueError(message)
        return self


class ScenarioPreview(BaseModel):
    """A selected evidence lead and its explicit costing blockers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: ResearchScenario
    candidate: ResearchCandidate
    sources: tuple[ResearchSource, ...]
    catalogue_sha256: Digest
    costing_available: Literal[False] = False
    blockers: tuple[str, ...]


def preview_scenario(path: Path, scenario_id: str) -> ScenarioPreview:
    """Read a named research scenario; no baseline or costing inputs are written."""
    payload = path.read_bytes()
    catalogue = ResearchCatalogue.model_validate_json(payload)
    scenario = next(
        (item for item in catalogue.scenarios if item.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise KeyError(scenario_id)
    candidate = next(
        item
        for item in catalogue.candidates
        if item.candidate_id == scenario.candidate_id
    )
    sources = tuple(
        item for item in catalogue.sources if item.source_id in candidate.source_ids
    )
    return ScenarioPreview(
        scenario=scenario,
        candidate=candidate,
        sources=sources,
        catalogue_sha256=sha256(payload).hexdigest(),
        blockers=(
            (
                "Parameter provenance ledger and comparable priced inputs "
                "are not qualified"
            ),
            "Candidate scientific and process equivalence have not been established",
            "Source snapshots and contextual transferability remain unqualified",
            *scenario.limitations,
        ),
    )
