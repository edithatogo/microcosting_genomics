# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Bind verified trace attempts to declared workload cases without allocating cost."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.nextflow_trace import (
    TraceContext,
    TraceImport,
    read_raw_trace,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class TaskMapping(BaseModel):
    """Declare case relationships or shared scope for one trace task attempt."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    task_id: NonEmpty
    attempt: int = Field(strict=True, ge=1)
    scope: Literal["cases", "shared"]
    case_ids: tuple[NonEmpty, ...]

    @model_validator(mode="after")
    def explicit_scope(self) -> Self:
        """Keep shared work separate and reject ambiguous duplicate case references."""
        if len(set(self.case_ids)) != len(self.case_ids) or (
            (self.scope == "cases") != bool(self.case_ids)
        ):
            msg = "Task case relationships are duplicated or inconsistent with scope"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class BoundTraceWorkload:
    """Retain explicit mappings and visible unallocated/unrepresented scope."""

    trace: TraceImport
    workload: Workload
    mappings: tuple[TaskMapping, ...]
    binding_sha256: str
    cases_without_tasks: tuple[str, ...]
    shared_task_attempts: tuple[tuple[str, int], ...]
    allocation_state: Literal["unallocated"] = "unallocated"


def bind_trace_workload(
    payload: bytes,
    context: TraceContext,
    workload: Workload,
    mappings: tuple[TaskMapping, ...],
) -> BoundTraceWorkload:
    """Verify trace bytes and exact mapping coverage without inferring consumption."""
    trace = read_raw_trace(payload, context)
    workload = Workload.model_validate(workload.model_dump())
    if trace.context.workload_id != workload.workload_id:
        msg = "Trace and workload identity differ"
        raise ValueError(msg)
    checked = tuple(TaskMapping.model_validate(m.model_dump()) for m in mappings)
    mapped = {(m.task_id, m.attempt): m for m in checked}
    identities = {(t.task_id, t.attempt) for t in trace.tasks}
    if len(mapped) != len(checked) or mapped.keys() != identities:
        msg = "Trace mapping coverage differs or is duplicated"
        raise ValueError(msg)
    case_ids = {c.case_id for c in workload.cases}
    referenced = {case for mapping in checked for case in mapping.case_ids}
    if not referenced <= case_ids:
        msg = "Trace mapping references an unknown workload case"
        raise ValueError(msg)
    canonical = tuple(sorted(checked, key=lambda m: (m.task_id, m.attempt)))
    identity = {
        "context": trace.context.model_dump(mode="json"),
        "workload": workload.model_dump(mode="json"),
        "mappings": [m.model_dump(mode="json") for m in canonical],
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return BoundTraceWorkload(
        trace,
        workload,
        canonical,
        digest,
        tuple(c.case_id for c in workload.cases if c.case_id not in referenced),
        tuple((m.task_id, m.attempt) for m in canonical if m.scope == "shared"),
    )
