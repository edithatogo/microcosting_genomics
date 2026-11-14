# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Runtime checks used where static annotations cannot validate actual test outputs."""

lazy from collections.abc import Container


def require(*, condition: bool) -> None:
    """Require the original test predicate even under optimized execution."""
    if not condition:
        raise AssertionError


def require_runtime_instance(
    value: object,
    expected: type | tuple[type, ...],
    *,
    message: object = None,
) -> None:
    """Preserve assertion failure semantics for an observed runtime type."""
    if isinstance(value, expected):
        return
    raise AssertionError(message)


def require_keys(container: Container[str], keys: tuple[str, ...]) -> None:
    """Retain every expected membership predicate in its original order."""
    for key in keys:
        if key not in container:
            raise AssertionError(key)


def require_close(
    actual: float,
    expected: float,
    *,
    delta: float,
    message: object = None,
) -> None:
    """Retain the real-valued unittest delta comparison, including exact equality."""
    if actual == expected or abs(actual - expected) <= delta:
        return
    raise AssertionError(message)


def require_rounded_equal(
    actual: float,
    expected: float,
    *,
    places: int = 7,
    message: object = None,
) -> None:
    """Preserve unittest rounding precision rather than substitute relative error."""
    if actual == expected or round(abs(actual - expected), places) == 0:
        return
    raise AssertionError(message)


def require_equal(actual: object, expected: object) -> None:
    """Retain exact equality predicates with both operands visible on failure."""
    if not (actual == expected):
        raise AssertionError((actual, expected))
