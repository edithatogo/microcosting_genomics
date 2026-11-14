# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Immutable phase-one workload accounting; no capacity or cost assumptions."""

from typing import Literal, Self
lazy from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.parameter_provenance import Digest, NonEmpty


class WorkloadCase(BaseModel):
    """One requested test and its explicitly supplied entity relationships."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    case_id: NonEmpty
    requested_test_id: NonEmpty
    assay_id: NonEmpty
    arrival_seconds: Decimal | None = Field(ge=0, allow_inf_nan=False)
    patient_ids: tuple[NonEmpty, ...] | None
    family_ids: tuple[NonEmpty, ...] | None
    specimen_ids: tuple[NonEmpty, ...] | None
    library_ids: tuple[NonEmpty, ...] | None
    reportable_result_ids: tuple[NonEmpty, ...] | None

    @model_validator(mode="after")
    def unique_relationships(self) -> Self:
        """Reject repeated references within a case while allowing shared entities."""
        for ids in (
            self.patient_ids,
            self.family_ids,
            self.specimen_ids,
            self.library_ids,
            self.reportable_result_ids,
        ):
            if ids is not None and len(set(ids)) != len(ids):
                msg = "Duplicate entity relationship within a case"
                raise ValueError(msg)
        return self


class WorkloadAttempt(BaseModel):
    """One case attempt, including failed, cached and cancelled work."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    attempt_id: NonEmpty
    case_id: NonEmpty
    ordinal: int = Field(strict=True, ge=1)
    state: Literal["pending", "completed", "failed", "cached", "cancelled"]


class Workload(BaseModel):
    """Freeze a declared workload independently of batch policy and compute cost."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    format_version: Literal["workload-v1"] = "workload-v1"
    workload_id: NonEmpty
    process_id: NonEmpty
    process_graph_sha256: Digest
    parameter_version_id: NonEmpty
    horizon_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    cases: tuple[WorkloadCase, ...]
    control_ids: tuple[NonEmpty, ...] | None
    attempts: tuple[WorkloadAttempt, ...] | None

    @model_validator(mode="after")
    def consistent_scope(self) -> Self:
        """Reject identity collisions, out-of-horizon arrivals and attempt gaps."""
        case_ids = [c.case_id for c in self.cases]
        test_ids = [c.requested_test_id for c in self.cases]
        if len(set(case_ids)) != len(case_ids) or len(set(test_ids)) != len(test_ids):
            msg = "Duplicate case or requested test identity"
            raise ValueError(msg)
        if self.control_ids is not None and len(set(self.control_ids)) != len(
            self.control_ids,
        ):
            msg = "Duplicate control identity"
            raise ValueError(msg)
        if any(
            c.arrival_seconds is not None and c.arrival_seconds > self.horizon_seconds
            for c in self.cases
        ):
            msg = "Arrival exceeds the declared horizon"
            raise ValueError(msg)
        self._check_attempts(set(case_ids))
        return self

    def _check_attempts(self, case_ids: set[str]) -> None:
        if self.attempts is None:
            return
        ids = [a.attempt_id for a in self.attempts]
        if len(set(ids)) != len(ids):
            msg = "Duplicate attempt identity"
            raise ValueError(msg)
        histories: dict[str, list[int]] = {}
        for attempt in self.attempts:
            if attempt.case_id not in case_ids:
                msg = "Attempt references an unknown case"
                raise ValueError(msg)
            histories.setdefault(attempt.case_id, []).append(attempt.ordinal)
        for ordinals in histories.values():
            if sorted(ordinals) != list(range(1, len(ordinals) + 1)):
                msg = "Attempt history is incomplete or duplicated"
                raise ValueError(msg)

    def entity_counts(self) -> dict[str, int | None]:
        """Count declared unique entities, preserving unknown relationships."""
        checked = Workload.model_validate(self.model_dump())
        result: dict[str, int | None] = {"requested_tests": len(checked.cases)}
        for key, attribute in (
            ("patients", "patient_ids"),
            ("families", "family_ids"),
            ("specimens", "specimen_ids"),
            ("libraries", "library_ids"),
            ("reportable_results", "reportable_result_ids"),
        ):
            groups = [getattr(case, attribute) for case in checked.cases]
            result[key] = (
                None
                if any(group is None for group in groups)
                else len({identifier for group in groups for identifier in group})
            )
        result["controls"] = (
            None if checked.control_ids is None else len(checked.control_ids)
        )
        result["attempts"] = None if checked.attempts is None else len(checked.attempts)
        return result
