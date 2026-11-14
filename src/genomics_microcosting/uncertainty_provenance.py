# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Immutable uncertainty assertions without inferred probability semantics."""

import re
from hashlib import sha256
from io import BytesIO
from itertools import pairwise
from typing import Literal, Self
lazy from decimal import Decimal, InvalidOperation
lazy from pathlib import Path

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.provenance_ledger import (
    ParameterSet,
    SourceRecord,
    require_resolved_parameters,
)
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class BoundValue(BaseModel):
    """Retain one source location and either its numeric value or absence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    value: Decimal | None = Field(allow_inf_nan=False)
    locator: NonEmpty
    absence_reason: NonEmpty | None

    @model_validator(mode="after")
    def validate_absence(self) -> Self:
        """Reject implicit missing values or contradictory absence reasons."""
        if (self.value is None) != (self.absence_reason is not None):
            message = "Bound absence requires a reason and cannot accompany a value"
            raise ValueError(message)
        return self


class EvidenceDeclaration(BaseModel):
    """Represent an unresolved or source-attributed caller assertion."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    state: Literal["unresolved", "declared"]
    description: NonEmpty | None
    source: SourceRecord | None

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        """Require source and description together only for declarations."""
        if self.state == "declared":
            if self.description is None or self.source is None:
                message = "Declared evidence requires a description and source"
                raise ValueError(message)
        elif self.description is not None or self.source is not None:
            message = "Unresolved evidence cannot assert a description or source"
            raise ValueError(message)
        return self


class UncertaintyRecord(BaseModel):
    """Keep reported bounds separate from asserted distributions and dependence.

    Source attribution and declarations do not prove interpretation, statistical
    adequacy or economic applicability, and this model does not execute PSA.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    measure_id: NonEmpty
    unit: NonEmpty
    source: SourceRecord
    lower: BoundValue
    midpoint: BoundValue
    upper: BoundValue
    interpretation: Literal["unresolved", "reported_range"]
    interpretation_evidence: EvidenceDeclaration
    distribution: EvidenceDeclaration
    dependence: EvidenceDeclaration

    @model_validator(mode="after")
    def ordered_bounds(self) -> Self:
        """Reject inconsistent numeric bounds without filling missing values."""
        if (self.interpretation == "reported_range") != (
            self.interpretation_evidence.state == "declared"
        ):
            message = "Range interpretation requires a source-attributed declaration"
            raise ValueError(message)
        present = [
            b.value
            for b in (self.lower, self.midpoint, self.upper)
            if b.value is not None
        ]
        if any(left > right for left, right in pairwise(present)):
            message = "Available bounds must be ordered"
            raise ValueError(message)
        return self

    def require_specified(self) -> None:
        """Require structural declarations, not evidence of statistical validity."""
        checked = UncertaintyRecord.model_validate(self.model_dump())
        if any(
            b.value is None for b in (checked.lower, checked.midpoint, checked.upper)
        ):
            message = "Complete bounds are required"
            raise ValueError(message)
        if checked.interpretation == "unresolved":
            message = "Bound interpretation must be declared"
            raise ValueError(message)
        if (
            checked.distribution.state != "declared"
            or checked.dependence.state != "declared"
        ):
            message = "Distribution and dependence declarations are required"
            raise ValueError(message)


class UncertaintyLedger(BaseModel):
    """Bind uncertainty assertions to exactly one parameter-set version.

    Source bytes and declarative structure do not establish semantic support,
    valid distributions, correlations or suitability for a particular analysis.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter_set: ParameterSet
    records: tuple[UncertaintyRecord, ...]

    @model_validator(mode="after")
    def exact_coverage(self) -> Self:
        """Reject omitted, duplicate, dimensionally stale or inconsistent records."""
        records = {record.measure_id: record for record in self.records}
        parameters = {item.parameter_id: item for item in self.parameter_set.parameters}
        if len(records) != len(self.records) or records.keys() != parameters.keys():
            message = "Uncertainty coverage differs from parameter scope"
            raise ValueError(message)
        for identifier, parameter in parameters.items():
            record = records[identifier]
            if record.unit != parameter.unit:
                message = "Uncertainty unit differs from parameter unit"
                raise ValueError(message)
            if (
                record.midpoint.value is not None
                and parameter.derived_value is not None
            ):
                try:
                    value = Decimal(parameter.derived_value)
                except InvalidOperation as error:
                    message = "Parameter midpoint must be finite and numeric"
                    raise ValueError(message) from error
                if not value.is_finite() or value != record.midpoint.value:
                    message = "Uncertainty midpoint differs from parameter value"
                    raise ValueError(message)
        return self

    def verify_required(
        self,
        required_ids: tuple[str, ...],
        snapshots: dict[str, Path],
    ) -> None:
        """Verify structure and source bytes without asserting scientific validity."""
        checked = UncertaintyLedger.model_validate(self.model_dump())
        require_resolved_parameters(
            checked.parameter_set,
            required_ids,
            checked.parameter_set.workbook_sha256,
        )
        sources_by_id: dict[str, SourceRecord] = {}
        for record in checked.records:
            if record.measure_id not in required_ids:
                continue
            record.require_specified()
            sources = (
                record.source,
                record.interpretation_evidence.source,
                record.distribution.source,
                record.dependence.source,
            )
            for source in sources:
                if source is None:
                    message = "Uncertainty source missing"
                    raise ValueError(message)
                previous = sources_by_id.get(source.source_id)
                if previous is not None and previous != source:
                    message = "Conflicting uncertainty source identity"
                    raise ValueError(message)
                sources_by_id[source.source_id] = source
                path = snapshots.get(source.source_id)
                if path is None or not path.is_file():
                    message = "Uncertainty source snapshot missing"
                    raise ValueError(message)
                if sha256(path.read_bytes()).hexdigest() != source.sha256:
                    message = "Uncertainty source hash mismatch"
                    raise ValueError(message)
            bound_path = snapshots[record.source.source_id]
            payload = bound_path.read_bytes()
            if sha256(payload).hexdigest() != record.source.sha256:
                message = "Uncertainty source hash mismatch"
                raise ValueError(message)
            _verify_bound_values(
                record,
                payload,
                workbook=record.source.sha256 == checked.parameter_set.workbook_sha256,
            )


def _verify_bound_values(
    record: UncertaintyRecord,
    payload: bytes,
    *,
    workbook: bool,
) -> None:
    """Match bound values to supported exact source locations, not their meaning."""
    bounds = (record.lower, record.midpoint, record.upper)
    if workbook:
        book = load_workbook(BytesIO(payload), data_only=True, read_only=True)
        try:
            for bound in bounds:
                match = re.fullmatch(r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)", bound.locator)
                if match is None or not 1 <= int(match.group(1)) <= len(
                    book.worksheets,
                ):
                    message = "Uncertainty bound source locator unsupported"
                    raise ValueError(message)
                value = book.worksheets[int(match.group(1)) - 1][match.group(2)].value
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or Decimal(str(value)) != bound.value
                ):
                    message = "Uncertainty bound source value mismatch"
                    raise ValueError(message)
        finally:
            book.close()
        return
    try:
        lines = payload.decode("utf-8").splitlines()
        for bound in bounds:
            match = re.fullmatch(r"line ([1-9][0-9]*)", bound.locator)
            if match is None or int(match.group(1)) > len(lines):
                message = "Uncertainty bound source locator unsupported"
                raise ValueError(message)
            if Decimal(lines[int(match.group(1)) - 1].strip()) != bound.value:
                message = "Uncertainty bound source value mismatch"
                raise ValueError(message)
    except (UnicodeDecodeError, InvalidOperation) as error:
        message = "Uncertainty bound source value unsupported"
        raise ValueError(message) from error
