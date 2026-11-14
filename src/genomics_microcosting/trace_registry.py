# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Append-only finalized trace snapshots with explicit correction identities."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Literal
lazy from pathlib import Path

from genomics_microcosting.nextflow_trace import (
    TraceContext,
    TraceImport,
    read_raw_trace,
)

APPLICATION_ID = 0x474D4354
SCHEMA_VERSION = 1
SELECT_RECORD = (
    "SELECT source_sha,run_id,revision,context_json,payload,supersedes FROM imports"
)


@dataclass(frozen=True)
class TraceRegistration:
    """Report whether one immutable source snapshot was inserted or reused."""

    source_sha256: str
    revision: int
    state: Literal["inserted", "already_present"]


@dataclass(frozen=True)
class TraceExport:
    """Retain exact source bytes and their independently revalidated context."""

    payload: bytes
    context: TraceContext


@dataclass(frozen=True)
class _Snapshot:
    trace: TraceImport
    payload: bytes
    revision: int
    supersedes: str | None


def _schema(db: sqlite3.Connection, *, create: bool) -> None:
    app = db.execute("PRAGMA application_id").fetchone()[0]
    version = db.execute("PRAGMA user_version").fetchone()[0]
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    if create and app == 0 and version == 0 and not tables:
        db.execute("""CREATE TABLE imports (
            source_sha TEXT PRIMARY KEY NOT NULL,
            run_id TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK(revision > 0),
            context_json TEXT NOT NULL,
            payload BLOB NOT NULL,
            supersedes TEXT REFERENCES imports(source_sha),
            UNIQUE(run_id,revision), UNIQUE(supersedes)
        )""")
        db.execute("PRAGMA application_id=1196245844")
        db.execute("PRAGMA user_version=1")
    elif app != APPLICATION_ID or version != SCHEMA_VERSION:
        msg = "File is not a supported trace registry"
        raise ValueError(msg)


def _decode(row: tuple[object, ...]) -> _Snapshot:
    source, run, revision, encoded, payload, previous = row
    if (
        not isinstance(source, str)
        or not isinstance(run, str)
        or type(revision) is not int
        or revision < 1
        or not isinstance(encoded, str)
        or not isinstance(payload, bytes)
        or (previous is not None and not isinstance(previous, str))
    ):
        msg = "Trace registry record has invalid types"
        raise ValueError(msg)
    context = TraceContext.model_validate_json(encoded)
    if context.source_sha256 != source or context.run_id != run:
        msg = "Trace registry context differs from record identity"
        raise ValueError(msg)
    return _Snapshot(read_raw_trace(payload, context), payload, revision, previous)


def store_trace(
    path: Path,
    payload: bytes,
    context: TraceContext,
    *,
    finalized: bool,
    supersedes: str | None = None,
) -> TraceRegistration:
    """Retain verified bytes atomically; finality remains a caller assertion."""
    if finalized is not True:
        msg = "Trace snapshot must be explicitly finalized"
        raise ValueError(msg)
    parsed = read_raw_trace(payload, context)
    context = parsed.context
    with closing(sqlite3.connect(path, isolation_level=None)) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        _schema(db, create=True)
        existing = db.execute(
            SELECT_RECORD + " WHERE source_sha=?",
            (context.source_sha256,),
        ).fetchone()
        if existing is not None:
            saved = _decode(existing)
            if (
                saved.trace.context != context
                or saved.payload != payload
                or (supersedes is not None and supersedes != saved.supersedes)
            ):
                msg = (
                    "Trace source already belongs to a different context or correction"
                )
                raise ValueError(msg)
            return TraceRegistration(
                context.source_sha256,
                saved.revision,
                "already_present",
            )
        latest = db.execute(
            SELECT_RECORD + " WHERE run_id=? ORDER BY revision DESC LIMIT 1",
            (context.run_id,),
        ).fetchone()
        previous = None if latest is None else _decode(latest)
        expected = None if previous is None else previous.trace.context.source_sha256
        if supersedes != expected:
            msg = "Trace correction must name the latest snapshot of this run"
            raise ValueError(msg)
        revision = 1 if previous is None else previous.revision + 1
        db.execute(
            "INSERT INTO imports VALUES (?,?,?,?,?,?)",
            (
                context.source_sha256,
                context.run_id,
                revision,
                context.model_dump_json(),
                payload,
                supersedes,
            ),
        )
        return TraceRegistration(context.source_sha256, revision, "inserted")


def _active_snapshots(path: Path) -> tuple[_Snapshot, ...]:
    """Read and reverify all chains before selecting latest snapshots."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        _schema(db, create=False)
        rows = db.execute(
            """SELECT source_sha,run_id,revision,context_json,payload,supersedes
               FROM imports ORDER BY run_id,revision""",
        ).fetchall()
        latest: dict[str, _Snapshot] = {}
        for row in rows:
            snapshot = _decode(row)
            run = snapshot.trace.context.run_id
            previous = latest.get(run)
            expected_revision = 1 if previous is None else previous.revision + 1
            expected_source = (
                None if previous is None else previous.trace.context.source_sha256
            )
            if (
                snapshot.revision != expected_revision
                or snapshot.supersedes != expected_source
            ):
                msg = "Trace registry correction chain is inconsistent"
                raise ValueError(msg)
            latest[run] = snapshot
        return tuple(latest.values())


def active_traces(path: Path) -> tuple[TraceImport, ...]:
    """Read and reverify only latest snapshots without creating a missing store."""
    return tuple(s.trace for s in _active_snapshots(path))


def active_trace_exports(path: Path) -> tuple[TraceExport, ...]:
    """Read exact latest payloads and contexts without rebuilding raw exports."""
    return tuple(
        TraceExport(s.payload, s.trace.context) for s in _active_snapshots(path)
    )
