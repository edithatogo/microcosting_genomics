# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check explicit task-to-workload mappings without inferred allocation."""

from hashlib import sha256

import pytest

from genomics_microcosting.nextflow_trace import TraceContext
from genomics_microcosting.trace_workload import TaskMapping, bind_trace_workload
from tests import checks
from tests.test_workload_contract import workload

PAYLOAD = (
    b"task_id\thash\tprocess\tstatus\tattempt\n"
    b"1\th\tp\tCOMPLETED\t1\n2\th2\tp\tCACHED\t1\n"
)


def context() -> TraceContext:
    """Declare synthetic export provenance."""
    return TraceContext(
        run_id="run",
        workload_id="w1",
        nextflow_version="synthetic",
        executor="synthetic",
        source_sha256=sha256(PAYLOAD).hexdigest(),
        raw_metrics=True,
    )


def mappings() -> tuple[TaskMapping, ...]:
    """Associate one task with a case and explicitly retain shared work."""
    return (
        TaskMapping(task_id="1", attempt=1, scope="cases", case_ids=("a",)),
        TaskMapping(task_id="2", attempt=1, scope="shared", case_ids=()),
    )


def test_mapping_preserves_shared_work_and_cases_without_tasks() -> None:
    """A task is not a test and unrepresented cases are visible."""
    result = bind_trace_workload(PAYLOAD, context(), workload(), mappings())
    checks.require_equal(result.cases_without_tasks, ("b",))
    checks.require_equal(result.shared_task_attempts, (("2", 1),))
    checks.require_equal(result.allocation_state, "unallocated")
    checks.require_equal(len(result.trace.tasks), 2)


def test_missing_duplicate_and_unknown_case_mapping_fail_closed() -> None:
    """Every trace attempt has exactly one explicit valid mapping."""
    good = mappings()
    for selected in (
        good[:1],
        (good[0], good[0]),
        (good[0].model_copy(update={"case_ids": ("missing",)}), good[1]),
    ):
        with pytest.raises(ValueError, match=r"coverage|case"):
            bind_trace_workload(PAYLOAD, context(), workload(), selected)
    with pytest.raises(ValueError, match="workload identity"):
        bind_trace_workload(
            PAYLOAD,
            context().model_copy(update={"workload_id": "other"}),
            workload(),
            good,
        )
    with pytest.raises(ValueError, match="hash"):
        bind_trace_workload(PAYLOAD + b"\n", context(), workload(), good)


def test_pooled_case_relationships_are_explicit_and_bindings_are_canonical() -> None:
    """Multiple cases may share a task; input order cannot change its identity."""
    good = mappings()
    pooled = (good[0].model_copy(update={"case_ids": ("a", "b")}), good[1])
    bound = bind_trace_workload(PAYLOAD, context(), workload(), pooled)
    checks.require_equal(bound.cases_without_tasks, ())
    reordered = bind_trace_workload(PAYLOAD, context(), workload(), pooled[::-1])
    checks.require_equal(bound.binding_sha256, reordered.binding_sha256)
    if (
        bound.binding_sha256
        == bind_trace_workload(
            PAYLOAD,
            context(),
            workload(),
            good,
        ).binding_sha256
    ):
        msg = "Changed relationships must change binding identity"
        raise AssertionError(msg)
