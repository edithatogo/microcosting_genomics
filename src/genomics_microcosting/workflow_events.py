# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reconcile immutable event revisions for the synthetic workflow sidecar."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import cast
lazy from collections.abc import Iterable, Mapping
lazy from pathlib import Path

from genomics_microcosting.workflow_allocations import AllocationQuantity
from genomics_microcosting.workflow_mdt import MeetingObservation


class WorkflowEventError(ValueError):
    """Invalid synthetic workflow event or source file."""


@dataclass(frozen=True, slots=True)
class WorkflowEventRevision:
    """One observation of a source event, with its original timezone."""

    source: str
    event_id: str
    revision: int
    observed_at: datetime
    cancelled: bool = False
    allocations: tuple[AllocationQuantity, ...] = ()
    meeting: MeetingObservation | None = None

    def __post_init__(self) -> None:
        """Validate source identity, revision and timezone."""
        if not self.source.strip() or not self.event_id.strip():
            message = "Source and event identity are required"
            raise WorkflowEventError(message)
        if type(self.revision) is not int or self.revision < 1:
            message = "Revision must be a positive integer"
            raise WorkflowEventError(message)
        if self.observed_at.utcoffset() is None:
            message = "Observation time requires a UTC offset"
            raise WorkflowEventError(message)


def reconcile_event_revisions(
    observations: Iterable[WorkflowEventRevision],
) -> tuple[WorkflowEventRevision, ...]:
    """Return latest revisions in source order, including cancellation tombstones."""
    revisions: dict[tuple[str, str, int], WorkflowEventRevision] = {}
    latest: dict[tuple[str, str], WorkflowEventRevision] = {}
    for event in observations:
        identity = (event.source, event.event_id)
        key = (*identity, event.revision)
        prior = revisions.get(key)
        if prior is not None and (
            prior != event
            or prior.observed_at.isoformat() != event.observed_at.isoformat()
        ):
            message = f"Conflicting observations for event revision {key!r}"
            raise WorkflowEventError(message)
        revisions[key] = event
        selected = latest.get(identity)
        if selected is None or event.revision > selected.revision:
            latest[identity] = event
    return tuple(latest[identity] for identity in sorted(latest))


@dataclass(frozen=True, slots=True)
class WorkflowRevisionLog:
    """Verified source identity, revision history and selected observations."""

    source_sha256: str
    observations: tuple[WorkflowEventRevision, ...]
    selected: tuple[WorkflowEventRevision, ...]
    trace_sha256: str | None


def read_event_revision_log(path: Path, expected_sha256: str) -> WorkflowRevisionLog:
    """Verify and read the synthetic revision-log profile without writing files."""
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        message = "Revision log SHA-256 mismatch"
        raise WorkflowEventError(message)
    decoded: object = json.loads(raw, object_pairs_hook=_unique_json_fields)
    document = cast("dict[str, object]", decoded)
    if not isinstance(decoded, dict) or set(document) - {"trace_sha256"} != {
        "profile",
        "events",
    }:
        message = "Invalid revision log envelope"
        raise WorkflowEventError(message)
    if document["profile"] != "synthetic-workflow-revisions-v1":
        message = "Unsupported revision log profile"
        raise WorkflowEventError(message)
    events = document["events"]
    if not isinstance(events, list):
        message = "Revision log events must be a list"
        raise TypeError(message)
    trace_sha256 = document.get("trace_sha256")
    if trace_sha256 is not None and (
        not isinstance(trace_sha256, str)
        or len(trace_sha256) != sha256().digest_size * 2
        or any(char not in "0123456789abcdef" for char in trace_sha256)
    ):
        message = "Invalid workflow trace SHA-256"
        raise WorkflowEventError(message)
    observations = tuple(_decode_event(event) for event in cast("list[object]", events))
    return WorkflowRevisionLog(
        expected_sha256,
        observations,
        reconcile_event_revisions(observations),
        trace_sha256,
    )


def _unique_json_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        message = "Duplicate JSON field"
        raise WorkflowEventError(message)
    return fields


def _decode_event(raw: object) -> WorkflowEventRevision:
    event = cast("dict[str, object]", raw)
    if not isinstance(raw, dict) or set(event) - {"allocations", "meeting"} != {
        "source",
        "event_id",
        "revision",
        "observed_at",
        "cancelled",
    }:
        message = "Invalid revision log event fields"
        raise WorkflowEventError(message)
    source = event["source"]
    event_id = event["event_id"]
    observed_at = event["observed_at"]
    cancelled = event["cancelled"]
    if (
        not isinstance(source, str)
        or not isinstance(event_id, str)
        or not isinstance(observed_at, str)
    ):
        message = "Expected text identity and observation timestamp"
        raise WorkflowEventError(message)
    revision = event["revision"]
    if type(revision) is not int:
        message = "Revision must be a positive integer"
        raise WorkflowEventError(message)
    if type(cancelled) is not bool:
        message = "Cancellation must be a boolean"
        raise WorkflowEventError(message)
    allocations = event.get("allocations", [])
    if not isinstance(allocations, list) or (cancelled and allocations):
        message = "Invalid allocation bundle for workflow event"
        raise WorkflowEventError(message)
    meeting = event.get("meeting")
    if meeting is not None and (source != "mdt" or cancelled):
        message = "Meeting observations require an active MDT event"
        raise WorkflowEventError(message)
    return WorkflowEventRevision(
        source,
        event_id,
        revision,
        datetime.fromisoformat(observed_at),
        cancelled,
        tuple(
            AllocationQuantity.model_validate(item)
            for item in cast("list[object]", allocations)
        ),
        None
        if meeting is None
        else MeetingObservation.model_validate_json(json.dumps(meeting)),
    )


def select_resource_observations[T](
    log: WorkflowRevisionLog,
    resources: Mapping[WorkflowEventRevision, T],
) -> tuple[tuple[WorkflowEventRevision, T], ...]:
    """Bind one resource bundle to each selected active revision."""
    expected = {event for event in log.selected if not event.cancelled}
    if expected != set(resources):
        message = "Resource bundles must cover exactly the active event revisions"
        raise WorkflowEventError(message)
    return tuple(
        (event, resources[event]) for event in log.selected if not event.cancelled
    )
