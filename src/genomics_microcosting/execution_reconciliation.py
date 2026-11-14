# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reconcile explicit physical-execution declarations across exact trace exports.

Execution links are declared assumptions. Neither short task hashes nor equal
counters independently establish physical identity. Cached timings remain raw
observations and never become new execution consumption or implicit zero.
"""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from genomics_microcosting.nextflow_trace import TraceTask, read_raw_trace
from genomics_microcosting.parameter_provenance import Digest, NonEmpty
lazy from genomics_microcosting.trace_registry import TraceExport

MAX_EXPORTS = 256
MAX_BINDINGS = 100000
RowIdentity = tuple[str, str, str, int]


class ExecutionBinding(BaseModel):
    """Declare one exact row's physical execution or cache-producer identity."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    source_sha256: Digest
    run_id: NonEmpty
    task_id: NonEmpty
    attempt: int = Field(strict=True, gt=0)
    execution_id: NonEmpty
    role: Literal["execution", "cache_reference"]
    identity_basis: NonEmpty


@dataclass(frozen=True)
class ExecutionObservation:
    """Preserve exact row provenance, counters and the explicit mapping."""

    binding: ExecutionBinding
    task: TraceTask


@dataclass(frozen=True)
class ReconciledExecution:
    """One declared physical execution with all observations still attached."""

    execution_id: str
    observations: tuple[ExecutionObservation, ...]
    duration_ms: int | None
    realtime_ms: int | None


@dataclass(frozen=True)
class CounterSum:
    """A sum of unique task counters, never workflow wall time or CPU time."""

    total: int | None
    known_subtotal: int
    missing_execution_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionReconciliation:
    """Retain explicit identity assumptions and separate counter completeness."""

    format_version: Literal["trace-execution-reconciliation-v1"]
    input_sha256: str
    observations: tuple[ExecutionObservation, ...]
    executions: tuple[ReconciledExecution, ...]
    sum_task_duration_ms: CounterSum
    sum_task_realtime_ms: CounterSum
    identity_state: Literal["declared_not_independently_authenticated"]


def _key(binding: ExecutionBinding) -> RowIdentity:
    return (binding.source_sha256, binding.run_id, binding.task_id, binding.attempt)


def _execution(
    execution_id: str,
    observations: tuple[ExecutionObservation, ...],
) -> ReconciledExecution:
    originals = tuple(o for o in observations if o.binding.role == "execution")
    if not originals:
        msg = "Orphan cache reference has no selected execution producer"
        raise ValueError(msg)
    if len({o.task.status for o in originals}) != 1:
        msg = "Physical execution status conflict"
        raise ValueError(msg)
    if any(o.binding.role == "cache_reference" for o in observations) and (
        originals[0].task.status != "COMPLETED"
    ):
        msg = "A failed execution cannot produce a cache reference"
        raise ValueError(msg)
    for field in (
        "task_hash",
        "process",
        "attempt",
        "requested_cpus",
        "requested_memory_bytes",
        "peak_rss_bytes",
        "duration_ms",
        "realtime_ms",
    ):
        values = {
            getattr(o.task, field)
            for o in observations
            if getattr(o.task, field) is not None
        }
        if len(values) > 1:
            msg = "Physical execution identity or counter conflict"
            raise ValueError(msg)
    # A cache record cannot establish a missing original counter. Nor can a
    # partial repeated observation silently replace a complete original export.
    duration = (
        originals[0].task.duration_ms
        if all(o.task.duration_ms is not None for o in originals)
        else None
    )
    realtime = (
        originals[0].task.realtime_ms
        if all(o.task.realtime_ms is not None for o in originals)
        else None
    )
    return ReconciledExecution(execution_id, observations, duration, realtime)


def _sum(executions: tuple[ReconciledExecution, ...], *, realtime: bool) -> CounterSum:
    pairs = tuple(
        (e.execution_id, e.realtime_ms if realtime else e.duration_ms)
        for e in executions
    )
    missing = tuple(name for name, value in pairs if value is None)
    known = sum(value for _, value in pairs if value is not None)
    return CounterSum(known if not missing else None, known, missing)


def reconcile_executions(
    exports: tuple[TraceExport, ...],
    bindings: tuple[ExecutionBinding, ...],
) -> ExecutionReconciliation:
    """Verify every exact row then sum unique explicitly linked task counters.

    Args:
        exports: Explicitly selected exact raw exports, such as registry readback.
        bindings: Complete one-to-one row coverage with justified identity links.

    Returns:
        Raw observations and conservative unique-execution counter sums.

    Raises:
        ValueError: Invalid bytes, duplicated/missing rows, cache or counter links.

    """
    if len(exports) > MAX_EXPORTS or len(bindings) > MAX_BINDINGS:
        msg = "Selected execution reconciliation exceeds bounded profile"
        raise ValueError(msg)
    rows: dict[RowIdentity, TraceTask] = {}
    contexts: dict[str, object] = {}
    for export in exports:
        trace = read_raw_trace(export.payload, export.context)
        context = trace.context
        if context.source_sha256 in contexts:
            msg = "Duplicate selected execution export"
            raise ValueError(msg)
        contexts[context.source_sha256] = context.model_dump(mode="json")
        for task in trace.tasks:
            rows[
                (context.source_sha256, context.run_id, task.task_id, task.attempt)
            ] = task
    checked = tuple(ExecutionBinding.model_validate(b) for b in bindings)
    mapped = {_key(b): b for b in checked}
    if len(mapped) != len(checked) or mapped.keys() != rows.keys():
        msg = "Execution binding coverage differs or repeats selected rows"
        raise ValueError(msg)
    observations = tuple(
        ExecutionObservation(mapped[key], rows[key]) for key in sorted(rows)
    )
    grouped: dict[str, list[ExecutionObservation]] = {}
    for observation in observations:
        task, binding = observation.task, observation.binding
        if (binding.role == "cache_reference" and task.status != "CACHED") or (
            binding.role == "execution" and task.status not in {"COMPLETED", "FAILED"}
        ):
            msg = "Trace status does not support the declared execution/cache role"
            raise ValueError(msg)
        grouped.setdefault(binding.execution_id, []).append(observation)
    executions = tuple(
        _execution(name, tuple(grouped[name])) for name in sorted(grouped)
    )
    identity = {
        "version": "trace-execution-reconciliation-v1",
        "contexts": contexts,
        "bindings": [o.binding.model_dump(mode="json") for o in observations],
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return ExecutionReconciliation(
        "trace-execution-reconciliation-v1",
        digest,
        observations,
        executions,
        _sum(executions, realtime=False),
        _sum(executions, realtime=True),
        "declared_not_independently_authenticated",
    )
