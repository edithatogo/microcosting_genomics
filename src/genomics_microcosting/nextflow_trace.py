# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Read an explicitly raw tab-separated Nextflow trace without costing it."""

import csv
import re
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from typing import Literal

from pydantic import BaseModel, ConfigDict

from genomics_microcosting.parameter_provenance import Digest, NonEmpty


class TraceContext(BaseModel):
    """Bind declared trace export context to its exact retained bytes."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    run_id: NonEmpty
    workload_id: NonEmpty
    nextflow_version: NonEmpty
    executor: NonEmpty
    source_sha256: Digest
    raw_metrics: Literal[True]
    profile: Literal["nextflow-raw-tsv-v1"] = "nextflow-raw-tsv-v1"


@dataclass(frozen=True)
class TraceTask:
    """Retain task attempts and raw observations separately from requested values."""

    task_id: str
    task_hash: str
    process: str
    status: str
    attempt: int
    requested_cpus: int | None
    requested_memory_bytes: int | None
    peak_rss_bytes: int | None
    duration_ms: int | None
    realtime_ms: int | None
    raw_fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class TraceImport:
    """Keep exact export provenance without inferring task-to-case relationships."""

    context: TraceContext
    header: tuple[str, ...]
    tasks: tuple[TraceTask, ...]


def _raw_integer(value: str | None) -> int | None:
    if value in (None, "", "-"):
        return None
    if re.fullmatch(r"[0-9]+", value) is None:
        msg = "Unsupported raw integer metric or attempt"
        raise ValueError(msg)
    return int(value)


def _task(header: tuple[str, ...], row: list[str]) -> TraceTask:
    if len(row) != len(header):
        msg = "Trace row width differs from header"
        raise ValueError(msg)
    values = dict(zip(header, row, strict=True))
    required = ("task_id", "hash", "process", "status", "attempt")
    if any(values[k] in ("", "-") or not values[k].strip() for k in required):
        msg = "Trace identity or attempt is missing"
        raise ValueError(msg)
    attempt = _raw_integer(values["attempt"])
    if attempt is None or attempt < 1:
        msg = "Trace attempt must be positive"
        raise ValueError(msg)
    return TraceTask(
        values["task_id"],
        values["hash"],
        values["process"],
        values["status"],
        attempt,
        _raw_integer(values.get("cpus")),
        _raw_integer(values.get("memory")),
        _raw_integer(values.get("peak_rss")),
        _raw_integer(values.get("duration")),
        _raw_integer(values.get("realtime")),
        tuple(zip(header, row, strict=True)),
    )


def read_raw_trace(payload: bytes, context: TraceContext) -> TraceImport:
    """Validate an explicit raw-profile export while retaining missing metrics."""
    context = TraceContext.model_validate(context.model_dump())
    if sha256(payload).hexdigest() != context.source_sha256:
        msg = "Trace source hash mismatch"
        raise ValueError(msg)
    try:
        rows = csv.reader(
            StringIO(payload.decode("utf-8-sig")),
            delimiter="\t",
            strict=True,
        )
        header = tuple(next(rows))
        if (
            len(set(header)) != len(header)
            or any(not h for h in header)
            or not {"task_id", "hash", "process", "status", "attempt"} <= set(header)
        ):
            msg = "Trace header is duplicated or missing required identity fields"
            raise ValueError(msg)
        tasks = tuple(_task(header, row) for row in rows)
    except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
        msg = "Unsupported raw trace encoding or table"
        raise ValueError(msg) from exc
    identities = [(t.task_id, t.attempt) for t in tasks]
    if len(set(identities)) != len(identities):
        msg = "Duplicate task attempt in trace import"
        raise ValueError(msg)
    return TraceImport(context, header, tasks)
