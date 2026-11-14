# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Native accounting metadata and CPU counters must be retained, not guessed."""

import json
from decimal import Decimal
from hashlib import sha256

import pytest

from genomics_microcosting.native_usage import NativeUsageContext, read_native_usage
from tests import checks


def native_payload() -> bytes:
    """Supply synthetic parser data in the actual collector's fixed profile."""
    raw = dict.fromkeys(
        (
            "ru_idrss",
            "ru_inblock",
            "ru_isrss",
            "ru_ixrss",
            "ru_majflt",
            "ru_maxrss",
            "ru_minflt",
            "ru_msgrcv",
            "ru_msgsnd",
            "ru_nivcsw",
            "ru_nsignals",
            "ru_nswap",
            "ru_nvcsw",
            "ru_oublock",
            "ru_stime",
            "ru_utime",
        ),
        "0",
    )
    raw.update({"ru_utime": "1.25", "ru_stime": "0.25", "ru_maxrss": "100"})
    return json.dumps(
        {
            "format_version": "darwin-wait4-synthetic-v1",
            "exporter_sha256": "a" * 64,
            "child_program_sha256": "b" * 64,
            "python": "3.15.1 synthetic fixture",
            "platform": "Darwin",
            "release": "27.2.0",
            "machine": "arm64",
            "task_label": "retry",
            "attempt": 1,
            "child_pid": 100,
            "wait_status": 4352,
            "exit_code": 17,
            "elapsed_monotonic_ns": 2000000000,
            "user_cpu_seconds": "1.25",
            "system_cpu_seconds": "0.25",
            "peak_rss_raw": 100,
            "peak_rss_unit": "unqualified",
            "raw_rusage": raw,
            "scope": (
                "one waited synthetic child; parent, shell, "
                "Nextflow and host overhead excluded"
            ),
            "native_accounting_resolution": "not qualified",
        },
    ).encode()


def native_context(payload: bytes) -> NativeUsageContext:
    """Declare synthetic source identities without claiming native execution."""
    return NativeUsageContext(
        source_sha256=sha256(payload).hexdigest(),
        exporter_sha256="a" * 64,
        child_program_sha256="b" * 64,
        python_version="3.15.1 synthetic fixture",
        release="27.2.0",
        machine="arm64",
        run_id="run1",
        task_id="2",
        task_label="retry",
        attempt=1,
        exit_code=17,
    )


def test_native_counter_reader_preserves_units_failure_and_scope() -> None:
    """CPU counters survive failed work; raw RSS never becomes memory-time or bytes."""
    payload = native_payload()
    context = native_context(payload)
    result = read_native_usage(payload, context)
    checks.require_equal(result.user_cpu_seconds, Decimal("1.25"))
    checks.require_equal(result.system_cpu_seconds, Decimal("0.25"))
    checks.require_equal(result.exit_code, 17)
    checks.require_equal(result.peak_rss_raw, 100)
    checks.require_equal(result.peak_rss_bytes, None)
    checks.require_equal(dict(result.raw_rusage)["ru_utime"], "1.25")
    with pytest.raises(ValueError, match="hash"):
        read_native_usage(payload + b" ", context)
    for field, value in (
        ("exporter_sha256", "c" * 64),
        ("attempt", 2),
        ("exit_code", 0),
        ("python_version", "3.15.1 different"),
    ):
        with pytest.raises(ValueError, match="context"):
            read_native_usage(payload, context.model_copy(update={field: value}))


def test_native_raw_values_and_schema_cannot_silently_change() -> None:
    """Reject contradictory counters/status, unknown profile fields and ambiguity."""
    original = native_payload()
    for field, value in (
        ("user_cpu_seconds", "NaN"),
        ("system_cpu_seconds", "-1"),
        ("wait_status", 0),
        ("peak_rss_unit", "bytes"),
        ("raw_rusage", {"ru_utime": "1.25"}),
    ):
        record = json.loads(original)
        record[field] = value
        payload = json.dumps(record).encode()
        with pytest.raises(ValueError, match=r"validation|counter|status|raw"):
            read_native_usage(payload, native_context(payload))
    payload = original.replace(b'"attempt": 1', b'"attempt": 2, "attempt": 1')
    with pytest.raises(ValueError, match="Duplicate"):
        read_native_usage(payload, native_context(payload))
