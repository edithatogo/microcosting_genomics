# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Explicit cross-export mappings prevent repeated task-counter consumption."""

from dataclasses import replace
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.execution_reconciliation import (
    ExecutionBinding,
    reconcile_executions,
)
from genomics_microcosting.trace_registry import (
    TraceExport,
    active_trace_exports,
    store_trace,
)
from tests import checks
from tests.test_nextflow_export_profile import INITIAL, RESUME, probe_context


def exports() -> tuple[TraceExport, ...]:
    """Retain original failed/retry and resume exports separately."""
    return tuple(
        TraceExport(payload, probe_context(payload, run))
        for payload, run in [(INITIAL, "initial"), (RESUME, "resume")]
    )


def bindings() -> tuple[ExecutionBinding, ...]:
    """Declare exact links; short task hashes alone never identify executions."""
    first, resumed = exports()
    return tuple(
        ExecutionBinding.model_validate(
            {
                "source_sha256": export.context.source_sha256,
                "run_id": export.context.run_id,
                "task_id": task,
                "attempt": attempt,
                "execution_id": execution,
                "role": role,
                "identity_basis": "Synthetic explicit execution/cache ancestry fixture",
            },
        )
        for export, task, attempt, execution, role in [
            (first, "1", 1, "success", "execution"),
            (first, "2", 1, "failure", "execution"),
            (first, "3", 2, "retry", "execution"),
            (resumed, "1", 1, "success", "cache_reference"),
            (resumed, "2", 2, "retry", "cache_reference"),
        ]
    )


def test_original_and_resume_counters_count_unique_executions() -> None:
    """Cached old timings remain visible without being new consumption."""
    result = reconcile_executions(exports(), bindings())
    checks.require_equal(len(result.executions), 3)
    checks.require_equal(len(result.observations), 5)
    checks.require_equal(result.sum_task_duration_ms.total, 2268)
    checks.require_equal(result.sum_task_realtime_ms.total, 2077)
    checks.require_equal(result.sum_task_realtime_ms.missing_execution_ids, ())
    checks.require_equal(
        reconcile_executions(tuple(reversed(exports())), tuple(reversed(bindings()))),
        result,
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "orphan_cache",
        "cache_as_execution",
        "execution_as_cache",
        "wrong_source",
        "wrong_run",
        "joined_failed_retry",
    ],
)
def test_invalid_execution_links_fail_closed(fault: str) -> None:
    """Every exact selected row requires one valid explicit identity link."""
    links = list(bindings())
    if fault == "missing":
        links.pop()
    elif fault == "duplicate":
        links.append(links[0])
    else:
        index, changes = {
            "orphan_cache": (4, {"execution_id": "absent"}),
            "cache_as_execution": (4, {"role": "execution"}),
            "execution_as_cache": (0, {"role": "cache_reference"}),
            "wrong_source": (0, {"source_sha256": "f" * 64}),
            "wrong_run": (0, {"run_id": "other"}),
            "joined_failed_retry": (1, {"execution_id": "retry"}),
        }[fault]
        links[index] = links[index].model_copy(update=changes)
    with pytest.raises(ValueError, match=r"coverage|cache|execution|conflict"):
        reconcile_executions(exports(), tuple(links))


def test_same_hash_does_not_merge_new_executions() -> None:
    """A distinct explicitly declared execution with identical counters is new."""
    first = exports()[0]
    payload = first.payload.replace(b"SYNTHETIC (success)", b"SYNTHETIC (success2)")
    other = TraceExport(payload, probe_context(payload, "separate"))
    links = bindings()[:3]
    copies = tuple(
        link.model_copy(
            update={
                "source_sha256": other.context.source_sha256,
                "run_id": other.context.run_id,
                "execution_id": link.execution_id + "2",
            },
        )
        for link in links
    )
    result = reconcile_executions((first, other), (*links, *copies))
    checks.require_equal(len(result.executions), 6)
    checks.require_equal(result.sum_task_realtime_ms.total, 4154)


def test_unknown_execution_counter_is_not_filled_from_cache() -> None:
    """A cache observation cannot supply a missing original execution counter."""
    first, cached = exports()
    payload = first.payload.replace(b"1107\t1030", b"1107\t-")
    first = TraceExport(payload, probe_context(payload, "initial"))
    links = tuple(
        link.model_copy(
            update={
                "source_sha256": first.context.source_sha256,
            },
        )
        if link.run_id == first.context.run_id
        else link
        for link in bindings()
    )
    result = reconcile_executions((first, cached), links)
    checks.require_equal(result.sum_task_realtime_ms.total, None)
    checks.require_equal(result.sum_task_realtime_ms.known_subtotal, 1047)
    checks.require_equal(
        result.sum_task_realtime_ms.missing_execution_ids,
        ("success",),
    )


def test_conflicting_cache_counter_is_rejected() -> None:
    """Known original and cached counter disagreements require reconciliation."""
    first, cached = exports()
    payload = cached.payload.replace(b"1083\t1028", b"1083\t1029")
    cached = replace(cached, payload=payload, context=probe_context(payload, "resume"))
    links = tuple(
        link.model_copy(
            update={
                "source_sha256": sha256(payload).hexdigest(),
            },
        )
        if link.run_id == cached.context.run_id
        else link
        for link in bindings()
    )
    with pytest.raises(ValueError, match="conflict"):
        reconcile_executions((first, cached), links)


def test_registry_exports_preserve_bytes_and_reconcile(tmp_path: Path) -> None:
    """Durable latest snapshots feed reconciliation without reconstructing TSV."""
    path = tmp_path / "trace.sqlite"
    for export in exports():
        store_trace(path, export.payload, export.context, finalized=True)
    retained = active_trace_exports(path)
    checks.require_equal(retained, exports())
    checks.require_equal(
        reconcile_executions(retained, bindings()),
        reconcile_executions(exports(), bindings()),
    )


def test_cache_cannot_reference_failed_execution() -> None:
    """A failed attempt cannot be a successful cached output producer."""
    first = exports()[0]
    payload = (
        RESUME.replace(b"be/a681ba", b"a4/32767a")
        .replace(b"CACHED\t2", b"CACHED\t1")
        .replace(b"1083\t1028", b"78\t19")
    )
    cached = TraceExport(payload, probe_context(payload, "resume"))
    links = tuple(
        link.model_copy(
            update={
                "source_sha256": cached.context.source_sha256,
                "execution_id": "failure" if link.task_id == "2" else "success",
                "attempt": 1,
            },
        )
        if link.run_id == cached.context.run_id
        else link
        for link in bindings()
    )
    with pytest.raises(ValueError, match=r"failed.*cache|cache.*failed"):
        reconcile_executions((first, cached), links)


def test_repeated_noncache_observations_deduplicate_explicit_identity() -> None:
    """Two exported observations may explicitly describe one physical execution."""
    first = exports()[0]
    payload = INITIAL.replace(b"SYNTHETIC (success)", b"SYNTHETIC (renamed)")
    second = TraceExport(payload, probe_context(payload, "reexport"))
    initial_links = bindings()[:3]
    repeated = tuple(
        link.model_copy(
            update={
                "source_sha256": second.context.source_sha256,
                "run_id": second.context.run_id,
            },
        )
        for link in initial_links
    )
    result = reconcile_executions((first, second), (*initial_links, *repeated))
    checks.require_equal(len(result.executions), 3)
    checks.require_equal(len(result.observations), 6)
    checks.require_equal(result.sum_task_realtime_ms.total, 2077)


def test_missing_all_counters_and_empty_selected_scope_are_distinct() -> None:
    """No executions is zero in scope; unknown counters are undefined totals."""
    empty = reconcile_executions((), ())
    checks.require_equal(empty.sum_task_realtime_ms.total, 0)
    first = exports()[0]
    payload = (
        INITIAL.replace(b"1107\t1030", b"-\t-")
        .replace(b"78\t19", b"-\t-")
        .replace(b"1083\t1028", b"-\t-")
    )
    unknown = TraceExport(payload, probe_context(payload, "initial"))
    links = tuple(
        link.model_copy(
            update={
                "source_sha256": unknown.context.source_sha256,
            },
        )
        for link in bindings()[:3]
    )
    result = reconcile_executions((unknown,), links)
    checks.require_equal(result.sum_task_realtime_ms.total, None)
    checks.require_equal(result.sum_task_realtime_ms.known_subtotal, 0)
    checks.require_equal(len(result.sum_task_realtime_ms.missing_execution_ids), 3)
    with pytest.raises(ValueError, match=r"Duplicate.*export"):
        reconcile_executions((first, first), bindings()[:3])


def test_reconciliation_reverifies_payload_and_copied_bindings() -> None:
    """Immutable wrappers cannot admit altered source bytes or invalid ordinals."""
    first, cached = exports()
    with pytest.raises(ValueError, match="hash"):
        reconcile_executions(
            (replace(first, payload=first.payload + b"\n"), cached),
            bindings(),
        )
    bad = bindings()[0].model_copy(update={"attempt": True})
    with pytest.raises(ValueError, match="integer"):
        reconcile_executions(exports(), (bad, *bindings()[1:]))
