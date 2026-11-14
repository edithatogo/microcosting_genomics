# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replay exact synthetic exports produced by local Nextflow 26.10.5."""

from decimal import Decimal
from hashlib import sha256

import pytest

from genomics_microcosting.nextflow_trace import TraceContext, read_raw_trace
from genomics_microcosting.trace_workload import TaskMapping, bind_trace_workload
from genomics_microcosting.workload_contract import Workload, WorkloadCase
from tests import checks

HEADER = (
    b"task_id\thash\tname\tprocess\tstatus\tattempt\tcpus\tmemory\t"
    b"peak_rss\tduration\trealtime\texit\n"
)
INITIAL = HEADER + (
    b"1\tac/20f3c1\tSYNTHETIC (success)\tSYNTHETIC\tCOMPLETED\t1\t1\t"
    b"67108864\t-\t1107\t1030\t0\n"
    b"2\ta4/32767a\tSYNTHETIC (retry)\tSYNTHETIC\tFAILED\t1\t1\t"
    b"67108864\t-\t78\t19\t17\n"
    b"3\tbe/a681ba\tSYNTHETIC (retry)\tSYNTHETIC\tCOMPLETED\t2\t1\t"
    b"67108864\t-\t1083\t1028\t0\n"
)
RESUME = HEADER + (
    b"2\tbe/a681ba\tSYNTHETIC (retry)\tSYNTHETIC\tCACHED\t2\t1\t"
    b"67108864\t-\t1083\t1028\t0\n"
    b"1\tac/20f3c1\tSYNTHETIC (success)\tSYNTHETIC\tCACHED\t1\t1\t"
    b"67108864\t-\t1107\t1030\t0\n"
)


def probe_context(payload: bytes, run: str) -> TraceContext:
    """Bind a retained export to its actual local engine and run name."""
    return TraceContext(
        run_id=f"t5_synthetic_{run}",
        workload_id="t5-nf-synthetic-v1",
        nextflow_version="26.10.5 build 14654",
        executor="local",
        raw_metrics=True,
        source_sha256=sha256(payload).hexdigest(),
    )


def test_actual_export_preserves_failed_and_cached_attempts() -> None:
    """Cached timings are retained observations rather than newly consumed resources."""
    checks.require_equal(
        sha256(INITIAL).hexdigest(),
        "b46215c7952d9855e6f69a7b6a71d132129cb059237a6ecf0f1b60eee8f09569",
    )
    checks.require_equal(
        sha256(RESUME).hexdigest(),
        "0b83fbdacd5260372edc105c559f2dc88f4e4c7e54d6fd497f599058a1ee6cbb",
    )
    initial = read_raw_trace(INITIAL, probe_context(INITIAL, "initial"))
    resumed = read_raw_trace(RESUME, probe_context(RESUME, "resume"))
    checks.require_equal(
        tuple((t.status, t.attempt) for t in initial.tasks),
        (("COMPLETED", 1), ("FAILED", 1), ("COMPLETED", 2)),
    )
    checks.require_equal(
        tuple((t.status, t.attempt) for t in resumed.tasks),
        (("CACHED", 2), ("CACHED", 1)),
    )
    originals = {t.task_hash: t for t in initial.tasks if t.status == "COMPLETED"}
    for task in resumed.tasks:
        original = originals[task.task_hash]
        checks.require_equal(task.realtime_ms, original.realtime_ms)
        checks.require_equal(task.duration_ms, original.duration_ms)
        checks.require_equal(task.peak_rss_bytes, None)
        checks.require_equal(task.requested_cpus, 1)
        checks.require_equal(task.requested_memory_bytes, 67108864)
    checks.require_equal(dict(initial.tasks[1].raw_fields)["exit"], "17")


@pytest.mark.parametrize(("payload", "run"), [(INITIAL, "initial"), (RESUME, "resume")])
def test_actual_export_maps_to_explicit_synthetic_cases(
    payload: bytes,
    run: str,
) -> None:
    """Task attempts map to virtual case IDs without becoming case attempt history."""
    workload = Workload(
        workload_id="t5-nf-synthetic-v1",
        process_id="synthetic-trace-probe",
        process_graph_sha256="1d0c38cde846ac55047692905d1635c9be54ebbc918ee7a9495789ca71a2265c",
        parameter_version_id="synthetic-no-cost-v1",
        horizon_seconds=Decimal(60),
        control_ids=(),
        attempts=(),
        cases=tuple(
            WorkloadCase(
                case_id=name,
                requested_test_id=f"toy-{name}",
                assay_id="synthetic",
                arrival_seconds=None,
                patient_ids=None,
                family_ids=None,
                specimen_ids=None,
                library_ids=None,
                reportable_result_ids=None,
            )
            for name in ("success", "retry")
        ),
    )
    context = probe_context(payload, run)
    trace = read_raw_trace(payload, context)
    by_name = {"SYNTHETIC (success)": "success", "SYNTHETIC (retry)": "retry"}
    mappings = tuple(
        TaskMapping(
            task_id=t.task_id,
            attempt=t.attempt,
            scope="cases",
            case_ids=(by_name[dict(t.raw_fields)["name"]],),
        )
        for t in trace.tasks
    )
    bound = bind_trace_workload(payload, context, workload, mappings)
    checks.require_equal(bound.cases_without_tasks, ())
    checks.require_equal(bound.allocation_state, "unallocated")
    checks.require_equal(bound.workload.attempts, ())
