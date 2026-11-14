# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Map explicit manual-extraction batches to the installed Dapane Rust kernel.

This is the selected labour stage, not a complete assay costing, workforce
eligibility decision, clinical workflow approval or empirical validation.
"""

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Literal, Protocol, TypedDict, Unpack, cast
from unicodedata import category
lazy from collections.abc import Sequence

from genomics_microcosting.dapane_release import selected_workforce_quote

WORKBOOK_SHA256 = "2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4"
SHEET = "Labour - Usage - VCGS"
MAX_BATCHES = 1000
MAX_SPECIMENS = 6
MAX_ID_BYTES = 80
MAX_MAPPING_BYTES = 1024
STEPS = (("labwork", "30", "D22"), ("admin", "5", "D23"))


@dataclass(frozen=True, slots=True)
class ExtractionBatch:
    """One explicitly incurred batch; failed work retains both resource uses."""

    batch_id: str
    specimen_ids: tuple[str, ...]
    outcome: Literal["completed", "failed"] = "completed"
    repeat_of: str | None = None


class ExtractionOptions(TypedDict):
    """Required named inputs for the versioned consumer boundary."""

    release_digest: str
    quote_id: str
    batches: Sequence[ExtractionBatch]
    service_date: str
    knowledge_cutoff: str
    role_mapping_basis: str
    run_id: str


class HistoricalEngine(Protocol):
    """The preserved cell-read entry point, without importing the legacy engine."""

    def get_cell_value(self, sheet_name: str, cell_ref: str) -> object:
        """Return the original engine's value or raise its original exception."""
        ...


class DapaneRuntime(Protocol):
    """The optional installed wheel's public entry point."""

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a request in the shared native implementation."""
        ...


def _require(*, condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identifier(value: object, *, field: str, limit: int = MAX_ID_BYTES) -> str:
    _require(condition=isinstance(value, str), message=f"{field} must be a string")
    text = cast("str", value)
    _require(
        condition=bool(text) and text.strip() == text and not any(category(c) == "Cc" for c in text),
        message=f"{field} must be a nonblank, trimmed identifier",
    )
    try:
        _require(condition=len(text.encode()) <= limit, message=f"{field} exceeds its UTF-8 byte bound")
    except UnicodeError as error:
        message = f"{field} must contain valid Unicode"
        raise ValueError(message) from error
    return text


def _checked_batches(batches: Sequence[ExtractionBatch]) -> tuple[ExtractionBatch, ...]:
    _require(
        condition=isinstance(batches, (list, tuple)) and 0 < len(batches) <= MAX_BATCHES,
        message="Supply an explicit bounded nonempty batch sequence",
    )
    known: dict[str, ExtractionBatch] = {}
    consumed: set[str] = set()
    repeated: set[str] = set()
    for batch in batches:
        _require(condition=isinstance(batch, ExtractionBatch), message="Invalid batch record")
        _identifier(batch.batch_id, field="batch_id")
        _require(condition=batch.batch_id not in known, message="Duplicate batch identity")
        members = batch.specimen_ids
        _require(
            condition=isinstance(members, tuple) and 0 < len(members) <= MAX_SPECIMENS,
            message="Supply one to six explicit specimen identities per batch",
        )
        for member in members:
            _identifier(member, field="specimen_id")
        _require(condition=len(set(members)) == len(members), message="Duplicate specimen in batch")
        _require(
            condition=batch.outcome in ("completed", "failed"),
            message="Unknown batch outcome",
        )
        if batch.repeat_of is None:
            _require(condition=not consumed.intersection(members), message="Repeated specimen requires repeat_of")
        else:
            _identifier(batch.repeat_of, field="repeat_of")
            parent = known.get(batch.repeat_of)
            _require(
                condition=parent is not None and parent.outcome == "failed"
                and set(parent.specimen_ids) == set(members)
                and batch.repeat_of not in repeated,
                message="A repeat requires one preceding failed batch with identical specimens",
            )
            repeated.add(batch.repeat_of)
        consumed.update(members)
        known[batch.batch_id] = batch
    return tuple(batches)


def manual_dna_extraction_descriptor() -> dict[str, Any]:
    """Describe the source mapping and explicit exclusions without opening data."""
    return {
        "recipe_id": "manual-dna-extraction-v1",
        "workbook_sha256": WORKBOOK_SHA256,
        "sheet": SHEET,
        "steps": [
            {"id": step, "batch_minutes": minutes, "source_cell": cell}
            for step, minutes, cell in STEPS
        ],
        "nominal_batch_samples": MAX_SPECIMENS,
        "sample_count_cells": ["E22", "E23"],
        "role_mapping": "Historical LT to quote target requires an explicit analyst mapping",
        "repeat_policy": "Every declared failed or repeated batch incurs both uses",
        "allocation": "Equal shares of each rounded pool over actual named specimens",
        "scope": "manual DNA extraction labour only",
        "scientific_validation": False,
        "excluded": [
            "other assay stages", "equipment", "consumables", "unquoted labour components",
            "automatic failure probabilities", "employment eligibility", "clinical equivalence",
        ],
    }


def _batch_records(
    batch: ExtractionBatch, quote: dict[str, Any], service_date: str,
    role_mapping_basis: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    process_id, event_id = "batch:" + batch.batch_id, "attempt:" + batch.batch_id
    members = sorted(batch.specimen_ids)
    usage: list[dict[str, Any]] = []
    for step, minutes, cell in STEPS:
        identity = batch.batch_id + ":" + step
        usage.append({
            "id": identity, "use_id": identity, "kind": "resource_use",
            "target": quote["target"], "unit": "minute", "quantity": minutes,
            "service_date": service_date, "quote_id": quote["id"],
            "process_id": process_id, "event_id": event_id,
            "activity_id": "manual-extraction-" + batch.outcome,
            "object_ids": members,
            "source": {
                "id": "manual-extraction-v15", "version": "manual-dna-extraction-v1",
                "evidence": "derived", "access": "public", "validation": "unvalidated",
                "content_digest": "sha256:" + WORKBOOK_SHA256,
                "locator": (
                    f"{SHEET}!{cell}; batch={batch.batch_id}; outcome={batch.outcome}; "
                    f"repeat_of={batch.repeat_of}; role_mapping={role_mapping_basis}"
                ),
            },
        })
    allocation = {
        "id": "pool:" + batch.batch_id,
        "source_line_ids": [line["id"] for line in usage],
        "weights": [{"object_id": member, "weight": "1"} for member in members],
    }
    process = {
        "id": process_id, "model_id": "manual-dna-extraction",
        "model_version": "manual-dna-extraction-v1",
    }
    event = {
        "id": event_id, "occurred_on": service_date, "process_id": process_id,
        "activity_id": "manual-extraction-" + batch.outcome, "object_ids": members,
    }
    return usage, allocation, process, event


def manual_dna_extraction_request(
    release_json: str | bytes, **options: Unpack[ExtractionOptions],
) -> dict[str, Any]:
    """Construct exact usage; Dapane alone values and allocates each batch.

    The external artifact digest must identify the reviewed workforce release.
    Role mapping is preserved verbatim in usage provenance, not inferred from
    the historical LT label. A partial batch consumes the same declared labour;
    no throughput, waiting-time or staff-utilization inference is made.
    """
    _require(
        condition=set(options) == ExtractionOptions.__required_keys__,
        message="Missing or unknown manual extraction option",
    )
    run_id = options["run_id"]
    role_mapping_basis = options["role_mapping_basis"]
    service_date = options["service_date"]
    knowledge_cutoff = options["knowledge_cutoff"]
    _identifier(run_id, field="run_id")
    _identifier(role_mapping_basis, field="role_mapping_basis", limit=MAX_MAPPING_BYTES)
    checked = _checked_batches(options["batches"])
    quote = selected_workforce_quote(
        release_json, expected_digest=options["release_digest"],
        quote_id=options["quote_id"],
        service_date=service_date, knowledge_cutoff=knowledge_cutoff,
    )
    usage: list[dict[str, Any]] = []
    allocations: list[dict[str, Any]] = []
    processes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for batch in checked:
        lines, allocation, process, event = _batch_records(
            batch, quote, service_date, role_mapping_basis,
        )
        usage.extend(lines)
        allocations.append(allocation)
        processes.append(process)
        events.append(event)
    members = sorted({member for batch in checked for member in batch.specimen_ids})
    return {
        "schema_version": "0.1", "run_id": run_id,
        "knowledge_cutoff": knowledge_cutoff,
        "policy": {
            "id": "manual-extraction-labour", "version": "1",
            "currency": quote["currency"], "price_year": quote["price_year"],
            "perspective": "provider", "basis": quote["basis"],
            "rounding": {"scale": 2, "mode": "half_even"},
        },
        "quotes": [quote], "usage": usage,
        "objects": [{"id": member, "kind": "specimen"} for member in members],
        "processes": processes, "events": events, "allocations": allocations,
    }


def evaluate_native_request(request: dict[str, Any]) -> dict[str, Any]:
    """Invoke the optional installed wheel, propagating its structured errors."""
    runtime = cast("DapaneRuntime", import_module("dapane"))
    return runtime.evaluate(request)


def evaluate_manual_dna_extraction(
    release_json: str | bytes, **options: Unpack[ExtractionOptions],
) -> dict[str, Any]:
    """Evaluate the source-mapped request through the same Rust public boundary."""
    return evaluate_native_request(
        manual_dna_extraction_request(release_json, **options),
    )


def historical_manual_extraction(engine: HistoricalEngine) -> dict[str, object]:
    """Preserve explicit legacy calls; do not translate, repair or silence values."""
    return {cell: engine.get_cell_value(SHEET, cell) for cell in ("AB22", "AB23", "AB24")}
