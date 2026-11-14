# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise revision-bound pricing through the existing component engine."""

import json
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.component_allocations import component_cohort_sha256
from genomics_microcosting.nextflow_trace import TraceContext
from genomics_microcosting.workflow_events import read_event_revision_log
from genomics_microcosting.workflow_pilot import (
    price_workflow_pilot,
    workflow_pilot_report,
)
from tests import checks
from tests.test_component_allocations import component_inputs


def test_workflow_pilot_prices_selected_bundle(tmp_path: Path) -> None:
    """Retain a repeat's evidence and price its declared quantities exactly."""
    path = tmp_path / "instrument.json"
    raw = (
        b'{"profile":"synthetic-workflow-revisions-v1","events":['
        b'{"source":"instrument","event_id":"repeat-1","revision":1,'
        b'"observed_at":"2026-11-07T11:00:00+10:00","cancelled":false}]}'
    )
    inputs = component_inputs(tmp_path)
    document = json.loads(raw)
    document["events"][0]["allocations"] = [
        quantity.model_dump() for quantity in inputs.pricing.quantities
    ]
    trace_path = tmp_path / "trace.tsv"
    trace_bytes = (
        b"task_id\thash\tprocess\tstatus\tattempt\trealtime\n"
        b"1\tab/cdef\tALIGN\tFAILED\t1\t500\n"
        b"2\tac/cdef\tALIGN\tCOMPLETED\t2\t900\n"
        b"3\tac/cdef\tALIGN\tCACHED\t1\t900\n"
    )
    trace_path.write_bytes(trace_bytes)
    trace_digest = sha256(trace_bytes).hexdigest()
    document["trace_sha256"] = trace_digest
    context = TraceContext(
        run_id="synthetic-run",
        workload_id="synthetic-workload",
        nextflow_version="26.10.5",
        executor="local",
        source_sha256=trace_digest,
        raw_metrics=True,
    )
    document["events"].append(
        {
            "source": "nextflow",
            "event_id": "synthetic-run/3/1",
            "revision": 1,
            "observed_at": "2026-11-07T11:00:00+10:00",
            "cancelled": False,
        },
    )
    document["events"].append(
        {
            "source": "mdt",
            "event_id": "meeting-1",
            "revision": 1,
            "observed_at": "2026-11-07T11:30:00+10:00",
            "cancelled": False,
            "meeting": {
                "elapsed_seconds": 1800,
                "attendance": [
                    {"attendee_id": "a", "role": "scientist", "seconds": 1200},
                    {"attendee_id": "b", "role": "clinician", "seconds": None},
                ],
                "cases": [
                    {"case_id": "c1", "weight": 1},
                    {"case_id": "c2", "weight": 2},
                ],
            },
        },
    )
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    digest = sha256(raw).hexdigest()
    event, meeting, cached = read_event_revision_log(path, digest).selected
    cohort = inputs.cohort.model_copy(update={"source_workload_sha256": digest})
    pricing = inputs.pricing.model_copy(
        update={"cohort_sha256": component_cohort_sha256(cohort)},
    )
    inputs = replace(inputs, cohort=cohort, pricing=pricing)
    with pytest.raises(ValueError, match="requires a Nextflow trace"):
        price_workflow_pilot(path, digest, inputs)
    result = price_workflow_pilot(
        path,
        digest,
        inputs,
        trace_source=(trace_path, context),
    )
    trace = result.trace
    if trace is None:
        pytest.fail("Verified trace was omitted from the ledger")
    checks.require_equal(
        tuple(task.status for task in trace.tasks),
        ("FAILED", "COMPLETED", "CACHED"),
    )
    checks.require_equal(result.revisions.source_sha256, digest)
    checks.require_equal(
        result.allocations,
        ((event, pricing.quantities), (meeting, ()), (cached, ())),
    )
    checks.require_equal(result.cost.selected_component_cost, Fraction(14, 3))
    checks.require_equal(
        result.mdt_labour,
        (
            ("meeting-1", "a", "c1", Fraction(400)),
            ("meeting-1", "a", "c2", Fraction(800)),
            ("meeting-1", "b", "c1", None),
            ("meeting-1", "b", "c2", None),
        ),
    )
    report = json.loads(workflow_pilot_report(result))
    checks.require_equal(
        [row["status"] for row in report["trace_attempts"]],
        ["FAILED", "COMPLETED", "CACHED"],
    )
    checks.require_equal(
        [row["event_id"] for row in report["selected_events"] if row["priced"]],
        [event.event_id],
    )
    trace_path.write_bytes(trace_bytes + b"\n")
    with pytest.raises(ValueError, match="Trace source hash mismatch"):
        price_workflow_pilot(path, digest, inputs, trace_source=(trace_path, context))

    trace_path.write_bytes(trace_bytes)
    document["events"][1]["allocations"] = document["events"][0]["allocations"]
    amended = json.dumps(document).encode()
    path.write_bytes(amended)
    amended_digest = sha256(amended).hexdigest()
    amended_cohort = cohort.model_copy(
        update={"source_workload_sha256": amended_digest},
    )
    with pytest.raises(ValueError, match="Only executed Nextflow attempts"):
        price_workflow_pilot(
            path,
            amended_digest,
            replace(inputs, cohort=amended_cohort),
            trace_source=(trace_path, context),
        )


MDT_SOURCE_SECONDS = 1200


@pytest.mark.parametrize("attendance_seconds", [1200, 1800, None])
def test_mdt_pricing_uses_verified_labour(
    tmp_path: Path,
    attendance_seconds: int | None,
) -> None:
    """Price equal case shares only when verified seconds match attendance."""
    inputs = component_inputs(
        tmp_path,
        numerator="1200",
        denominator="2",
        rate="0.05",
        units=("second", "second"),
    )
    document = {
        "profile": "synthetic-workflow-revisions-v1",
        "events": [
            {
                "source": "mdt",
                "event_id": "meeting-1",
                "revision": 1,
                "observed_at": "2026-11-07T11:30:00+10:00",
                "cancelled": False,
                "allocations": [q.model_dump() for q in inputs.pricing.quantities],
                "meeting": {
                    "elapsed_seconds": 1800,
                    "attendance": [
                        {
                            "attendee_id": "a",
                            "role": "extra",
                            "seconds": attendance_seconds,
                        },
                    ],
                    "cases": [
                        {"case_id": c.case_id, "weight": 1} for c in inputs.cohort.cases
                    ],
                },
            },
        ],
    }
    raw = json.dumps(document).encode()
    path = tmp_path / "mdt.json"
    path.write_bytes(raw)
    digest = sha256(raw).hexdigest()
    cohort = inputs.cohort.model_copy(update={"source_workload_sha256": digest})
    pricing = inputs.pricing.model_copy(
        update={"cohort_sha256": component_cohort_sha256(cohort)},
    )
    inputs = replace(inputs, cohort=cohort, pricing=pricing)
    if attendance_seconds != MDT_SOURCE_SECONDS:
        with pytest.raises(ValueError, match="verified role and case labour seconds"):
            price_workflow_pilot(path, digest, inputs)
        return
    result = price_workflow_pilot(path, digest, inputs)
    checks.require_equal(result.cost.selected_component_cost, Fraction(60))


@pytest.mark.parametrize("realtime", ["900", "901", "-"])
def test_nextflow_prices_only_conserved_elapsed_time(
    tmp_path: Path,
    realtime: str,
) -> None:
    """Price an executed attempt's elapsed milliseconds across two cases."""
    inputs = component_inputs(
        tmp_path,
        numerator="900",
        denominator="2",
        rate="0.01",
        units=("elapsed_ms", "elapsed_ms"),
    )
    trace_path = tmp_path / "trace.tsv"
    raw_trace = (
        "task_id\thash\tprocess\tstatus\tattempt\trealtime\n"
        f"2\tac/cdef\tALIGN\tCOMPLETED\t2\t{realtime}\n"
    ).encode()
    trace_path.write_bytes(raw_trace)
    trace_digest = sha256(raw_trace).hexdigest()
    context = TraceContext(
        run_id="synthetic-run",
        workload_id="synthetic-workload",
        nextflow_version="26.10.5",
        executor="local",
        source_sha256=trace_digest,
        raw_metrics=True,
    )
    document = {
        "profile": "synthetic-workflow-revisions-v1",
        "trace_sha256": trace_digest,
        "events": [
            {
                "source": "nextflow",
                "event_id": "synthetic-run/2/2",
                "revision": 1,
                "observed_at": "2026-11-07T11:30:00+10:00",
                "cancelled": False,
                "allocations": [q.model_dump() for q in inputs.pricing.quantities],
            },
        ],
    }
    raw = json.dumps(document).encode()
    path = tmp_path / "compute.json"
    path.write_bytes(raw)
    digest = sha256(raw).hexdigest()
    cohort = inputs.cohort.model_copy(update={"source_workload_sha256": digest})
    pricing = inputs.pricing.model_copy(
        update={"cohort_sha256": component_cohort_sha256(cohort)},
    )
    inputs = replace(inputs, cohort=cohort, pricing=pricing)
    if realtime != "900":
        with pytest.raises(ValueError, match="conserve observed elapsed"):
            price_workflow_pilot(
                path,
                digest,
                inputs,
                trace_source=(trace_path, context),
            )
        return
    result = price_workflow_pilot(
        path,
        digest,
        inputs,
        trace_source=(trace_path, context),
    )
    checks.require_equal(result.cost.selected_component_cost, Fraction(9))
    report = workflow_pilot_report(result)
    (tmp_path / "cost-report.json").write_bytes(report)
    replay = price_workflow_pilot(
        path,
        digest,
        inputs,
        trace_source=(trace_path, context),
    )
    checks.require_equal(report, workflow_pilot_report(replay))
    checks.require_equal(json.loads(report)["selected_component_cost"], "9")
