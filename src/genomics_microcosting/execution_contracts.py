# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Shared contracts for execution decorators and profiling results."""

from typing import Protocol, TypedDict
lazy from collections.abc import Callable


def legacy_bool_option(
    name: str,
    positional: tuple[bool, ...],
    *,
    keyword: bool | None,
    default: bool,
) -> bool:
    """Bind an existing positional flag alongside its explicit keyword form."""
    if len(positional) > 1 or (positional and keyword is not None):
        message = f"Invalid arguments for {name}"
        raise TypeError(message)
    if positional:
        return positional[0]
    return default if keyword is None else keyword


class ProfileMetrics(TypedDict):
    """Describe measured counts, elapsed seconds and memory changes in MiB."""

    call_count: int
    total_time: float
    avg_time: float
    max_time: float
    min_time: float
    total_memory: float
    avg_memory: float
    max_memory: float
    errors: int


class ProfilerDecorator(Protocol):
    """Preserve the signature and result type of a profiled operation."""

    def __call__[**P, R](self, func: Callable[P, R], /) -> Callable[P, R]:
        """Wrap a callable without changing its argument or result contract."""
        ...


class DegradationDecorator[D](Protocol):
    """Retain normal results and make fallback or null results explicit."""

    def __call__[**P, R](self, func: Callable[P, R], /) -> Callable[P, R | D | None]:
        """Wrap an operation with its declared recovery result."""
        ...
