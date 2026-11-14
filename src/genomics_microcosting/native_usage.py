# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Read explicitly contextualized native counters without executing a workload."""

import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from genomics_microcosting.parameter_provenance import Digest, NonEmpty

CHILD_SCOPE = (
    "one waited synthetic child; parent, shell, Nextflow and host overhead excluded"
)
RUSAGE_FIELDS = frozenset(
    (
        "ru_idrss",
        "ru_inblock",
        "ru_isrss",
        "ru_ixrss",
        "ru_majflt",
        "ru_maxrss",
        "ru_minflt",
        "ru_msgrcv",
        "ru_msgsnd",
        "ru_nivcsw",
        "ru_nsignals",
        "ru_nswap",
        "ru_nvcsw",
        "ru_oublock",
        "ru_stime",
        "ru_utime",
    ),
)


class _NativeModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class NativeUsageContext(_NativeModel):
    """Retain declared source, producer, runtime and native task relationships."""

    profile: Literal["darwin-wait4-synthetic-v1"] = "darwin-wait4-synthetic-v1"
    source_sha256: Digest
    exporter_sha256: Digest
    child_program_sha256: Digest
    python_version: str = Field(pattern=r"^3\.15\.1(?:\s|$)")
    release: NonEmpty
    machine: NonEmpty
    run_id: NonEmpty
    task_id: NonEmpty
    task_label: NonEmpty
    attempt: int = Field(strict=True, gt=0)
    exit_code: int = Field(strict=True, ge=-127, le=255)


class _NativeRecord(_NativeModel):
    format_version: Literal["darwin-wait4-synthetic-v1"]
    exporter_sha256: Digest
    child_program_sha256: Digest
    python: NonEmpty
    platform: Literal["Darwin"]
    release: NonEmpty
    machine: NonEmpty
    task_label: NonEmpty
    attempt: int = Field(strict=True, gt=0)
    child_pid: int = Field(strict=True, gt=0)
    wait_status: int = Field(strict=True, ge=0, le=65535)
    exit_code: int = Field(strict=True, ge=-127, le=255)
    elapsed_monotonic_ns: int = Field(strict=True, ge=0)
    user_cpu_seconds: NonEmpty
    system_cpu_seconds: NonEmpty
    peak_rss_raw: int = Field(strict=True, ge=0)
    peak_rss_unit: Literal["unqualified"]
    raw_rusage: dict[str, str]
    scope: NonEmpty
    native_accounting_resolution: Literal["not qualified"]


@dataclass(frozen=True)
class NativeUsageObservation:
    """Keep CPU accounting separate from unqualified memory and excluded overhead."""

    context: NativeUsageContext
    child_pid: int
    exit_code: int
    elapsed_monotonic_ns: int
    user_cpu_seconds: Decimal
    system_cpu_seconds: Decimal
    peak_rss_raw: int
    raw_rusage: tuple[tuple[str, str], ...]
    peak_rss_bytes: None = None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate native observation JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def read_native_usage(
    payload: bytes,
    context: NativeUsageContext,
) -> NativeUsageObservation:
    """Verify a fixed counter profile; context matching does not authenticate origin."""
    context = NativeUsageContext.model_validate(context.model_dump())
    if sha256(payload).hexdigest() != context.source_sha256:
        msg = "Native observation source hash mismatch"
        raise ValueError(msg)
    record = _NativeRecord.model_validate(
        json.loads(payload, object_pairs_hook=_unique_fields),
    )
    if (
        record.exporter_sha256 != context.exporter_sha256
        or record.child_program_sha256 != context.child_program_sha256
        or record.python != context.python_version
        or record.release != context.release
        or record.machine != context.machine
        or record.task_label != context.task_label
        or record.attempt != context.attempt
        or record.exit_code != context.exit_code
        or record.scope != CHILD_SCOPE
    ):
        msg = "Native observation context or scope mismatch"
        raise ValueError(msg)
    if os.waitstatus_to_exitcode(record.wait_status) != record.exit_code:
        msg = "Native observation terminal status mismatch"
        raise ValueError(msg)
    if (
        frozenset(record.raw_rusage) != RUSAGE_FIELDS
        or record.raw_rusage["ru_utime"] != record.user_cpu_seconds
        or record.raw_rusage["ru_stime"] != record.system_cpu_seconds
        or record.raw_rusage["ru_maxrss"] != str(record.peak_rss_raw)
        or any(
            re.fullmatch(r"[0-9]+", v) is None
            for k, v in record.raw_rusage.items()
            if k not in ("ru_utime", "ru_stime")
        )
    ):
        msg = "Native raw accounting fields differ from observations"
        raise ValueError(msg)
    try:
        user = Decimal(record.user_cpu_seconds)
        system = Decimal(record.system_cpu_seconds)
    except InvalidOperation as exc:
        msg = "Native CPU counter is not numeric"
        raise ValueError(msg) from exc
    if not user.is_finite() or not system.is_finite() or user < 0 or system < 0:
        msg = "Native CPU counter is invalid"
        raise ValueError(msg)
    return NativeUsageObservation(
        context,
        record.child_pid,
        record.exit_code,
        record.elapsed_monotonic_ns,
        user,
        system,
        record.peak_rss_raw,
        tuple(sorted(record.raw_rusage.items())),
    )
