# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Retain finalized trace snapshots without replay duplication or silent correction."""

import sqlite3
from contextlib import closing
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.trace_registry import active_traces, store_trace
from tests import checks
from tests.test_nextflow_export_profile import INITIAL, RESUME, probe_context


def test_actual_exports_are_durable_and_exact_replays_are_idempotent(
    tmp_path: Path,
) -> None:
    """Synthetic exports retain failed/cached rows without replay duplication."""
    path = tmp_path / "traces.sqlite"
    first = store_trace(
        path,
        INITIAL,
        probe_context(INITIAL, "initial"),
        finalized=True,
    )
    checks.require_equal(first.state, "inserted")
    checks.require_equal(first.revision, 1)
    duplicate = store_trace(
        path,
        INITIAL,
        probe_context(INITIAL, "initial"),
        finalized=True,
    )
    checks.require_equal(duplicate.state, "already_present")
    store_trace(path, RESUME, probe_context(RESUME, "resume"), finalized=True)
    traces = active_traces(path)
    checks.require_equal(len(traces), 2)
    checks.require_equal(
        tuple(t.status for t in traces[0].tasks),
        ("COMPLETED", "FAILED", "COMPLETED"),
    )
    checks.require_equal(tuple(t.status for t in traces[1].tasks), ("CACHED", "CACHED"))
    wrong = probe_context(INITIAL, "other")
    with pytest.raises(ValueError, match="context"):
        store_trace(path, INITIAL, wrong, finalized=True)
    with pytest.raises(ValueError, match="finalized"):
        store_trace(path, INITIAL, wrong, finalized=False)


def test_corrections_are_explicit_and_preserve_prior_bytes(tmp_path: Path) -> None:
    """Only a correction naming the latest snapshot may change one run's export."""
    path = tmp_path / "traces.sqlite"
    context = probe_context(INITIAL, "initial")
    store_trace(path, INITIAL, context, finalized=True)
    changed = INITIAL.replace(b"1107", b"1108")
    corrected = context.model_copy(
        update={"source_sha256": sha256(changed).hexdigest()},
    )
    with pytest.raises(ValueError, match="latest"):
        store_trace(path, changed, corrected, finalized=True)
    next_record = store_trace(
        path,
        changed,
        corrected,
        finalized=True,
        supersedes=context.source_sha256,
    )
    checks.require_equal(next_record.revision, 2)
    checks.require_equal(active_traces(path)[0].tasks[0].duration_ms, 1108)
    replay = store_trace(path, INITIAL, context, finalized=True)
    checks.require_equal(replay.state, "already_present")
    checks.require_equal(active_traces(path)[0].tasks[0].duration_ms, 1108)
    with closing(sqlite3.connect(path)) as db, db:
        checks.require_equal(
            db.execute("SELECT payload FROM imports WHERE revision=1").fetchone()[0],
            INITIAL,
        )
    third = changed.replace(b"1108", b"1109")
    third_context = corrected.model_copy(
        update={"source_sha256": sha256(third).hexdigest()},
    )
    with pytest.raises(ValueError, match="latest"):
        store_trace(
            path,
            third,
            third_context,
            finalized=True,
            supersedes=context.source_sha256,
        )
    checks.require_equal(active_traces(path)[0].tasks[0].duration_ms, 1108)


def test_foreign_databases_and_corrupted_retention_are_rejected(tmp_path: Path) -> None:
    """Never claim an unrelated database or accept damaged retained evidence."""
    foreign = tmp_path / "foreign.sqlite"
    with closing(sqlite3.connect(foreign)) as db, db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
    with pytest.raises(ValueError, match="registry"):
        store_trace(foreign, INITIAL, probe_context(INITIAL, "initial"), finalized=True)
    path = tmp_path / "traces.sqlite"
    store_trace(path, INITIAL, probe_context(INITIAL, "initial"), finalized=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE imports SET payload=?", (b"damaged",))
    with pytest.raises(ValueError, match="hash"):
        active_traces(path)
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError, match="unable to open"):
        active_traces(missing)
    checks.require_equal(int(missing.exists()), 0)
