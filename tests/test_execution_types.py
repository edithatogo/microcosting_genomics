# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify runtime and static contracts for execution decorators."""

from typing import assert_type

import pytest

from genomics_microcosting.error_handling import ErrorHandler
from genomics_microcosting.performance import PerformanceProfiler
from tests.checks import require_equal


def test_profile_preserves_signature_and_error_identity() -> None:
    """Keep typed results and re-raise the original failure after measuring it."""
    profiler = PerformanceProfiler()
    failure = ValueError("synthetic failure")

    @profiler.profile("typed")
    def operation(value: int) -> int:
        if value < 0:
            raise failure
        return value * 2

    assert_type(operation(2), int)
    require_equal(operation(2), 4)
    with pytest.raises(ValueError, match=r"^synthetic failure$") as caught:
        operation(-1)
    if caught.value is not failure:
        raise AssertionError
    if not (profiler.get_report()["typed"]["errors"] == 1):
        raise AssertionError


def test_degradation_declares_null_and_fallback() -> None:
    """Keep fallback values explicit in both runtime results and static types."""
    handler = ErrorHandler()

    @handler.graceful_degradation("nullable")
    def nullable(value: int) -> int:
        if value < 0:
            message = "synthetic failure"
            raise ValueError(message)
        return value

    @handler.graceful_degradation("fallback", default_value="unavailable")
    def fallback(value: int) -> int:
        if value < 0:
            message = "synthetic failure"
            raise ValueError(message)
        return value

    assert_type(nullable(2), int | None)
    assert_type(fallback(2), int | str | None)
    if nullable(-1) is not None:
        raise AssertionError
    if not (fallback(-1) == "unavailable"):
        raise AssertionError
    require_equal(fallback(2), 2)
