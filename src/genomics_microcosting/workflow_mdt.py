# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Allocate synthetic MDT attendance independently of meeting elapsed time."""

from fractions import Fraction
lazy from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Observation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Attendance(_Observation):
    """One pseudonymous attendee's labour observation."""

    attendee_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    seconds: int | None = Field(ge=0)


class MeetingCase(_Observation):
    """One case and its positive allocation weight."""

    case_id: str = Field(min_length=1)
    weight: int = Field(gt=0)


class MeetingObservation(_Observation):
    """A meeting's independent elapsed, attendee and case observations."""

    elapsed_seconds: int | None = Field(ge=0)
    attendance: tuple[Attendance, ...] = Field(min_length=1)
    cases: tuple[MeetingCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def verify_identities(self) -> Self:
        """Guard against duplicate labour and case shares."""
        if len({row.attendee_id for row in self.attendance}) != len(self.attendance):
            message = "Duplicate MDT attendee"
            raise ValueError(message)
        if len({row.case_id for row in self.cases}) != len(self.cases):
            message = "Duplicate MDT case"
            raise ValueError(message)
        return self

    def labour_seconds(self) -> tuple[tuple[str, str, Fraction | None], ...]:
        """Return attendee/case allocations, retaining unknown duration."""
        total_weight = sum(case.weight for case in self.cases)
        return tuple(
            (
                attendee.attendee_id,
                case.case_id,
                None
                if attendee.seconds is None
                else Fraction(
                    attendee.seconds * case.weight,
                    total_weight,
                ),
            )
            for attendee in self.attendance
            for case in self.cases
        )
