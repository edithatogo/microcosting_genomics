# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify raw trace identity, missing metrics and attempts."""

from hashlib import sha256

import pytest

from genomics_microcosting.nextflow_trace import TraceContext, read_raw_trace
from tests import checks

HEADER = (
    "task_id\thash\tprocess\tstatus\tattempt\tcpus\tmemory\tpeak_rss"
    "\tduration\trealtime\n"
)


def context(payload: bytes) -> TraceContext:
    """Declare a synthetic raw-profile provenance context."""
    return TraceContext(
        run_id="run",
        workload_id="workload",
        nextflow_version="synthetic",
        executor="synthetic",
        source_sha256=sha256(payload).hexdigest(),
        raw_metrics=True,
    )


def test_raw_trace_preserves_missing_failed_retried_and_cached_rows() -> None:
    """Task status does not zero cached or failed metrics or merge attempts."""
    payload = (
        HEADER
        + "1\tab/cd\talign\tFAILED\t1\t2\t1024\t512\t1500\t1000\n"
        + "1\tab/cd\talign\tCOMPLETED\t2\t2\t1024\t600\t2000\t1500\n"
        + "2\tab/cd\talign\tCACHED\t1\t-\t-\t-\t-\t-\n"
    ).encode()
    result = read_raw_trace(payload, context(payload))
    checks.require_equal(len(result.tasks), 3)
    checks.require_equal(result.tasks[0].duration_ms, 1500)
    checks.require_equal(result.tasks[0].requested_memory_bytes, 1024)
    checks.require_equal(result.tasks[0].peak_rss_bytes, 512)
    checks.require_equal(result.tasks[2].duration_ms, None)
    checks.require_equal(result.tasks[2].status, "CACHED")


@pytest.mark.parametrize(
    "row",
    [
        "1\th\tp\tCOMPLETED\t1\t2\t1024\t512\t1s\t1000\n",
        "1\th\tp\tCOMPLETED\t0\t2\t1024\t512\t1000\t1000\n",
        "1\th\tp\tCOMPLETED\t1\t2\t1024\t512\t1000\n",
    ],
)
def test_invalid_raw_profile_rows_are_rejected(row: str) -> None:
    """Formatted units, invalid attempts and incomplete rows fail closed."""
    payload = (HEADER + row).encode()
    with pytest.raises(ValueError, match=r"raw|attempt|width"):
        read_raw_trace(payload, context(payload))


def test_duplicate_attempts_headers_and_source_mismatch_are_rejected() -> None:
    """Duplicate imports cannot silently double resource usage."""
    row = "1\th\tp\tFAILED\t1\t2\t1024\t512\t1000\t1000\n"
    payload = (HEADER + row + row).encode()
    with pytest.raises(ValueError, match="Duplicate"):
        read_raw_trace(payload, context(payload))
    with pytest.raises(ValueError, match="hash"):
        read_raw_trace(payload, context(b"other"))
    duplicate_header = (HEADER.replace("hash", "task_id") + row).encode()
    with pytest.raises(ValueError, match="header"):
        read_raw_trace(duplicate_header, context(duplicate_header))


def test_optional_metric_absence_and_extension_fields_are_retained() -> None:
    """Absent columns remain unknown and unparsed extensions retain raw values."""
    payload = (
        b"task_id\thash\tprocess\tstatus\tattempt\tcustom\n1\th\tp\tNEW\t1\tvalue\n"
    )
    result = read_raw_trace(payload, context(payload))
    checks.require_equal(result.tasks[0].requested_cpus, None)
    checks.require_equal(result.tasks[0].peak_rss_bytes, None)
    checks.require_equal(dict(result.tasks[0].raw_fields)["custom"], "value")
