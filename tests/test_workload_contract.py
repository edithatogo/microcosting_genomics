# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify distinct workload entities and attempt conservation."""

from decimal import Decimal

import pytest

from genomics_microcosting.workload_contract import (
    Workload,
    WorkloadAttempt,
    WorkloadCase,
)
from tests import checks


def case(identifier: str) -> WorkloadCase:
    """Create a synthetic case with shared specimen and unknown result mapping."""
    return WorkloadCase(
        case_id=identifier,
        requested_test_id=f"test-{identifier}",
        assay_id="assay",
        patient_ids=None,
        family_ids=None,
        arrival_seconds=Decimal(0),
        specimen_ids=("shared-specimen",),
        library_ids=(f"library-{identifier}",),
        reportable_result_ids=None,
    )


def workload() -> Workload:
    """Create an unexecuted workload with unknown control and attempt data."""
    return Workload(
        workload_id="w1",
        process_id="p1",
        process_graph_sha256="a" * 64,
        parameter_version_id="v1",
        horizon_seconds=Decimal(10),
        cases=(case("a"), case("b")),
        control_ids=None,
        attempts=None,
    )


def test_counts_preserve_shared_entities_and_unknown_results() -> None:
    """Distinct tests can share a specimen without fabricated result counts."""
    w = workload()
    checks.require_equal(
        w.entity_counts(),
        {
            "requested_tests": 2,
            "patients": None,
            "families": None,
            "specimens": 1,
            "libraries": 2,
            "reportable_results": None,
            "controls": None,
            "attempts": None,
        },
    )
    empty = w.model_copy(update={"cases": (), "control_ids": (), "attempts": ()})
    checks.require_equal(
        empty.entity_counts(),
        {
            "requested_tests": 0,
            "patients": 0,
            "families": 0,
            "specimens": 0,
            "libraries": 0,
            "reportable_results": 0,
            "controls": 0,
            "attempts": 0,
        },
    )


def test_attempts_require_known_cases_unique_order_and_complete_history() -> None:
    """Retries remain explicit attempts rather than new requested tests."""
    first = WorkloadAttempt(attempt_id="a1", case_id="a", ordinal=1, state="failed")
    second = WorkloadAttempt(attempt_id="a2", case_id="a", ordinal=2, state="completed")
    w = workload().model_copy(update={"attempts": (first, second)})
    checks.require_equal(w.entity_counts()["requested_tests"], 2)
    checks.require_equal(w.entity_counts()["attempts"], 2)
    for attempts in (
        (second,),
        (first, first),
        (first.model_copy(update={"case_id": "missing"}),),
    ):
        with pytest.raises(ValueError, match=r"attempt|Attempt"):
            workload().model_copy(update={"attempts": attempts}).entity_counts()


def test_invalid_copied_scope_and_time_cannot_be_counted() -> None:
    """Reads revalidate copies and reject duplicate tests or invalid arrivals."""
    w = workload()
    for change in (
        {"cases": (case("a"), case("a"))},
        {"horizon_seconds": Decimal(0)},
        {"cases": (case("a").model_copy(update={"arrival_seconds": Decimal(11)}),)},
    ):
        with pytest.raises(ValueError, match=r"Duplicate|horizon|Arrival"):
            w.model_copy(update=change).entity_counts()


def test_workload_serialization_preserves_missing_and_identity() -> None:
    """Serialized workload boundaries retain unknowns and exact identifiers."""
    w = workload()
    checks.require_equal(Workload.model_validate_json(w.model_dump_json()), w)
    with pytest.raises(ValueError, match="frozen"):
        w.workload_id = "other"
    with pytest.raises(ValueError, match="ordinal"):
        WorkloadAttempt(attempt_id="a1", case_id="a", ordinal=True, state="pending")
