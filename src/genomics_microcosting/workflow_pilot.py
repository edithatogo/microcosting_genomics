# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Price a selected workflow revision log through the component costing API."""

import json
from dataclasses import dataclass
from fractions import Fraction
lazy from pathlib import Path

from genomics_microcosting.component_allocations import price_component_allocations
from genomics_microcosting.nextflow_trace import read_raw_trace
from genomics_microcosting.workflow_events import (
    WorkflowEventError,
    read_event_revision_log,
)
lazy from genomics_microcosting.component_allocations import (
    ComponentAllocationCost,
    ComponentAllocationInputs,
)
lazy from genomics_microcosting.nextflow_trace import TraceContext, TraceImport
lazy from genomics_microcosting.workflow_allocations import AllocationQuantity
lazy from genomics_microcosting.workflow_events import (
    WorkflowEventRevision,
    WorkflowRevisionLog,
)


@dataclass(frozen=True, slots=True)
class WorkflowPilotLedger:
    """Retain the cost result with source history and selected quantity joins."""

    revisions: WorkflowRevisionLog
    allocations: tuple[
        tuple[WorkflowEventRevision, tuple[AllocationQuantity, ...]],
        ...,
    ]
    cost: ComponentAllocationCost
    trace: TraceImport | None
    mdt_labour: tuple[tuple[str, str, str, Fraction | None], ...]


def price_workflow_pilot(
    path: Path,
    expected_sha256: str,
    inputs: ComponentAllocationInputs,
    *,
    trace_source: tuple[Path, TraceContext] | None = None,
) -> WorkflowPilotLedger:
    """Check the source and every allocation before delegating unit-cost pricing."""
    revisions = read_event_revision_log(path, expected_sha256)
    if inputs.cohort.source_workload_sha256 != revisions.source_sha256:
        message = "Costing cohort is not bound to the workflow revision log"
        raise WorkflowEventError(message)
    trace = None
    if trace_source is not None:
        trace_path, trace_context = trace_source
        if revisions.trace_sha256 != trace_context.source_sha256:
            message = "Nextflow trace is not bound to the revision log"
            raise WorkflowEventError(message)
        trace = read_raw_trace(trace_path.read_bytes(), trace_context)
    elif revisions.trace_sha256 is not None:
        message = "Revision log requires a Nextflow trace"
        raise WorkflowEventError(message)
    allocations = tuple(
        (event, event.allocations)
        for event in revisions.selected
        if not event.cancelled
    )
    _verify_trace_allocations(allocations, trace, None)
    observed = tuple(quantity for _, bundle in allocations for quantity in bundle)
    if observed != inputs.pricing.quantities:
        message = "Selected observations do not match the pricing quantities"
        raise WorkflowEventError(message)
    cost = price_component_allocations(inputs)
    _verify_trace_allocations(allocations, trace, cost)
    _verify_mdt_cost(allocations, cost)
    return WorkflowPilotLedger(
        revisions,
        allocations,
        cost,
        trace,
        tuple(
            (event.event_id, attendee, case, seconds)
            for event, _ in allocations
            if event.meeting is not None
            for attendee, case, seconds in event.meeting.labour_seconds()
        ),
    )


def _verify_trace_allocations(
    allocations: tuple[
        tuple[WorkflowEventRevision, tuple[AllocationQuantity, ...]],
        ...,
    ],
    trace: TraceImport | None,
    cost: ComponentAllocationCost | None,
) -> None:
    attempts = (
        {}
        if trace is None
        else {
            f"{trace.context.run_id}/{task.task_id}/{task.attempt}": task
            for task in trace.tasks
        }
    )
    lines = {} if cost is None else {line.binding: line for line in cost.lines}
    for event, bundle in allocations:
        if event.source != "nextflow":
            continue
        task = attempts.get(event.event_id)
        if task is None:
            message = "Nextflow event does not identify a retained task attempt"
            raise WorkflowEventError(message)
        if bundle and task.status not in {"COMPLETED", "FAILED"}:
            message = "Only executed Nextflow attempts may carry allocations"
            raise WorkflowEventError(message)

        if (
            cost is not None
            and bundle
            and (
                task.realtime_ms is None
                or any(
                    lines[binding].resource_unit != "elapsed_ms" for binding in bundle
                )
                or sum((lines[binding].quantity for binding in bundle), Fraction(0))
                != task.realtime_ms
            )
        ):
            message = "Nextflow allocation must conserve observed elapsed milliseconds"
            raise WorkflowEventError(message)


def _verify_mdt_cost(
    allocations: tuple[
        tuple[WorkflowEventRevision, tuple[AllocationQuantity, ...]],
        ...,
    ],
    cost: ComponentAllocationCost,
) -> None:
    lines = {line.binding: line for line in cost.lines}
    for event, bundle in allocations:
        if event.meeting is None:
            if event.source == "mdt" and bundle:
                message = "MDT pricing requires attendance evidence"
                raise WorkflowEventError(message)
            continue
        roles = {row.attendee_id: row.role for row in event.meeting.attendance}
        seconds_by_role: dict[tuple[str, str], Fraction | None] = {}
        for attendee, case, seconds in event.meeting.labour_seconds():
            key = (roles[attendee], case)
            prior = seconds_by_role.get(key, Fraction(0))
            seconds_by_role[key] = (
                None if prior is None or seconds is None else prior + seconds
            )
        for binding in bundle:
            expected = seconds_by_role.get((binding.resource_id, binding.case_id))
            line = lines[binding]
            if (
                expected is None
                or line.resource_unit != "second"
                or line.quantity != expected
            ):
                message = (
                    "MDT quantity must match verified role and case labour seconds"
                )
                raise WorkflowEventError(message)


def workflow_pilot_report(ledger: WorkflowPilotLedger) -> bytes:
    """Encode exact priced quantities and source identities for replay."""
    cost = ledger.cost
    report = {
        "profile": "synthetic-workflow-cost-report-v1",
        "revision_sha256": ledger.revisions.source_sha256,
        "trace_sha256": ledger.revisions.trace_sha256,
        "pricing_input_sha256": cost.input_sha256,
        "cohort_sha256": cost.cohort_sha256,
        "selected_events": [
            {
                "source": event.source,
                "event_id": event.event_id,
                "revision": event.revision,
                "observed_at": event.observed_at.isoformat(),
                "cancelled": event.cancelled,
                "priced": bool(event.allocations),
            }
            for event in ledger.revisions.selected
        ],
        "trace_attempts": []
        if ledger.trace is None
        else [
            {
                "run_id": ledger.trace.context.run_id,
                "task_id": task.task_id,
                "attempt": task.attempt,
                "status": task.status,
                "elapsed_ms": task.realtime_ms,
            }
            for task in ledger.trace.tasks
        ],
        "currency": cost.pricing.currency,
        "price_year": cost.pricing.price_year,
        "tax_basis": cost.pricing.tax_basis,
        "cost_scope": cost.cost_scope,
        "selected_component_cost": str(cost.selected_component_cost),
        "lines": [
            {
                "source": event.source,
                "event_id": event.event_id,
                "revision": event.revision,
                "observed_at": event.observed_at.isoformat(),
                **line.binding.model_dump(),
                "resource_unit": line.resource_unit,
                "quantity": str(line.quantity),
                "unit_rate": str(line.unit_rate),
                "cost": str(line.selected_cost),
            }
            for (event, _), line in zip(
                (
                    (event, binding)
                    for event, bundle in ledger.allocations
                    for binding in bundle
                ),
                cost.lines,
                strict=True,
            )
        ],
        "mdt_labour": [
            [event, attendee, case, None if seconds is None else str(seconds)]
            for event, attendee, case, seconds in ledger.mdt_labour
        ],
        "full_workload_cost": None,
    }
    return (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
