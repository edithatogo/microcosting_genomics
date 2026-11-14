# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Immutable, explicit parameter versions for research costing."""

from hashlib import sha256
from os import link
from tempfile import TemporaryDirectory
from typing import Literal, Self
lazy from datetime import date
lazy from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.parameter_provenance import Digest, NonEmpty


class Parameter(BaseModel):
    """Record a parameter with its source and transformation status."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter_id: NonEmpty
    raw_value: str | None
    derived_value: str | None
    unit: NonEmpty
    source_sha256: Digest
    source_locator: NonEmpty
    transformation: NonEmpty
    uncertainty: NonEmpty
    status: Literal["observed", "reported", "derived", "assumed", "unresolved"]

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        """Keep unresolved values explicit and derived values traceable."""
        if self.status == "unresolved" and self.derived_value is not None:
            msg = "Unresolved parameters cannot have an active derived value"
            raise ValueError(msg)
        if self.status != "unresolved" and self.derived_value is None:
            msg = "Resolved parameters require a derived value"
            raise ValueError(msg)
        if (
            self.status in {"observed", "reported", "derived"}
            and self.raw_value is None
        ):
            msg = "Observed, reported and derived values require source data"
            raise ValueError(msg)
        return self


class ParameterSet(BaseModel):
    """Identify an immutable parameter set and its source baseline."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    version_id: NonEmpty
    workbook_sha256: Digest
    parameters: tuple[Parameter, ...]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        """Reject ambiguous parameter identities."""
        ids = [item.parameter_id for item in self.parameters]
        if len(ids) != len(set(ids)):
            msg = "Duplicate parameter identity"
            raise ValueError(msg)
        return self


def successor(
    baseline: ParameterSet,
    replacements: tuple[Parameter, ...],
    *,
    version_id: str,
) -> ParameterSet:
    """Build a successor without mutating or silently adding baseline entries."""
    if version_id == baseline.version_id:
        msg = "Successor must have a distinct version identity"
        raise ValueError(msg)
    baseline = ParameterSet.model_validate(baseline.model_dump())
    checked = tuple(
        Parameter.model_validate(item.model_dump()) for item in replacements
    )
    changes = {item.parameter_id: item for item in checked}
    if len(changes) != len(replacements):
        msg = "Duplicate replacement identity"
        raise ValueError(msg)
    if not changes.keys() <= {item.parameter_id for item in baseline.parameters}:
        msg = "Replacement parameter is absent from baseline"
        raise ValueError(msg)
    return ParameterSet(
        version_id=version_id,
        workbook_sha256=baseline.workbook_sha256,
        parameters=tuple(
            changes.get(item.parameter_id, item) for item in baseline.parameters
        ),
    )


def require_resolved_parameters(
    parameter_set: ParameterSet,
    required_ids: tuple[str, ...],
    workbook_sha256: str,
) -> None:
    """Reject absent or unresolved inputs within the caller-declared scope.

    This checks declared coverage, not the completeness or truth of that scope.
    """
    parameter_set = ParameterSet.model_validate(parameter_set.model_dump())
    if parameter_set.workbook_sha256 != workbook_sha256:
        msg = "Parameter set workbook identity mismatch"
        raise ValueError(msg)
    if not required_ids or len(required_ids) != len(set(required_ids)):
        msg = "Required baseline parameter scope is empty or duplicated"
        raise ValueError(msg)
    parameters = {item.parameter_id: item for item in parameter_set.parameters}
    if not set(required_ids) <= parameters.keys():
        msg = "Required baseline parameter is missing"
        raise ValueError(msg)
    if any(
        parameters[parameter_id].status == "unresolved" for parameter_id in required_ids
    ):
        msg = "Required baseline parameter is unresolved"
        raise ValueError(msg)


class ParameterDelta(BaseModel):
    """Retain complete before/after provenance for a parameter transition."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    before: Parameter
    after: Parameter

    @model_validator(mode="after")
    def stable_identity(self) -> Self:
        """Reject identity changes and empty transitions."""
        if self.before.parameter_id != self.after.parameter_id:
            msg = "Delta parameter identities differ"
            raise ValueError(msg)
        if self.before == self.after:
            msg = "Delta must contain a change"
            raise ValueError(msg)
        return self


class VersionDelta(BaseModel):
    """Describe an explicit successor without losing unchanged identities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    baseline: ParameterSet
    successor: ParameterSet
    reason: NonEmpty

    @model_validator(mode="after")
    def consistent_versions(self) -> Self:
        """Keep source identity and parameter membership stable across versions."""
        if self.baseline.version_id == self.successor.version_id:
            msg = "Delta versions must differ"
            raise ValueError(msg)
        if self.baseline.workbook_sha256 != self.successor.workbook_sha256:
            msg = "Delta workbook identities differ"
            raise ValueError(msg)
        before = {p.parameter_id for p in self.baseline.parameters}
        after = {p.parameter_id for p in self.successor.parameters}
        if before != after:
            msg = "Delta parameter membership differs"
            raise ValueError(msg)
        return self

    def changes(self) -> tuple[ParameterDelta, ...]:
        """Return changed records in baseline order, including provenance changes."""
        checked = VersionDelta.model_validate(self.model_dump())
        after = {p.parameter_id: p for p in checked.successor.parameters}
        return tuple(
            ParameterDelta(before=p, after=after[p.parameter_id])
            for p in checked.baseline.parameters
            if p != after[p.parameter_id]
        )

    def unchanged_ids(self) -> tuple[str, ...]:
        """Identify carried-forward records without dropping unresolved entries."""
        checked = VersionDelta.model_validate(self.model_dump())
        changed = {item.before.parameter_id for item in checked.changes()}
        return tuple(
            item.parameter_id
            for item in checked.baseline.parameters
            if item.parameter_id not in changed
        )

    def select(self, version_id: str) -> ParameterSet:
        """Select either retained version explicitly, including rollback."""
        checked = VersionDelta.model_validate(self.model_dump())
        if version_id == checked.baseline.version_id:
            return checked.baseline
        if version_id == checked.successor.version_id:
            return checked.successor
        msg = "Selected version is absent from this transition"
        raise ValueError(msg)


class SourceRecord(BaseModel):
    """Identify retained evidence without treating byte integrity as truth."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    source_id: NonEmpty
    sha256: Digest
    edition: NonEmpty
    locator: NonEmpty
    limitations: NonEmpty


def verify_parameter_sources(
    parameters: ParameterSet,
    sources: tuple[SourceRecord, ...],
    snapshots: dict[str, Path],
) -> None:
    """Require unique source identities and exact retained bytes for each parameter.

    This verifies evidence retention, including unresolved records; semantic
    support, units and local applicability require separate qualification.
    """
    parameters = ParameterSet.model_validate(parameters.model_dump())
    checked = tuple(SourceRecord.model_validate(item.model_dump()) for item in sources)
    ids = [source.source_id for source in checked]
    if len(ids) != len(set(ids)):
        msg = "Duplicate source identity"
        raise ValueError(msg)
    digests: set[str] = set()
    for source in checked:
        path = snapshots.get(source.source_id)
        if path is None or not path.is_file():
            msg = "Required ledger source snapshot missing"
            raise ValueError(msg)
        if sha256(path.read_bytes()).hexdigest() != source.sha256:
            msg = "Ledger source snapshot hash mismatch"
            raise ValueError(msg)
        digests.add(source.sha256)
    if any(
        parameter.source_sha256 not in digests for parameter in parameters.parameters
    ):
        msg = "Parameter source is absent from verified ledger sources"
        raise ValueError(msg)


class ParameterQualification(BaseModel):
    """Retain the evidence judgments required before adopting a parameter."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter: Parameter
    source: SourceRecord
    exact_support: NonEmpty
    dimensional_basis: NonEmpty
    applicability: NonEmpty
    qualification: Literal["qualified", "unresolved"]
    blockers: tuple[NonEmpty, ...]

    @model_validator(mode="after")
    def consistent_qualification(self) -> Self:
        """Reject mismatched evidence and unsupported promotion of unknown inputs."""
        if self.parameter.source_sha256 != self.source.sha256:
            msg = "Qualification source identity mismatch"
            raise ValueError(msg)
        if (
            self.qualification == "qualified"
            and self.parameter.source_locator != self.source.locator
        ):
            msg = "Qualified parameter and source locators differ"
            raise ValueError(msg)
        if self.qualification == "qualified" and (
            self.parameter.status == "unresolved" or self.blockers
        ):
            msg = "Qualified parameter cannot retain unresolved values or blockers"
            raise ValueError(msg)
        if self.qualification == "unresolved" and not self.blockers:
            msg = "Unresolved qualification requires explicit blockers"
            raise ValueError(msg)
        return self


class QualificationLedger(BaseModel):
    """Bind complete qualification coverage to one immutable parameter version."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter_set: ParameterSet
    qualifications: tuple[ParameterQualification, ...]

    @model_validator(mode="after")
    def exact_coverage(self) -> Self:
        """Reject omissions, duplicates and stale parameter qualifications."""
        records = {item.parameter.parameter_id: item for item in self.qualifications}
        if len(records) != len(self.qualifications):
            msg = "Duplicate parameter qualification"
            raise ValueError(msg)
        parameters = {item.parameter_id: item for item in self.parameter_set.parameters}
        if records.keys() != parameters.keys():
            msg = "Qualification coverage differs from parameter scope"
            raise ValueError(msg)
        if any(records[key].parameter != value for key, value in parameters.items()):
            msg = "Qualification refers to a different parameter version"
            raise ValueError(msg)
        sources: dict[str, SourceRecord] = {}
        for record in self.qualifications:
            previous = sources.get(record.source.source_id)
            if previous is not None and previous != record.source:
                msg = "Conflicting records for one source identity"
                raise ValueError(msg)
            sources[record.source.source_id] = record.source
        return self

    def verify_required(
        self,
        required_ids: tuple[str, ...],
        snapshots: dict[str, Path],
    ) -> None:
        """Verify retained source bytes and judgments before accepting inputs."""
        checked = QualificationLedger.model_validate(self.model_dump())
        sources = {
            item.source.source_id: item.source for item in checked.qualifications
        }
        verify_parameter_sources(
            checked.parameter_set,
            tuple(sources.values()),
            snapshots,
        )
        checked.require_qualified(required_ids)

    def require_qualified(self, required_ids: tuple[str, ...]) -> None:
        """Fail closed when any required input lacks an affirmative qualification."""
        checked = QualificationLedger.model_validate(self.model_dump())
        require_resolved_parameters(
            checked.parameter_set,
            required_ids,
            checked.parameter_set.workbook_sha256,
        )
        records = {item.parameter.parameter_id: item for item in checked.qualifications}
        if any(records[key].qualification != "qualified" for key in required_ids):
            msg = "Required parameter evidence is unresolved"
            raise ValueError(msg)


class SourceValidity(BaseModel):
    """Retain explicit source dates without inventing a period of applicability."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    source: SourceRecord
    retrieved: date
    effective_from: date | None
    effective_until: date | None
    date_basis: NonEmpty
    applicability_kind: Literal["period", "observation"] = "period"

    @model_validator(mode="after")
    def ordered_period(self) -> Self:
        """Reject inverted dates and an end date without a known start."""
        if self.effective_until is not None and (
            self.effective_from is None or self.effective_until < self.effective_from
        ):
            msg = "Source validity period is missing its start or inverted"
            raise ValueError(msg)
        if self.applicability_kind == "observation" and (
            self.effective_from is None
            or self.effective_until not in (None, self.effective_from)
        ):
            msg = "Observation evidence must identify one date"
            raise ValueError(msg)
        return self

    def require_applicable(self, period: date) -> None:
        """Reject unknown validity and dates outside the evidenced period."""
        checked = SourceValidity.model_validate(self.model_dump())
        if checked.applicability_kind == "observation":
            if period != checked.effective_from:
                msg = "Observation evidence does not cover selected costing date"
                raise ValueError(msg)
            return
        if checked.effective_from is None or checked.effective_until is None:
            msg = "Source applicability date is unresolved"
            raise ValueError(msg)
        if period < checked.effective_from or period > checked.effective_until:
            msg = "Source does not cover selected costing date"
            raise ValueError(msg)


def verify_qualified_period(
    ledger: QualificationLedger,
    snapshots: dict[str, Path],
    validity: tuple[SourceValidity, ...],
    *,
    required_ids: tuple[str, ...],
    costing_date: date,
) -> None:
    """Require source integrity, semantic judgments and dated applicability."""
    ledger = QualificationLedger.model_validate(ledger.model_dump())
    periods = tuple(
        SourceValidity.model_validate(item.model_dump()) for item in validity
    )
    by_id = {item.source.source_id: item for item in periods}
    if len(by_id) != len(periods):
        msg = "Duplicate source validity identity"
        raise ValueError(msg)
    ledger.verify_required(required_ids, snapshots)
    for record in ledger.qualifications:
        if record.parameter.parameter_id not in required_ids:
            continue
        period = by_id.get(record.source.source_id)
        if period is None or period.source != record.source:
            msg = "Required source validity missing or mismatched"
            raise ValueError(msg)
        period.require_applicable(costing_date)


def export_parameter_set(parameters: ParameterSet, destination: Path) -> str:
    """Publish exact version bytes locally without replacing an existing export.

    A temporary file and exclusive hard-link creation prevent partial exports
    or replacement of another writer's destination. Identical reruns are allowed.
    """
    checked = ParameterSet.model_validate(parameters.model_dump())
    payload = (checked.model_dump_json(indent=2) + "\n").encode()
    if destination.is_symlink():
        msg = "Parameter export destination must not be a symlink"
        raise ValueError(msg)
    with TemporaryDirectory(
        prefix=".parameter-export-",
        dir=destination.parent,
    ) as staging:
        temporary = Path(staging) / "parameters.json"
        temporary.write_bytes(payload)
        try:
            link(temporary, destination)
        except FileExistsError:
            if destination.is_symlink() or destination.read_bytes() != payload:
                msg = "Immutable parameter export already exists with different content"
                raise FileExistsError(msg) from None
    return sha256(payload).hexdigest()


class InputRequirement(BaseModel):
    """Represent a required input even when no supporting source is available."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    input_id: NonEmpty
    resource_id: NonEmpty
    role: NonEmpty
    value_kind: Literal[
        "numeric",
        "workbook_text",
        "workbook_formula_number",
    ] = "numeric"
    formula_token_index: int | None = Field(default=None, strict=True, ge=1)
    parameter: Parameter | None
    qualification: ParameterQualification | None
    blockers: tuple[NonEmpty, ...]

    @model_validator(mode="after")
    def explicit_disposition(self) -> Self:
        """Reject unsupported values and missing evidence without a blocker."""
        if (self.value_kind == "workbook_formula_number") != (
            self.formula_token_index is not None
        ):
            msg = "Formula-number requirements need exactly one positive token index"
            raise ValueError(msg)
        if self.parameter is not None and self.parameter.parameter_id != self.input_id:
            msg = "Required input and parameter identity differ"
            raise ValueError(msg)
        if (
            self.qualification is not None
            and self.qualification.parameter != self.parameter
        ):
            msg = "Required input qualification differs from parameter"
            raise ValueError(msg)
        if not self.blockers and (
            self.parameter is None
            or self.qualification is None
            or self.qualification.qualification != "qualified"
        ):
            msg = "Unqualified required input needs explicit blockers"
            raise ValueError(msg)
        return self


class InputManifest(BaseModel):
    """Account for every input in an explicitly declared comparison scope."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    version_id: NonEmpty
    candidate_id: NonEmpty
    workbook_sha256: Digest
    scope: NonEmpty
    required_ids: tuple[NonEmpty, ...]
    inputs: tuple[InputRequirement, ...]

    @model_validator(mode="after")
    def exact_required_coverage(self) -> Self:
        """Reject empty, duplicated, omitted or extra declared input records."""
        actual = [item.input_id for item in self.inputs]
        if not self.required_ids or len(set(self.required_ids)) != len(
            self.required_ids,
        ):
            msg = "Required input scope is empty or duplicated"
            raise ValueError(msg)
        if len(set(actual)) != len(actual) or set(actual) != set(self.required_ids):
            msg = "Input manifest coverage differs from declared scope"
            raise ValueError(msg)
        return self

    def blocked_input_ids(self) -> tuple[str, ...]:
        """Return every declared input still lacking accepted evidence."""
        checked = InputManifest.model_validate(self.model_dump())
        return tuple(
            item.input_id
            for item in checked.inputs
            if item.blockers
            or item.qualification is None
            or item.qualification.qualification != "qualified"
        )

    def require_ready(self) -> None:
        """Reject unresolved requirements before building any costing calculation."""
        blocked = self.blocked_input_ids()
        if blocked:
            message = f"Input manifest has {len(blocked)} blocked requirements"
            raise ValueError(message)
