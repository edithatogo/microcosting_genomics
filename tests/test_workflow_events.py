# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise workflow revision reconciliation and source validation."""

from datetime import datetime
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.workflow_events import (
    WorkflowEventRevision,
    read_event_revision_log,
    reconcile_event_revisions,
    select_resource_observations,
)
from tests import checks

OBSERVED = datetime.fromisoformat("2026-11-07T09:00:00+10:00")


def test_late_delivery_preserves_cancellation_and_distinct_repeat() -> None:
    """Late delivery preserves cancellation and distinct repeat."""
    original = WorkflowEventRevision("instrument", "run-1", 1, OBSERVED)
    cancelled = WorkflowEventRevision(
        "instrument",
        "run-1",
        2,
        OBSERVED,
        cancelled=True,
    )
    repeat = WorkflowEventRevision("instrument", "run-2", 1, OBSERVED)
    checks.require_equal(
        reconcile_event_revisions([repeat, cancelled, original, original]),
        (cancelled, repeat),
    )


def test_conflict_in_superseded_revision_still_fails() -> None:
    """Conflict in superseded revision still fails."""
    original = WorkflowEventRevision("instrument", "run-1", 1, OBSERVED)
    latest = WorkflowEventRevision("instrument", "run-1", 2, OBSERVED)
    conflict = WorkflowEventRevision("instrument", "run-1", 1, OBSERVED, cancelled=True)
    with pytest.raises(ValueError, match="Conflicting observations"):
        reconcile_event_revisions([latest, original, conflict])


def test_naive_observation_time_fails() -> None:
    """Naive observation time fails."""
    with pytest.raises(ValueError, match="UTC offset"):
        WorkflowEventRevision("instrument", "run-1", 1, OBSERVED.replace(tzinfo=None))


def test_revision_log_checks_bytes_and_preserves_offset(tmp_path: Path) -> None:
    """Revision log checks bytes and preserves offset."""
    path = tmp_path / "revisions.json"
    raw = (
        b'{"profile":"synthetic-workflow-revisions-v1","events":['
        b'{"source":"instrument","event_id":"run-1","revision":2,'
        b'"observed_at":"2026-11-07T09:00:00+10:00","cancelled":true}]}'
    )
    path.write_bytes(raw)
    digest = sha256(raw).hexdigest()
    log = read_event_revision_log(path, digest)
    (event,) = log.selected
    checks.require_equal(log.source_sha256, digest)
    checks.require_equal(log.observations, (event,))
    if not event.cancelled:
        pytest.fail("Selected revision must retain cancellation")
    checks.require_equal(event.observed_at.isoformat(), "2026-11-07T09:00:00+10:00")
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        read_event_revision_log(path, sha256(raw).hexdigest())


def test_revision_log_rejects_duplicate_json_fields(tmp_path: Path) -> None:
    """Revision log rejects duplicate json fields."""
    path = tmp_path / "revisions.json"
    raw = b'{"profile":"synthetic-workflow-revisions-v1","events":[],"events":[]}'
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        read_event_revision_log(path, sha256(raw).hexdigest())


def test_resource_join_rejects_stale_and_cancelled_revisions(tmp_path: Path) -> None:
    """Resource join rejects stale and cancelled revisions."""
    path = tmp_path / "revisions.json"
    raw = (
        b'{"profile":"synthetic-workflow-revisions-v1","events":['
        b'{"source":"instrument","event_id":"run-1","revision":1,'
        b'"observed_at":"2026-11-07T09:00:00+10:00","cancelled":false},'
        b'{"source":"instrument","event_id":"run-1","revision":2,'
        b'"observed_at":"2026-11-07T10:00:00+10:00","cancelled":true},'
        b'{"source":"instrument","event_id":"run-2","revision":1,'
        b'"observed_at":"2026-11-07T11:00:00+10:00","cancelled":false}]}'
    )
    path.write_bytes(raw)
    log = read_event_revision_log(path, sha256(raw).hexdigest())
    stale, cancelled, repeat = log.observations
    checks.require_equal(
        select_resource_observations(log, {repeat: "one flow cell"}),
        ((repeat, "one flow cell"),),
    )
    with pytest.raises(ValueError, match="active event revisions"):
        select_resource_observations(log, {stale: 1, cancelled: 1, repeat: 1})
