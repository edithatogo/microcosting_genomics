# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Storage size, lifetime and sharing preserve units and evidence boundaries."""

import json
from fractions import Fraction
from hashlib import sha256
from typing import Any

import pytest

from genomics_microcosting.storage_usage import (
    StorageContext,
    calculate_storage_usage,
)
from genomics_microcosting.workload_contract import Workload
from tests import checks


def storage_inputs() -> tuple[bytes, bytes, Workload, StorageContext]:
    """Provide a shared copy and replica with assumed lifetimes."""
    workload = Workload.model_validate(
        {
            "workload_id": "w",
            "process_id": "p",
            "process_graph_sha256": "a" * 64,
            "parameter_version_id": "v1",
            "horizon_seconds": "10",
            "cases": [],
            "control_ids": [],
            "attempts": [],
        },
    )
    snapshot = {
        "format_version": "storage-size-json-v1",
        "workload_id": "w",
        "source_run_id": "run1",
        "exporter_version": "synthetic-v1",
        "time_origin_id": "origin1",
        "scope_limit": "Synthetic copies only",
        "objects": [
            {
                "observation_id": name,
                "object_id": "artifact-1",
                "copy_id": name,
                "resource_id": "volume1",
                "object_sha256": "b" * 64,
                "size_value": "1",
                "size_unit": "GB",
                "quantity_basis": "logical",
                "evidence_basis": "reported",
                "observed_at_utc": None,
            }
            for name in ("primary", "replica")
        ],
    }
    retention = {
        "format_version": "storage-lifetime-json-v1",
        "workload_id": "w",
        "parameter_version_id": "v1",
        "retention_policy_id": "policy1",
        "time_origin_id": "origin1",
        "scope_limit": "Assumed toy intervals",
        "lifetimes": [
            {
                "observation_id": name,
                "start_seconds": start,
                "end_seconds": end,
                "time_basis": "assumed",
                "shares": [
                    {"workload_id": "w", "share": "0.25"},
                    {"workload_id": "other", "share": "0.5"},
                ],
            }
            for name, start, end in (
                ("primary", "-2", "20"),
                ("replica", "2", "6"),
            )
        ],
    }
    sizes = json.dumps(snapshot).encode()
    times = json.dumps(retention).encode()
    context = StorageContext(
        function_version="storage-usage-v1",
        source_run_id="run1",
        exporter_version="synthetic-v1",
        time_origin_id="origin1",
        retention_policy_id="policy1",
        baseline_sha256="c" * 64,
        size_source_sha256=sha256(sizes).hexdigest(),
        lifetime_source_sha256=sha256(times).hexdigest(),
    )
    return sizes, times, workload, context


def change_source(
    payload: bytes,
    keys: tuple[str | int, ...],
    value: object,
) -> bytes:
    """Rebuild one explicit source without hiding the changed bytes."""
    record = json.loads(payload)
    node: Any = record
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    return json.dumps(record).encode()


def test_replication_clipping_sharing_and_replay() -> None:
    """A shared copy is allocated once; replicas add their lifetimes."""
    sizes, times, workload, context = storage_inputs()
    result = calculate_storage_usage(sizes, times, workload, context)
    group = result.groups[0]
    checks.require_equal(group.byte_seconds, Fraction(14_000_000_000))
    checks.require_equal(group.target_byte_seconds, Fraction(3_500_000_000))
    checks.require_equal(group.other_byte_seconds, Fraction(7_000_000_000))
    checks.require_equal(
        group.unallocated_byte_seconds,
        Fraction(3_500_000_000),
    )
    checks.require_equal(result.rows[0].active_seconds, Fraction(10))
    checks.require_equal(result.rows[1].active_seconds, Fraction(4))
    checks.require_equal(group.time_basis, "assumed")
    checks.require_equal(
        calculate_storage_usage(sizes, times, workload, context),
        result,
    )


def test_gib_and_gb_and_evidence_bases_are_separate() -> None:
    """Binary/decimal units normalize exactly without merging physical bases."""
    sizes, times, workload, context = storage_inputs()
    sizes = change_source(sizes, ("objects", 1, "size_unit"), "GiB")
    sizes = change_source(sizes, ("objects", 1, "quantity_basis"), "billed")
    sizes = change_source(sizes, ("objects", 1, "evidence_basis"), "billed")
    context = context.model_copy(
        update={"size_source_sha256": sha256(sizes).hexdigest()},
    )
    result = calculate_storage_usage(sizes, times, workload, context)
    checks.require_equal(
        result.rows[0].normalized_bytes,
        Fraction(1_000_000_000),
    )
    checks.require_equal(
        result.rows[1].normalized_bytes,
        Fraction(1_073_741_824),
    )
    checks.require_equal(len(result.groups), 2)


@pytest.mark.parametrize("field", ["size_value", "end_seconds"])
def test_unknown_size_or_lifetime_stays_unknown(field: str) -> None:
    """No missing retention or size becomes zero or the planning horizon."""
    sizes, times, workload, context = storage_inputs()
    if field == "size_value":
        sizes = change_source(sizes, ("objects", 0, field), None)
    else:
        times = change_source(times, ("lifetimes", 0, field), None)
    context = context.model_copy(
        update={
            "size_source_sha256": sha256(sizes).hexdigest(),
            "lifetime_source_sha256": sha256(times).hexdigest(),
        },
    )
    result = calculate_storage_usage(sizes, times, workload, context)
    checks.require_equal(result.rows[0].byte_seconds, None)
    checks.require_equal(result.groups[0].byte_seconds, None)
    checks.require_equal(result.unknown_byte_time_ids, ("primary",))


@pytest.mark.parametrize(
    ("source", "keys", "value", "error"),
    [
        ("size", ("objects", 0, "size_unit"), "month", "Input should be"),
        ("size", ("objects", 0, "size_value"), "-1", "negative"),
        ("size", ("objects", 0, "size_value"), "NaN", "decimal"),
        ("size", ("objects", 0, "copy_id"), "replica", "copy"),
        ("size", ("objects", 0, "observation_id"), "replica", "observation"),
        ("size", ("objects", 0, "size_unit"), None, "unit"),
        ("size", ("objects", 0, "quantity_basis"), "billed", "basis"),
        ("time", ("lifetimes", 0, "start_seconds"), "21", "reversed"),
        ("time", ("lifetimes", 0, "observation_id"), "missing", "coverage"),
        ("time", ("lifetimes", 0, "shares", 0, "share"), "0.75", "share"),
        ("time", ("time_origin_id",), "other", "context"),
        ("time", ("parameter_version_id",), "other", "context"),
    ],
)
def test_invalid_sources_fail_closed(
    source: str,
    keys: tuple[str | int, ...],
    value: object,
    error: str,
) -> None:
    """Coverage, unit, identity, evidence and allocation conflicts reject."""
    sizes, times, workload, context = storage_inputs()
    if source == "size":
        sizes = change_source(sizes, keys, value)
    else:
        times = change_source(times, keys, value)
    context = context.model_copy(
        update={
            "size_source_sha256": sha256(sizes).hexdigest(),
            "lifetime_source_sha256": sha256(times).hexdigest(),
        },
    )
    with pytest.raises(ValueError, match=error):
        calculate_storage_usage(sizes, times, workload, context)


def test_hash_and_duplicate_json_cannot_be_bypassed() -> None:
    """Exact payload and unambiguous JSON are checked before accounting."""
    sizes, times, workload, context = storage_inputs()
    with pytest.raises(ValueError, match="hash"):
        calculate_storage_usage(sizes + b"\n", times, workload, context)
    times = times.replace(
        b'"workload_id": "w"',
        b'"workload_id": "w", "workload_id": "w"',
    )
    context = context.model_copy(
        update={"lifetime_source_sha256": sha256(times).hexdigest()},
    )
    with pytest.raises(ValueError, match=r"Duplicate.*JSON"):
        calculate_storage_usage(sizes, times, workload, context)


@pytest.mark.parametrize(
    ("start", "end", "duration"),
    [
        ("0", "0", 0),
        ("10", "20", 0),
        ("-3", "-1", 0),
        ("0", "10", 10),
        ("9.5", "10.5", Fraction(1, 2)),
        ("20", None, 0),
        (None, "-1", 0),
    ],
)
def test_half_open_horizon_limits(
    start: str | None,
    end: str | None,
    duration: Fraction | int,
) -> None:
    """Outside-horizon lifetimes have zero modeled byte-time."""
    sizes, times, workload, context = storage_inputs()
    times = change_source(times, ("lifetimes", 0, "start_seconds"), start)
    times = change_source(times, ("lifetimes", 0, "end_seconds"), end)
    context = context.model_copy(
        update={
            "lifetime_source_sha256": sha256(times).hexdigest(),
        },
    )
    result = calculate_storage_usage(sizes, times, workload, context)
    checks.require_equal(result.rows[0].active_seconds, Fraction(duration))
    checks.require_equal(
        result.rows[0].byte_seconds,
        Fraction(duration) * 10**9,
    )


def test_empty_sources_do_not_assert_total_infrastructure_use() -> None:
    """An empty declared scope has no invented group, copy or infrastructure."""
    sizes, times, workload, context = storage_inputs()
    sizes = change_source(sizes, ("objects",), [])
    times = change_source(times, ("lifetimes",), [])
    context = context.model_copy(
        update={
            "size_source_sha256": sha256(sizes).hexdigest(),
            "lifetime_source_sha256": sha256(times).hexdigest(),
        },
    )
    result = calculate_storage_usage(sizes, times, workload, context)
    checks.require_equal(result.rows, ())
    checks.require_equal(result.groups, ())
    checks.require_equal(result.size_scope_limit, "Synthetic copies only")
    checks.require_equal(result.workload, workload)


def test_single_copy_can_be_wholly_unallocated() -> None:
    """Keep a shared copy unallocated without inventing another replica."""
    sizes, times, workload, context = storage_inputs()
    times = change_source(times, ("lifetimes", 0, "shares"), [])
    context = context.model_copy(
        update={
            "lifetime_source_sha256": sha256(times).hexdigest(),
        },
    )
    result = calculate_storage_usage(sizes, times, workload, context)
    row = result.rows[0]
    checks.require_equal(row.target_byte_seconds, Fraction(0))
    checks.require_equal(row.other_byte_seconds, Fraction(0))
    checks.require_equal(row.unallocated_byte_seconds, Fraction(10_000_000_000))


def test_bounded_small_interval_oracle_and_conservation() -> None:
    """Count integer occupied seconds independently of interval subtraction."""
    sizes, times, workload, context = storage_inputs()
    for start in range(-2, 12):
        for end in range(start, 13):
            recipe = change_source(
                times,
                ("lifetimes", 0, "start_seconds"),
                str(start),
            )
            recipe = change_source(
                recipe,
                ("lifetimes", 0, "end_seconds"),
                str(end),
            )
            ctx = context.model_copy(
                update={
                    "lifetime_source_sha256": sha256(recipe).hexdigest(),
                },
            )
            row = calculate_storage_usage(sizes, recipe, workload, ctx).rows[0]
            expected = sum(start <= tick < end for tick in range(10))
            checks.require_equal(row.active_seconds, Fraction(expected))
            if (
                row.target_byte_seconds is None
                or row.other_byte_seconds is None
                or row.unallocated_byte_seconds is None
            ):
                pytest.fail("Known source unexpectedly produced unknown share")
            checks.require_equal(
                row.target_byte_seconds
                + row.other_byte_seconds
                + row.unallocated_byte_seconds,
                row.byte_seconds,
            )


@pytest.mark.parametrize(
    ("value", "unit", "error"),
    [
        ("1", "bytes", "timestamp"),
        ("0.1", "bytes", "fractional"),
    ],
)
def test_observed_sizes_need_time_and_integer_bytes(
    value: str,
    unit: str,
    error: str,
) -> None:
    """Reported fractional sizes cannot become measured bytes."""
    sizes, times, workload, context = storage_inputs()
    sizes = change_source(sizes, ("objects", 0, "evidence_basis"), "observed")
    sizes = change_source(sizes, ("objects", 0, "size_value"), value)
    sizes = change_source(sizes, ("objects", 0, "size_unit"), unit)
    if error == "fractional":
        sizes = change_source(
            sizes,
            ("objects", 0, "observed_at_utc"),
            "2026-11-07T00:00:00Z",
        )
    context = context.model_copy(
        update={"size_source_sha256": sha256(sizes).hexdigest()},
    )
    with pytest.raises(ValueError, match=error):
        calculate_storage_usage(sizes, times, workload, context)
