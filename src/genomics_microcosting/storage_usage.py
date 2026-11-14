# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Account for explicit storage copies and lifetimes without inferring prices.

Size and lifetime evidence remain separate. This normalized project profile does
not authenticate observations or infer replica/retention policies or physical
consumption. Constant-size copy intervals are clipped to the declared workload
horizon; incompatible quantity/evidence/time bases never share an aggregate.
"""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from types import MappingProxyType
from typing import Literal, Self
lazy from collections.abc import Mapping

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from genomics_microcosting.parameter_provenance import (
    Digest,
    NonEmpty,
)
from genomics_microcosting.workload_contract import Workload

ByteUnit = Literal["bytes", "kB", "MB", "GB", "TB", "KiB", "MiB", "GiB", "TiB"]
QuantityBasis = Literal["logical", "filesystem_allocated", "billed"]
EvidenceBasis = Literal["observed", "reported", "assumed", "billed"]
TimeBasis = Literal["observed", "reported", "assumed"]
BYTE_FACTORS: Mapping[ByteUnit, int] = MappingProxyType(
    {
        "bytes": 1,
        "kB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    },
)
MAX_DECIMAL_LENGTH = 128


def _number(value: str) -> Fraction:
    if (
        len(value) > MAX_DECIMAL_LENGTH
        or re.fullmatch(
            r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,18})?",
            value,
        )
        is None
    ):
        msg = "Storage values must be bounded finite decimal strings"
        raise ValueError(msg)
    return Fraction(Decimal(value))


class _StorageModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class StorageContext(_StorageModel):
    """Pin both sources and independent baseline/import/retention identities."""

    function_version: Literal["storage-usage-v1"]
    source_run_id: NonEmpty
    exporter_version: NonEmpty
    time_origin_id: NonEmpty
    retention_policy_id: NonEmpty
    baseline_sha256: Digest
    size_source_sha256: Digest
    lifetime_source_sha256: Digest


class StorageObject(_StorageModel):
    """One immutable constant-size copy; aliases must share one observation."""

    observation_id: NonEmpty
    object_id: NonEmpty
    copy_id: NonEmpty
    resource_id: NonEmpty
    object_sha256: Digest | None
    size_value: NonEmpty | None
    size_unit: ByteUnit | None
    quantity_basis: QuantityBasis
    evidence_basis: EvidenceBasis
    observed_at_utc: AwareDatetime | None

    @model_validator(mode="after")
    def check_size(self) -> Self:
        """Keep billed/observed meanings distinct and reject invalid sizes."""
        if (self.quantity_basis == "billed") != (self.evidence_basis == "billed"):
            msg = "Storage billed quantity and evidence basis mismatch"
            raise ValueError(msg)
        if self.evidence_basis == "observed" and self.observed_at_utc is None:
            msg = "Observed storage size needs an observation timestamp"
            raise ValueError(msg)
        if self.size_value is not None:
            value = _number(self.size_value)
            if value < 0:
                msg = "Storage size is negative"
                raise ValueError(msg)
            if self.size_unit is None:
                msg = "Known storage size needs an explicit unit"
                raise ValueError(msg)
            if (
                self.evidence_basis == "observed"
                and (value * BYTE_FACTORS[self.size_unit]).denominator != 1
            ):
                msg = "Observed storage size cannot contain fractional bytes"
                raise ValueError(msg)
        return self


class StorageSizeSnapshot(_StorageModel):
    """Preserve logical, filesystem and billed size declarations separately."""

    format_version: Literal["storage-size-json-v1"]
    workload_id: NonEmpty
    source_run_id: NonEmpty
    exporter_version: NonEmpty
    time_origin_id: NonEmpty
    scope_limit: NonEmpty
    objects: tuple[StorageObject, ...]

    @model_validator(mode="after")
    def unique_copies(self) -> Self:
        """Reject duplicate observation IDs and physical-copy aliases."""
        if len({o.observation_id for o in self.objects}) != len(self.objects):
            msg = "Duplicate storage observation identity"
            raise ValueError(msg)
        if len({(o.resource_id, o.copy_id) for o in self.objects}) != len(
            self.objects,
        ):
            msg = "Duplicate storage resource/copy identity"
            raise ValueError(msg)
        return self


class StorageShare(_StorageModel):
    """An explicit workload fraction, never an inferred case count."""

    workload_id: NonEmpty
    share: NonEmpty

    @model_validator(mode="after")
    def fraction(self) -> Self:
        """Reject invalid allocation fractions without rounding."""
        if not 0 <= _number(self.share) <= 1:
            msg = "Storage share lies outside zero to one"
            raise ValueError(msg)
        return self


class StorageLifetime(_StorageModel):
    """One half-open lifetime relative to the explicitly named time origin."""

    observation_id: NonEmpty
    start_seconds: NonEmpty | None
    end_seconds: NonEmpty | None
    time_basis: TimeBasis
    shares: tuple[StorageShare, ...]

    @model_validator(mode="after")
    def lifetime_and_shares(self) -> Self:
        """Validate known endpoints and complete nonoverlapping shares."""
        start = None if self.start_seconds is None else _number(self.start_seconds)
        end = None if self.end_seconds is None else _number(self.end_seconds)
        if start is not None and end is not None and end < start:
            msg = "Storage lifetime interval is reversed"
            raise ValueError(msg)
        if (
            len({s.workload_id for s in self.shares}) != len(self.shares)
            or sum((_number(s.share) for s in self.shares), Fraction(0)) > 1
        ):
            msg = "Storage shares overlap or repeat a workload"
            raise ValueError(msg)
        return self


class StorageLifetimeSnapshot(_StorageModel):
    """Retain an independently sourced retention/allocation recipe."""

    format_version: Literal["storage-lifetime-json-v1"]
    workload_id: NonEmpty
    parameter_version_id: NonEmpty
    retention_policy_id: NonEmpty
    time_origin_id: NonEmpty
    scope_limit: NonEmpty
    lifetimes: tuple[StorageLifetime, ...]


@dataclass(frozen=True)
class StorageUsageRow:
    """Expose normalized size, clipped duration and each allocated byte-time."""

    observation: StorageObject
    lifetime: StorageLifetime
    normalized_bytes: Fraction | None
    active_seconds: Fraction | None
    byte_seconds: Fraction | None
    target_byte_seconds: Fraction | None
    other_byte_seconds: Fraction | None
    unallocated_byte_seconds: Fraction | None


@dataclass(frozen=True)
class StorageGroup:
    """Aggregate only compatible quantity, size-evidence and lifetime bases."""

    quantity_basis: QuantityBasis
    evidence_basis: EvidenceBasis
    time_basis: TimeBasis
    byte_seconds: Fraction | None
    target_byte_seconds: Fraction | None
    other_byte_seconds: Fraction | None
    unallocated_byte_seconds: Fraction | None


@dataclass(frozen=True)
class StorageUsageResult:
    """Retain both sources and scope; no global mixed-basis total or price."""

    input_sha256: str
    context: StorageContext
    workload: Workload
    size_scope_limit: str
    lifetime_scope_limit: str
    rows: tuple[StorageUsageRow, ...]
    groups: tuple[StorageGroup, ...]
    unknown_byte_time_ids: tuple[str, ...]


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate storage JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def _duration(lifetime: StorageLifetime, horizon: Fraction) -> Fraction | None:
    start = None if lifetime.start_seconds is None else _number(lifetime.start_seconds)
    end = None if lifetime.end_seconds is None else _number(lifetime.end_seconds)
    if (start is not None and start >= horizon) or (end is not None and end <= 0):
        return Fraction(0)
    if start is None or end is None:
        return None
    return max(Fraction(0), min(horizon, end) - max(Fraction(0), start))


def _product(a: Fraction | None, b: Fraction | None) -> Fraction | None:
    if a == 0 or b == 0:
        return Fraction(0)
    return None if a is None or b is None else a * b


def _sum_known(values: list[Fraction | None]) -> Fraction | None:
    total = Fraction(0)
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _row(
    obj: StorageObject,
    lifetime: StorageLifetime,
    workload: Workload,
    horizon: Fraction,
) -> StorageUsageRow:
    size = (
        None
        if obj.size_value is None or obj.size_unit is None
        else _number(obj.size_value) * BYTE_FACTORS[obj.size_unit]
    )
    duration = _duration(lifetime, horizon)
    amount = _product(size, duration)
    own = sum(
        (
            _number(s.share)
            for s in lifetime.shares
            if s.workload_id == workload.workload_id
        ),
        Fraction(0),
    )
    other = sum(
        (
            _number(s.share)
            for s in lifetime.shares
            if s.workload_id != workload.workload_id
        ),
        Fraction(0),
    )
    return StorageUsageRow(
        obj,
        lifetime,
        size,
        duration,
        amount,
        _product(amount, own),
        _product(amount, other),
        _product(amount, 1 - own - other),
    )


def _groups(rows: tuple[StorageUsageRow, ...]) -> tuple[StorageGroup, ...]:
    groups: dict[
        tuple[QuantityBasis, EvidenceBasis, TimeBasis],
        list[StorageUsageRow],
    ] = {}
    for row in rows:
        key = (
            row.observation.quantity_basis,
            row.observation.evidence_basis,
            row.lifetime.time_basis,
        )
        groups.setdefault(key, []).append(row)
    return tuple(
        StorageGroup(
            *key,
            _sum_known([r.byte_seconds for r in members]),
            _sum_known([r.target_byte_seconds for r in members]),
            _sum_known([r.other_byte_seconds for r in members]),
            _sum_known([r.unallocated_byte_seconds for r in members]),
        )
        for key, members in sorted(groups.items())
    )


def calculate_storage_usage(
    size_payload: bytes,
    lifetime_payload: bytes,
    workload: Workload,
    context: StorageContext,
) -> StorageUsageResult:
    """Integrate constant-size copies over explicit clipped lifetimes.

    Args:
        size_payload: Exact normalized size-source bytes.
        lifetime_payload: Exact independent lifetime/allocation source bytes.
        workload: Frozen phase-one demand, process, horizon and parameter IDs.
        context: Explicit source hashes and import/retention/model identities.

    Returns:
        Per-copy and compatible-group exact byte-time; unknowns stay explicit.

    Raises:
        ValueError: Source, coverage, unit, fraction or model identity fails.

    """
    context = StorageContext.model_validate(context.model_dump())
    workload = Workload.model_validate(workload.model_dump())
    if (
        sha256(size_payload).hexdigest() != context.size_source_sha256
        or sha256(lifetime_payload).hexdigest() != context.lifetime_source_sha256
    ):
        msg = "Storage source hash mismatch"
        raise ValueError(msg)
    sizes = StorageSizeSnapshot.model_validate(
        json.loads(size_payload, object_pairs_hook=_unique_fields),
    )
    times = StorageLifetimeSnapshot.model_validate(
        json.loads(lifetime_payload, object_pairs_hook=_unique_fields),
    )
    if (
        sizes.workload_id != workload.workload_id
        or times.workload_id != workload.workload_id
        or times.parameter_version_id != workload.parameter_version_id
        or sizes.source_run_id != context.source_run_id
        or sizes.exporter_version != context.exporter_version
        or times.retention_policy_id != context.retention_policy_id
        or sizes.time_origin_id != context.time_origin_id
        or times.time_origin_id != context.time_origin_id
    ):
        msg = "Storage context/workload identity mismatch"
        raise ValueError(msg)
    intervals = {t.observation_id: t for t in times.lifetimes}
    if len(intervals) != len(times.lifetimes) or intervals.keys() != {
        o.observation_id for o in sizes.objects
    }:
        msg = "Storage lifetime coverage must match each observation exactly once"
        raise ValueError(msg)
    digits = workload.horizon_seconds.as_tuple()
    if (
        not isinstance(digits.exponent, int)
        or abs(digits.exponent) > MAX_DECIMAL_LENGTH
        or len(digits.digits) > MAX_DECIMAL_LENGTH
    ):
        msg = "Storage horizon numeric representation exceeds profile bound"
        raise ValueError(msg)
    horizon = Fraction(workload.horizon_seconds)
    rows = tuple(
        _row(obj, intervals[obj.observation_id], workload, horizon)
        for obj in sizes.objects
    )
    identity = {
        "context": context.model_dump(mode="json"),
        "workload": workload.model_dump(mode="json"),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return StorageUsageResult(
        digest,
        context,
        workload,
        sizes.scope_limit,
        times.scope_limit,
        rows,
        _groups(rows),
        tuple(r.observation.observation_id for r in rows if r.byte_seconds is None),
    )
